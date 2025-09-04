# power_bi_api_client.py - Complete Power BI REST API client implementation

import os
import json
import time
import logging
import requests
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)


class PowerBIAPIClient:
    """
    Complete Power BI REST API client with OAuth2 authentication
    Supports both real API calls and mock mode for testing
    """
    
    def __init__(self, client_id: str = None, client_secret: str = None, 
                 tenant_id: str = None, mock_mode: bool = False):
        """
        Initialize Power BI API client
        
        Args:
            client_id: Azure AD application client ID
            client_secret: Azure AD application client secret
            tenant_id: Azure AD tenant ID
            mock_mode: Enable mock mode for testing without credentials
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.mock_mode = mock_mode
        
        # API configuration
        self.base_url = "https://api.powerbi.com/v1.0/myorg"
        self.auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        self.scope = "https://analysis.windows.net/powerbi/api/.default"
        
        # Session management
        self.access_token = None
        self.token_expires_at = None
        self.session = requests.Session()
        
        # Rate limiting
        self.rate_limit_delay = 0.1  # 100ms between requests
        self.last_request_time = 0
        self.timeout = 30
        
        # Configure session headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        logger.info(f"PowerBI API Client initialized (Mock Mode: {mock_mode})")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Azure AD and get access token
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        if self.mock_mode:
            self.access_token = "mock_token_12345"
            self.token_expires_at = datetime.now() + timedelta(hours=1)
            logger.info("Mock authentication successful")
            return True
        
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            logger.error("Missing required credentials for authentication")
            return False
        
        try:
            logger.info("Authenticating with Azure AD...")
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': self.scope,
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(self.auth_url, data=data, timeout=self.timeout)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
            
            # Update session header
            self.session.headers['Authorization'] = f'Bearer {self.access_token}'
            
            logger.info("Authentication successful")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid access token
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        if not self.access_token or (self.token_expires_at and datetime.now() >= self.token_expires_at):
            return self.authenticate()
        return True
    
    def _rate_limit(self):
        """Apply rate limiting between requests"""
        if not self.mock_mode:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
            self.last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        Make authenticated API request with error handling and retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request parameters
            
        Returns:
            dict: Response JSON or None if failed
        """
        if self.mock_mode:
            return self._get_mock_response(endpoint)
        
        if not self._ensure_authenticated():
            logger.error("Failed to authenticate for API request")
            return None
        
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            logger.debug(f"Making {method} request to {endpoint}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.warning("Got 401, attempting token refresh...")
                if self.authenticate():
                    # Retry once with new token
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response = requests.request(method=method, url=url, headers=headers, timeout=self.timeout, **kwargs)
                    response.raise_for_status()
                    return response.json() if response.content else {}
            
            logger.error(f"API request failed with {response.status_code}: {str(e)}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected API error: {str(e)}")
            return None
    
    def _get_mock_response(self, endpoint: str) -> Dict:
        """
        Return mock data for testing without real API calls
        
        Args:
            endpoint: API endpoint to mock
        
        Returns:
            dict: Mock response data
        """
        mock_responses = {
            '/groups': {
                'value': [
                    {'id': 'mock-ws-1', 'name': 'Sales Analytics', 'type': 'Workspace'},
                    {'id': 'mock-ws-2', 'name': 'Marketing Insights', 'type': 'Workspace'},
                    {'id': 'mock-ws-3', 'name': 'Finance Reports', 'type': 'Workspace'}
                ]
            },
            '/groups/mock-ws-1/reports': {
                'value': [
                    {'id': 'report1', 'name': 'Sales Dashboard', 'datasetId': 'dataset1'},
                    {'id': 'report2', 'name': 'Sales Performance', 'datasetId': 'dataset1'}
                ]
            }
        }
        
        # Check for specific patterns
        for pattern, response in mock_responses.items():
            if endpoint.startswith(pattern) or endpoint == pattern:
                return response
        
        # Default mock response
        return {'value': []}
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the API connection
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if not self.authenticate():
                return False, "Authentication failed - check credentials"
            
            # Try to get workspaces as a connection test
            workspaces = self.get_all_workspaces()
            if workspaces is None:
                return False, "Failed to retrieve workspaces"
            
            return True, f"Successfully connected! Found {len(workspaces)} accessible workspaces"
            
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"
    
    def get_all_workspaces(self) -> Optional[List[Dict]]:
        """Get all accessible workspaces
        
        Returns:
            List of workspace dictionaries with id, name, type
        """
        logger.info("Fetching all workspaces...")
        response = self._make_request('GET', '/groups')
        
        if response and 'value' in response:
            workspaces = response['value']
            logger.info(f"Found {len(workspaces)} workspaces")
            return workspaces
        
        return None
    
    def get_workspace_contents(self, workspace_id: str) -> Optional[Dict]:
        """Get all content in a workspace (reports, dashboards, datasets)
        
        Args:
            workspace_id: Power BI workspace ID
            
        Returns:
            Dict containing reports, dashboards, datasets
        """
        logger.info(f"Fetching workspace contents for {workspace_id}...")
        
        contents = {
            'reports': [],
            'dashboards': [],
            'datasets': []
        }
        
        # Get reports
        reports_response = self._make_request('GET', f'/groups/{workspace_id}/reports')
        if reports_response and 'value' in reports_response:
            contents['reports'] = reports_response['value']
        
        # Get dashboards
        dashboards_response = self._make_request('GET', f'/groups/{workspace_id}/dashboards')
        if dashboards_response and 'value' in dashboards_response:
            contents['dashboards'] = dashboards_response['value']
        
        # Get datasets
        datasets_response = self._make_request('GET', f'/groups/{workspace_id}/datasets')
        if datasets_response and 'value' in datasets_response:
            contents['datasets'] = datasets_response['value']
        
        logger.info(f"Found {len(contents['reports'])} reports, {len(contents['dashboards'])} dashboards, {len(contents['datasets'])} datasets")
        return contents
    
    def get_workspace_reports(self, workspace_id: str) -> List[Dict]:
        """Get all reports in a workspace
        
        Args:
            workspace_id: Power BI workspace ID
            
        Returns:
            List of report dictionaries with id, name, datasetId, etc.
        """
        if self.mock_mode:
            return [
                {"id": "report1", "name": "Sales Dashboard", "webUrl": "https://app.powerbi.com/report1", "datasetId": "dataset1"},
                {"id": "report2", "name": "Marketing Analytics", "webUrl": "https://app.powerbi.com/report2", "datasetId": "dataset2"},
                {"id": "report3", "name": "Financial Overview", "webUrl": "https://app.powerbi.com/report3", "datasetId": "dataset3"}
            ]
        
        logger.info(f"Fetching reports for workspace {workspace_id}...")
        response = self._make_request('GET', f'/groups/{workspace_id}/reports')
        
        if response and 'value' in response:
            return response['value']
        
        return []
    
    def get_report_details(self, workspace_id: str, report_id: str) -> Dict:
        """Get detailed information about a specific report
        
        Args:
            workspace_id: Power BI workspace ID
            report_id: Power BI report ID
            
        Returns:
            Dict containing report details including datasetId
        """
        if self.mock_mode:
            return {
                "id": report_id,
                "name": f"Report {report_id}",
                "datasetId": f"dataset_{report_id[-1]}",
                "webUrl": f"https://app.powerbi.com/{report_id}"
            }
        
        logger.info(f"Fetching details for report {report_id} in workspace {workspace_id}...")
        response = self._make_request('GET', f'/groups/{workspace_id}/reports/{report_id}')
        
        if response:
            return response
        
        return {}

    def get_dataset_measures(self, dataset_id: str, workspace_id: str = None) -> Optional[pd.DataFrame]:
        """Execute DAX query to get all measures in a dataset
        
        Args:
            dataset_id: Power BI dataset ID
            workspace_id: Workspace ID (optional, uses 'myorg' if not provided)
            
        Returns:
            DataFrame with measure information
        """
        if self.mock_mode:
            # Return mock measures data
            return pd.DataFrame({
                'MeasureName': ['Total Sales', 'YTD Sales', 'Growth Rate', 'Average Order Value'],
                'Expression': [
                    'SUM(Sales[Amount])',
                    'TOTALYTD([Total Sales], Calendar[Date])',
                    'DIVIDE([Total Sales] - [PY Sales], [PY Sales], 0)',
                    'DIVIDE([Total Sales], COUNT(Sales[OrderID]), 0)'
                ],
                'FormatString': ['$#,##0', '$#,##0', '0.0%', '$#,##0.00'],
                'Description': ['Total sales amount', 'Year to date sales', 'Growth vs previous year', 'Average order value']
            })
        
        logger.info(f"Fetching measures for dataset {dataset_id}...")
        
        endpoint = f'/datasets/{dataset_id}/executeQueries'
        if workspace_id:
            endpoint = f'/groups/{workspace_id}{endpoint}'
        
        query_data = {
            'queries': [
                {
                    'query': 'EVALUATE INFO.MEASURES()'
                }
            ]
        }
        
        response = self._make_request('POST', endpoint, json=query_data)
        
        if response and 'results' in response:
            try:
                # Parse DAX query results into DataFrame
                result = response['results'][0]
                if 'tables' in result and result['tables']:
                    table_data = result['tables'][0]
                    df = pd.DataFrame(table_data['rows'])
                    if not df.empty and 'columns' in table_data:
                        df.columns = [col['name'] for col in table_data['columns']]
                    return df
            except (KeyError, IndexError) as e:
                logger.error(f"Error parsing measures response: {str(e)}")
        
        return None
    
    def get_dataset_tables(self, dataset_id: str, workspace_id: str = None) -> Optional[pd.DataFrame]:
        """Execute DAX query to get all tables in a dataset
        
        Args:
            dataset_id: Power BI dataset ID
            workspace_id: Workspace ID (optional)
            
        Returns:
            DataFrame with table information
        """
        if self.mock_mode:
            return pd.DataFrame({
                'TableName': ['Sales', 'Customer', 'Product', 'Calendar', 'Territory'],
                'RowCount': [150000, 5000, 2500, 1461, 50],
                'TableType': ['Fact', 'Dimension', 'Dimension', 'Dimension', 'Dimension']
            })
        
        logger.info(f"Fetching tables for dataset {dataset_id}...")
        
        endpoint = f'/datasets/{dataset_id}/executeQueries'
        if workspace_id:
            endpoint = f'/groups/{workspace_id}{endpoint}'
        
        query_data = {
            'queries': [
                {
                    'query': 'EVALUATE INFO.TABLES()'
                }
            ]
        }
        
        response = self._make_request('POST', endpoint, json=query_data)
        
        if response and 'results' in response:
            try:
                result = response['results'][0]
                if 'tables' in result and result['tables']:
                    table_data = result['tables'][0]
                    df = pd.DataFrame(table_data['rows'])
                    if not df.empty and 'columns' in table_data:
                        df.columns = [col['name'] for col in table_data['columns']]
                    return df
            except (KeyError, IndexError) as e:
                logger.error(f"Error parsing tables response: {str(e)}")
        
        return None


def main():
    """Test the PowerBI API client"""
    # Example usage
    client = PowerBIAPIClient(mock_mode=True)
    
    # Test connection
    success, message = client.test_connection()
    print(f"Connection test: {message}")
    
    if success:
        # Get workspaces
        workspaces = client.get_all_workspaces()
        print(f"Found {len(workspaces)} workspaces")
        
        # Get reports from first workspace
        if workspaces:
            ws_id = workspaces[0]['id']
            reports = client.get_workspace_reports(ws_id)
            print(f"Found {len(reports)} reports in first workspace")


if __name__ == "__main__":
    main()