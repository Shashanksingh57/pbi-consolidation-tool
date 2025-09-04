# utils/file_handlers.py - File processing utilities

import io
import csv
import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import pandas as pd

logger = logging.getLogger(__name__)

class FileHandler:
    """Utility class for handling file operations"""
    
    def __init__(self):
        self.supported_image_formats = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}
        self.supported_csv_formats = {'csv', 'txt'}
        self.max_file_size_mb = 10
    
    def validate_image_file(self, file_content: bytes, filename: str) -> Tuple[bool, str]:
        """Validate image file format and size"""
        try:
            # Check file size
            if len(file_content) > self.max_file_size_mb * 1024 * 1024:
                return False, f"File size exceeds {self.max_file_size_mb}MB limit"
            
            # Check file extension
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if file_ext not in self.supported_image_formats:
                return False, f"Unsupported image format: {file_ext}"
            
            # Validate image can be opened
            try:
                image = Image.open(io.BytesIO(file_content))
                image.verify()  # Verify it's a valid image
                return True, "Valid image file"
            except Exception as e:
                return False, f"Invalid image file: {str(e)}"
                
        except Exception as e:
            return False, f"File validation error: {str(e)}"
    
    def process_image_file(self, file_content: bytes, filename: str) -> Optional[Image.Image]:
        """Process and return PIL Image object"""
        try:
            # Validate first
            is_valid, message = self.validate_image_file(file_content, filename)
            if not is_valid:
                logger.error(f"Image validation failed: {message}")
                return None
            
            # Open and convert image
            image = Image.open(io.BytesIO(file_content))
            
            # Convert to RGB if necessary (handles RGBA, etc.)
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            logger.info(f"Processed image: {filename}, Size: {image.size}, Mode: {image.mode}")
            return image
            
        except Exception as e:
            logger.error(f"Error processing image {filename}: {str(e)}")
            return None
    
    def validate_csv_file(self, file_content: str, filename: str) -> Tuple[bool, str]:
        """Validate CSV file content"""
        try:
            # Check file extension
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if file_ext not in self.supported_csv_formats:
                return False, f"Unsupported file format: {file_ext}"
            
            # Try to parse as CSV
            csv_file = io.StringIO(file_content)
            try:
                reader = csv.DictReader(csv_file)
                rows = list(reader)
                
                if not rows:
                    return False, "CSV file is empty"
                
                # Check for required columns (basic validation)
                headers = reader.fieldnames or []
                if not headers:
                    return False, "CSV file has no headers"
                
                return True, f"Valid CSV file with {len(rows)} rows and {len(headers)} columns"
                
            except csv.Error as e:
                return False, f"Invalid CSV format: {str(e)}"
                
        except Exception as e:
            return False, f"CSV validation error: {str(e)}"
    
    def parse_dax_studio_csv(self, file_content: str, filename: str) -> Optional[List[Dict[str, str]]]:
        """Parse DAX Studio export CSV"""
        try:
            # Validate first
            is_valid, message = self.validate_csv_file(file_content, filename)
            if not is_valid:
                logger.error(f"CSV validation failed: {message}")
                return None
            
            # Parse CSV
            csv_file = io.StringIO(file_content)
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            
            # Expected DAX Studio columns (may vary by export type)
            expected_columns = {
                'ObjectType', 'ObjectName', 'TableName', 'Expression', 
                'Description', 'FormatString'
            }
            
            actual_columns = set(reader.fieldnames or [])
            missing_columns = expected_columns - actual_columns
            
            if missing_columns:
                logger.warning(f"Missing expected columns in DAX Studio export: {missing_columns}")
            
            logger.info(f"Parsed DAX Studio CSV: {len(rows)} rows")
            return rows
            
        except Exception as e:
            logger.error(f"Error parsing DAX Studio CSV {filename}: {str(e)}")
            return None
    
    def parse_generic_csv(self, file_content: str, filename: str) -> Optional[pd.DataFrame]:
        """Parse generic CSV file into DataFrame"""
        try:
            # Validate first
            is_valid, message = self.validate_csv_file(file_content, filename)
            if not is_valid:
                logger.error(f"CSV validation failed: {message}")
                return None
            
            # Parse with pandas
            csv_file = io.StringIO(file_content)
            df = pd.read_csv(csv_file)
            
            logger.info(f"Parsed CSV: {len(df)} rows x {len(df.columns)} columns")
            return df
            
        except Exception as e:
            logger.error(f"Error parsing CSV {filename}: {str(e)}")
            return None
    
    def batch_process_images(self, files_data: List[Tuple[bytes, str]]) -> List[Image.Image]:
        """Process multiple image files"""
        processed_images = []
        
        for file_content, filename in files_data:
            image = self.process_image_file(file_content, filename)
            if image:
                processed_images.append(image)
            else:
                logger.warning(f"Failed to process image: {filename}")
        
        logger.info(f"Successfully processed {len(processed_images)} out of {len(files_data)} images")
        return processed_images
    
    def extract_dashboard_metadata(self, csv_content: str, filename: str) -> Dict[str, Any]:
        """Extract metadata from dashboard export files"""
        try:
            # Try different parsing approaches based on filename/content
            if 'dax' in filename.lower() or 'studio' in filename.lower():
                return self._extract_dax_studio_metadata(csv_content)
            else:
                return self._extract_generic_metadata(csv_content)
                
        except Exception as e:
            logger.error(f"Error extracting metadata from {filename}: {str(e)}")
            return {'error': str(e)}
    
    def _extract_dax_studio_metadata(self, csv_content: str) -> Dict[str, Any]:
        """Extract metadata from DAX Studio export"""
        try:
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            
            metadata = {
                'measures': [],
                'tables': [],
                'relationships': [],
                'columns': []
            }
            
            for row in rows:
                object_type = row.get('ObjectType', '').lower()
                
                if object_type == 'measure':
                    metadata['measures'].append({
                        'name': row.get('ObjectName', ''),
                        'table': row.get('TableName', ''),
                        'expression': row.get('Expression', ''),
                        'description': row.get('Description', '')
                    })
                
                elif object_type == 'table':
                    metadata['tables'].append({
                        'name': row.get('ObjectName', ''),
                        'description': row.get('Description', '')
                    })
                
                elif object_type == 'column':
                    metadata['columns'].append({
                        'name': row.get('ObjectName', ''),
                        'table': row.get('TableName', ''),
                        'data_type': row.get('DataType', ''),
                        'description': row.get('Description', '')
                    })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting DAX Studio metadata: {str(e)}")
            return {'error': str(e)}
    
    def _extract_generic_metadata(self, csv_content: str) -> Dict[str, Any]:
        """Extract metadata from generic CSV"""
        try:
            df = pd.read_csv(io.StringIO(csv_content))
            
            metadata = {
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist(),
                'data_types': df.dtypes.astype(str).to_dict(),
                'summary': df.describe().to_dict() if not df.empty else {}
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting generic metadata: {str(e)}")
            return {'error': str(e)}
    
    def create_sample_data(self) -> Dict[str, Any]:
        """Create sample data for testing"""
        return {
            'sample_dashboards': [
                {
                    'dashboard_id': 'sample_001',
                    'dashboard_name': 'Sales Performance Dashboard',
                    'visual_elements': [
                        {'visual_type': 'bar_chart', 'title': 'Sales by Region'},
                        {'visual_type': 'line_chart', 'title': 'Sales Trend'},
                        {'visual_type': 'kpi_card', 'title': 'Total Sales'}
                    ],
                    'measures': [
                        {'measure_name': 'Total Sales', 'dax_formula': 'SUM(Sales[Amount])'},
                        {'measure_name': 'Sales Growth', 'dax_formula': 'DIVIDE([Total Sales], CALCULATE([Total Sales], SAMEPERIODLASTYEAR(Calendar[Date])) - 1'}
                    ]
                },
                {
                    'dashboard_id': 'sample_002',
                    'dashboard_name': 'Regional Sales Report',
                    'visual_elements': [
                        {'visual_type': 'bar_chart', 'title': 'Revenue by Region'},
                        {'visual_type': 'table', 'title': 'Sales Details'},
                        {'visual_type': 'kpi_card', 'title': 'Total Revenue'}
                    ],
                    'measures': [
                        {'measure_name': 'Total Sales', 'dax_formula': 'SUM(Sales[Amount])'},
                        {'measure_name': 'Average Sale', 'dax_formula': 'AVERAGE(Sales[Amount])'}
                    ]
                }
            ]
        }
    
    def get_file_info(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Get detailed file information"""
        return {
            'filename': filename,
            'size_bytes': len(file_content),
            'size_mb': round(len(file_content) / (1024 * 1024), 2),
            'file_extension': filename.lower().split('.')[-1] if '.' in filename else 'unknown',
            'is_image': filename.lower().split('.')[-1] in self.supported_image_formats,
            'is_csv': filename.lower().split('.')[-1] in self.supported_csv_formats
        }