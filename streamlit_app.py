# streamlit_app.py - Refactored Power BI Dashboard Consolidation Tool with Batch Workflow

import os
import io
import json
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="Power BI Dashboard Consolidation Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_custom_css():
    st.markdown("""
    <style>
    .stButton > button {
        background-color: #0C62FB;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s;
        width: 100%;
    }
    
    .stButton > button:hover {
        background-color: #0952D0;
        box-shadow: 0 5px 10px rgba(12, 98, 251, 0.3);
    }
    
    [data-testid="stSidebar"] {
        background-color: #f0f2f6;
    }
    
    .stExpander {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .stProgress > div > div {
        background-color: #0C62FB;
    }
    
    /* Removed visibility hidden styles that might cause blank page */
    </style>
    """, unsafe_allow_html=True)

# Session state initialization
def init_session_state():
    if 'stage' not in st.session_state:
        st.session_state.stage = 'method_choice'
    if 'analysis_method' not in st.session_state:
        st.session_state.analysis_method = None
    if 'num_dashboards' not in st.session_state:
        st.session_state.num_dashboards = 2
    if 'dashboard_config' not in st.session_state:
        st.session_state.dashboard_config = {}
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = {}
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'similarity_matrix' not in st.session_state:
        st.session_state.similarity_matrix = None
    if 'processed_dashboards' not in st.session_state:
        st.session_state.processed_dashboards = None
    if 'api_credentials' not in st.session_state:
        st.session_state.api_credentials = {}
    if 'selected_workspaces' not in st.session_state:
        st.session_state.selected_workspaces = []
    if 'selected_reports' not in st.session_state:
        st.session_state.selected_reports = []

# Header
def render_header():
    st.markdown("""
    <div style='background: linear-gradient(135deg, #0C62FB 0%, #0952D0 100%); 
                padding: 2rem; 
                border-radius: 10px; 
                margin-bottom: 2rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);'>
        <h1 style='color: white; margin: 0; font-size: 2.5rem;'>
            📊 Power BI Dashboard Consolidation Tool
        </h1>
        <p style='color: white; opacity: 0.95; margin-top: 0.5rem; font-size: 1.1rem;'>
            Identify and consolidate duplicate dashboards using AI-powered batch analysis
        </p>
    </div>
    """, unsafe_allow_html=True)

# Progress tracker
def render_progress():
    # Define stages for different workflows
    local_stages = {
        'method_choice': 1,
        'dashboard_config': 2,
        'file_upload': 3,
        'processing': 4,
        'review': 5,
        'analysis': 6,
        'results': 7
    }
    
    api_stages = {
        'method_choice': 1,
        'api_credentials': 2,
        'workspace_selection': 3,
        'analysis': 4,
        'results': 5
    }
    
    # Choose the appropriate stages based on analysis method
    if st.session_state.get('analysis_method') == "REST API Analysis":
        stages = api_stages
        stage_names = [
            "🎯 Analysis Method",
            "🔐 Credentials", 
            "🏢 Workspace Selection",
            "🔄 Analysis",
            "📈 Results"
        ]
    else:
        stages = local_stages
        stage_names = [
            "🎯 Analysis Method",
            "⚙️ Dashboard Config", 
            "📁 File Upload",
            "⚡ Processing",
            "👀 Review & Confirm",
            "🔄 Analysis",
            "📈 Results"
        ]
    
    current_stage = stages.get(st.session_state.stage, 1)
    progress = (current_stage - 1) / (len(stage_names) - 1)
    
    st.progress(progress)
    
    cols = st.columns(len(stage_names))
    for i, (col, stage_name) in enumerate(zip(cols, stage_names)):
        with col:
            if i < current_stage:
                st.markdown(f"✅ **{stage_name}**")
            elif i == current_stage - 1:
                st.markdown(f"🔵 **{stage_name}**")
            else:
                st.markdown(f"⚪ {stage_name}")

# Sidebar
def render_sidebar():
    st.sidebar.header("🎛️ Dashboard Controls")
    
    # Current stage info
    st.sidebar.info(f"**Current Stage:** {st.session_state.stage.replace('_', ' ').title()}")
    
    if st.session_state.analysis_method:
        st.sidebar.success(f"**Method:** {st.session_state.analysis_method}")
    
    if st.session_state.dashboard_config:
        st.sidebar.write("**Dashboard Configuration:**")
        for db_id, config in st.session_state.dashboard_config.items():
            st.sidebar.write(f"• {db_id}: {config['views']} views")
    
    # Reset button
    if st.sidebar.button("🔄 Reset All", type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Stage 1: Analysis Method Choice
def render_method_choice():
    st.header("🎯 Choose Analysis Method")
    
    st.write("""
    Select how you want to analyze your Power BI dashboards:
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Local Batch Analysis")
        st.write("""
        **Best for one-off comparisons or when you don't have API access.** This method gives you complete control by using manually exported metadata files (from DAX Studio) and screenshots you upload directly.
        
        **Use this method if:**
        - You are working with local .pbix files
        - Your organization has not configured API access
        - You need to compare a small, specific set of dashboards
        """)
        
        if st.button("Start Local Batch Analysis", type="primary", key="local_batch"):
            st.session_state.analysis_method = "Local Batch Analysis"
            st.session_state.stage = 'dashboard_config'
            st.rerun()
    
    with col2:
        st.subheader("☁️ REST API Analysis")
        st.write("""
        **The recommended method for automated and scalable analysis.** Connect directly to your Power BI Service to fetch dashboard data from entire workspaces in real-time. Requires initial setup.
        
        **Use this method if:**
        - You have a Power BI Pro or Premium license
        - You need to analyze many dashboards across one or more workspaces
        - You want to automate the data extraction process
        """)
        
        if st.button("Start REST API Analysis", type="primary", key="rest_api"):
            st.session_state.analysis_method = "REST API Analysis"
            st.session_state.stage = 'api_credentials'
            st.rerun()

# Stage 2: Dashboard Configuration
def render_dashboard_config():
    st.header("⚙️ Configure Dashboards and Views")
    
    st.write("Define the scope of your consolidation analysis:")
    
    # Number of dashboards
    num_dashboards = st.number_input(
        "Number of Dashboards to Compare",
        min_value=2,
        max_value=10,
        value=st.session_state.num_dashboards,
        help="How many different dashboards do you want to compare?"
    )
    
    st.session_state.num_dashboards = num_dashboards
    
    st.divider()
    
    # Configure views for each dashboard
    st.subheader("📋 Configure Views for Each Dashboard")
    
    dashboard_config = {}
    
    for i in range(1, num_dashboards + 1):
        with st.expander(f"Dashboard {i} Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input(
                    f"Dashboard {i} Name",
                    value=f"Dashboard {i}",
                    key=f"dashboard_{i}_name"
                )
            
            with col2:
                num_views = st.number_input(
                    f"Number of Views for Dashboard {i}",
                    min_value=1,
                    max_value=20,
                    value=1,
                    key=f"dashboard_{i}_views"
                )
            
            dashboard_config[f"dashboard_{i}"] = {
                'name': name,
                'views': num_views
            }
    
    st.session_state.dashboard_config = dashboard_config
    
    # Summary
    st.subheader("📊 Configuration Summary")
    total_files = sum(config['views'] + 1 for config in dashboard_config.values())  # +1 for metadata
    st.info(f"""
    **Total Dashboards:** {num_dashboards}  
    **Total Views:** {sum(config['views'] for config in dashboard_config.values())}  
    **Expected Files:** {total_files} (including metadata files)
    """)
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Method Choice", key="back_to_method"):
            st.session_state.stage = 'method_choice'
            st.rerun()
    
    with col2:
        if st.button("Continue to File Upload →", type="primary", key="to_file_upload"):
            st.session_state.stage = 'file_upload'
            st.rerun()

# Stage 3: File Upload
def render_file_upload():
    st.header("📁 Upload Dashboard Files")
    
    st.write("Upload screenshots and metadata files for each configured dashboard:")
    
    uploaded_files = {}
    
    for db_id, config in st.session_state.dashboard_config.items():
        st.subheader(f"📊 {config['name']}")
        
        uploaded_files[db_id] = {
            'name': config['name'],
            'views': [],
            'view_names': [],
            'metadata': []
        }
        
        # Screenshots for each view
        st.write(f"📸 **Screenshots ({config['views']} views needed):**")
        
        for view_i in range(config['views']):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                view_file = st.file_uploader(
                    f"Upload {config['name']} - View {view_i + 1}",
                    type=['png', 'jpg', 'jpeg'],
                    key=f"{db_id}_view_{view_i}",
                    help=f"Screenshot of view {view_i + 1} for {config['name']}"
                )
                if view_file:
                    uploaded_files[db_id]['views'].append(view_file)
            
            with col2:
                view_name = st.text_input(
                    "Optional: Enter view name",
                    placeholder="e.g., Sales Summary",
                    key=f"{db_id}_view_name_{view_i}",
                    help="Optional custom name for this view"
                )
                uploaded_files[db_id]['view_names'].append(view_name if view_name else f"View {view_i + 1}")
        
        st.divider()
        
        # Metadata files
        st.write("🗂️ **Metadata Files (DAX Studio exports):**")
        metadata_files = st.file_uploader(
            f"Upload Metadata for {config['name']}",
            type=['csv'],
            accept_multiple_files=True,
            key=f"{db_id}_metadata",
            help="Upload measures.csv, tables.csv, relationships.csv from DAX Studio"
        )
        if metadata_files:
            uploaded_files[db_id]['metadata'].extend(metadata_files)
        
        st.divider()
    
    st.session_state.uploaded_files = uploaded_files
    
    # Validation and summary
    st.subheader("📋 Upload Summary")
    
    total_views_uploaded = sum(len(files['views']) for files in uploaded_files.values())
    total_views_expected = sum(config['views'] for config in st.session_state.dashboard_config.values())
    total_metadata = sum(len(files['metadata']) for files in uploaded_files.values())
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Views Uploaded", f"{total_views_uploaded}/{total_views_expected}")
    with col2:
        st.metric("Metadata Files", total_metadata)
    with col3:
        ready = total_views_uploaded == total_views_expected and total_metadata > 0
        st.metric("Ready for Analysis", "✅ Yes" if ready else "❌ No")
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Configuration", key="back_to_config"):
            st.session_state.stage = 'dashboard_config'
            st.rerun()
    
    with col2:
        can_proceed = total_views_uploaded == total_views_expected and total_metadata > 0
        if st.button("Process Dashboards →", type="primary", disabled=not can_proceed, key="start_processing"):
            st.session_state.stage = 'processing'
            st.rerun()

# Stage 4: Processing
def render_processing():
    st.header("⚡ Processing Dashboards")
    
    if not st.session_state.processed_dashboards:
        st.write("Processing your dashboards to extract visual and metadata information...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Prepare dashboard names mapping
            dashboard_names = {}
            for db_id, config in st.session_state.dashboard_config.items():
                db_num = db_id.split('_')[1]
                dashboard_names[db_num] = config['name']
            
            # Prepare files for API
            files_to_upload = []
            
            for db_id, file_data in st.session_state.uploaded_files.items():
                db_num = db_id.split('_')[1]
                
                # Add view screenshots with custom names
                for i, view_file in enumerate(file_data['views']):
                    view_name = file_data.get('view_names', [f"View {i+1}"])[i]
                    new_filename = f"dashboard_{db_num}_view_{i+1}_{view_name}.{view_file.name.split('.')[-1]}"
                    files_to_upload.append((new_filename, view_file))
                
                # Add metadata files
                for metadata_file in file_data['metadata']:
                    new_filename = f"dashboard_{db_num}_metadata_{metadata_file.name}"
                    files_to_upload.append((new_filename, metadata_file))
            
            progress_bar.progress(0.3)
            status_text.text("Uploading files to processing API...")
            
            # Call the processing API
            API_KEY = os.getenv("API_KEY", "supersecrettoken123")
            API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
            
            files = []
            for filename, file_obj in files_to_upload:
                file_obj.seek(0)  # Reset file pointer
                files.append(('files', (filename, file_obj.read(), file_obj.type)))
            
            # Add dashboard names as form data
            dashboard_info_json = json.dumps({'dashboard_names': dashboard_names})
            
            progress_bar.progress(0.6)
            status_text.text("Analyzing visual elements and metadata...")
            
            response = requests.post(
                f"{API_BASE_URL}/api/v1/process-dashboards",
                files=files,
                data={'dashboard_info': dashboard_info_json},
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=300
            )
            
            progress_bar.progress(0.9)
            status_text.text("Finalizing results...")
            
            if response.status_code == 200:
                result = response.json()
                st.session_state.processed_dashboards = result['data']['dashboards']
                progress_bar.progress(1.0)
                status_text.text("✅ Processing completed successfully!")
                
                st.success("Dashboard processing complete! Click below to review the results.")
                if st.button("Review Results →", type="primary"):
                    st.session_state.stage = 'review'
                    st.rerun()
            else:
                st.error(f"Processing failed: {response.text}")
                if st.button("← Back to File Upload", key="back_to_upload_error"):
                    st.session_state.stage = 'file_upload'
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error during processing: {str(e)}")
            if st.button("← Back to File Upload", key="back_to_upload_exception"):
                st.session_state.stage = 'file_upload'
                st.rerun()
    else:
        st.success("✅ Processing completed!")
        if st.button("Review Results →", type="primary"):
            st.session_state.stage = 'review'
            st.rerun()

# Stage 5: Review & Confirm
def render_review():
    st.header("👀 Review & Confirm")
    
    if not st.session_state.processed_dashboards:
        st.error("No processed dashboards found. Please go back and process your dashboards first.")
        return
    
    st.write("Review the extracted information from each dashboard before running similarity analysis:")
    
    dashboards = st.session_state.processed_dashboards
    
    for dashboard in dashboards:
        dashboard_name = dashboard['dashboard_name']
        
        with st.expander(f"📊 {dashboard_name}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 Visual Analysis Summary")
                st.metric("Total Visual Elements Found", dashboard.get('visual_elements_count', 0))
                st.metric("Number of Views/Pages", dashboard.get('total_pages', 0))
                
                # Show visual types breakdown if available
                metadata_summary = dashboard.get('metadata_summary', {})
                if 'visual_types_distribution' in metadata_summary:
                    visual_types = metadata_summary['visual_types_distribution']
                    if visual_types:
                        st.write("**Chart Types Detected:**")
                        for chart_type, count in visual_types.items():
                            st.write(f"• {count} {chart_type}")
                    else:
                        st.write("• No specific chart types detected")
                else:
                    st.write("• Chart type analysis pending")
                
                if dashboard.get('visual_elements_count', 0) > 0:
                    st.write(f"**Detected Filters:** {dashboard.get('filters_count', 'N/A')}")
                else:
                    st.write("**Detected Filters:** Visual analysis pending")
            
            with col2:
                st.subheader("🗂️ Metadata Summary")
                st.metric("Measures Found", dashboard.get('measures_count', 0))
                st.metric("Tables Found", dashboard.get('tables_count', 0))
                st.metric("Relationships Found", dashboard.get('relationships_count', 0))
                
                # Show complexity if available
                if metadata_summary.get('complexity_score'):
                    complexity = metadata_summary['complexity_score']
                    st.metric("Complexity Score", f"{complexity:.1f}/10")
            
            # Screenshot Previews
            if dashboard.get('view_summaries'):
                st.subheader("📸 Screenshot Previews")
                view_cols = st.columns(min(len(dashboard['view_summaries']), 3))
                
                for i, view_summary in enumerate(dashboard['view_summaries'][:3]):  # Limit to 3 previews
                    with view_cols[i % 3]:
                        try:
                            import base64
                            image_data = base64.b64decode(view_summary['data'])
                            st.image(image_data, caption=view_summary['name'], use_column_width=True)
                        except Exception as e:
                            st.write(f"Could not display {view_summary['name']}")
                
                if len(dashboard['view_summaries']) > 3:
                    st.write(f"... and {len(dashboard['view_summaries']) - 3} more views")
            else:
                st.info("No screenshot previews available")
    
    # Summary section
    st.divider()
    st.subheader("📊 Analysis Summary")
    
    total_dashboards = len(dashboards)
    total_views = sum(d.get('total_pages', 0) for d in dashboards)
    total_elements = sum(d.get('visual_elements_count', 0) for d in dashboards)
    total_measures = sum(d.get('measures_count', 0) for d in dashboards)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Dashboards Ready", total_dashboards)
    with col2:
        st.metric("Total Views", total_views)
    with col3:
        st.metric("Visual Elements", total_elements)
    with col4:
        st.metric("Total Measures", total_measures)
    
    if total_dashboards >= 2:
        st.success(f"✅ Ready to analyze {total_dashboards} dashboards for similarity!")
    else:
        st.warning("⚠️ Need at least 2 dashboards for similarity comparison.")
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Processing", key="back_to_processing"):
            st.session_state.stage = 'processing'
            st.rerun()
    
    with col2:
        can_proceed = total_dashboards >= 2
        if st.button("Confirm and Run Similarity Analysis →", type="primary", disabled=not can_proceed, key="run_similarity"):
            st.session_state.stage = 'analysis'
            st.rerun()

# Stage 6: Analysis
def render_analysis():
    st.header("🔄 Running Analysis")
    
    if not st.session_state.analysis_results:
        analysis_method = st.session_state.get('analysis_method', 'Local Batch Analysis')
        
        if analysis_method == "REST API Analysis":
            st.write("Analyzing your selected reports using automated Power BI API extraction...")
            render_api_analysis()
        else:
            st.write("Analyzing your dashboards using AI-powered comparison...")
            render_local_analysis()
    else:
        st.success("✅ Analysis completed!")
        if st.button("View Results →", type="primary"):
            st.session_state.stage = 'results'
            st.rerun()

def render_local_analysis():
    """Handle local file-based similarity analysis"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Check if we have processed dashboards from previous stage
        if not st.session_state.processed_dashboards:
            st.error("No processed dashboard data found. Please go back and complete the processing stage.")
            if st.button("← Back to Review", key="back_to_review_error"):
                st.session_state.stage = 'review'
                st.rerun()
            return
        
        progress_bar.progress(0.2)
        status_text.text("Initializing similarity analysis...")
        
        # Extract dashboard IDs and names from processed data
        dashboard_data = []
        for dashboard in st.session_state.processed_dashboards:
            dashboard_data.append({
                'dashboard_id': dashboard['dashboard_id'],
                'dashboard_name': dashboard['dashboard_name']
            })
        
        progress_bar.progress(0.5)
        status_text.text("Running similarity analysis...")
        
        # Call the new similarity analysis API
        API_KEY = os.getenv("API_KEY", "supersecrettoken123")
        API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/run-similarity",
            json={
                'dashboards': dashboard_data,
                'similarity_threshold': 0.7,
                'weights': {
                    'measures': 0.4,
                    'visuals': 0.3,
                    'data_model': 0.2,
                    'layout': 0.1
                }
            },
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=300
        )
        
        progress_bar.progress(0.9)
        status_text.text("Processing similarity results...")
        
        if response.status_code == 200:
            st.session_state.analysis_results = response.json()
            progress_bar.progress(1.0)
            status_text.text("✅ Similarity analysis completed successfully!")
            
            st.success("Analysis completed! Click below to view results.")
            if st.button("View Results →", type="primary"):
                st.session_state.stage = 'results'
                st.rerun()
        else:
            st.error(f"Similarity analysis failed: {response.text}")
            if st.button("← Back to Review", key="back_to_review_error"):
                st.session_state.stage = 'review'
                st.rerun()
    
    except Exception as e:
        st.error(f"Error during similarity analysis: {str(e)}")
        if st.button("← Back to Review", key="back_to_review_exception"):
            st.session_state.stage = 'review'
            st.rerun()

def render_api_analysis():
    """Handle API-based analysis"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        progress_bar.progress(0.2)
        status_text.text("Extracting report metadata from Power BI Service...")
        
        # Get selected reports data
        pbi_client = st.session_state.pbi_client
        selected_reports = st.session_state.selected_reports
        
        # For each selected report, extract metadata and pages
        report_data = []
        
        progress_bar.progress(0.4)
        status_text.text("Processing report pages and datasets...")
        
        for report_name in selected_reports:
            # Extract report information (this would need actual API implementation)
            # For now, we'll simulate the process
            report_info = {
                'name': report_name,
                'pages': ['Overview', 'Details', 'Summary'],  # Mock data
                'measures': [],  # Would be extracted via API
                'tables': [],    # Would be extracted via API
                'relationships': []  # Would be extracted via API
            }
            report_data.append(report_info)
        
        progress_bar.progress(0.7)
        status_text.text("Running similarity analysis...")
        
        # Call API analysis endpoint for Power BI data
        API_KEY = os.getenv("API_KEY", "supersecrettoken123")
        API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # This would need a new API endpoint for Power BI data
        response = requests.post(
            f"{API_BASE_URL}/api/v1/api-analysis",
            json={'reports': report_data},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=300
        )
        
        progress_bar.progress(0.9)
        status_text.text("Processing results...")
        
        if response.status_code == 200:
            st.session_state.analysis_results = response.json()
            progress_bar.progress(1.0)
            status_text.text("✅ Analysis completed successfully!")
            
            st.success("Analysis completed! Click below to view results.")
            if st.button("View Results →", type="primary"):
                st.session_state.stage = 'results'
                st.rerun()
        else:
            # Fallback to mock data for demo
            st.warning("API analysis endpoint not yet implemented. Generating demo results...")
            
            mock_results = {
                'success': True,
                'message': 'Mock API analysis completed',
                'data': {
                    'dashboards_processed': len(selected_reports),
                    'total_views': sum(3 for _ in selected_reports),  # Mock 3 pages per report
                    'similarity_pairs': max(0, len(selected_reports) * (len(selected_reports) - 1) // 2),
                    'consolidation_groups': max(0, len(selected_reports) // 2)
                }
            }
            
            st.session_state.analysis_results = mock_results
            progress_bar.progress(1.0)
            status_text.text("✅ Demo analysis completed!")
            
            st.info("🔬 **Demo Mode:** This shows how API analysis would work. Real implementation would extract actual Power BI metadata.")
            if st.button("View Demo Results →", type="primary"):
                st.session_state.stage = 'results'
                st.rerun()
    
    except Exception as e:
        st.error(f"Error during API analysis: {str(e)}")
        if st.button("← Back to Workspace Selection", key="back_to_workspace_error"):
            st.session_state.stage = 'workspace_selection'
            st.rerun()

def render_detailed_comparison(similarity_score, processed_dashboards):
    """Render detailed side-by-side comparison of two dashboards"""
    
    dashboard1_name = similarity_score['dashboard1_name']
    dashboard2_name = similarity_score['dashboard2_name']
    breakdown = similarity_score.get('breakdown', {})
    total_score = similarity_score['total_score']
    
    # Header with overall similarity
    st.markdown(f"### 🔬 **{dashboard1_name}** ↔ **{dashboard2_name}**")
    
    # Overall similarity score
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Create a circular progress indicator
        similarity_pct = total_score * 100
        if similarity_pct >= 85:
            st.success(f"🎯 **Overall Similarity: {similarity_pct:.1f}%** (Highly Similar)")
        elif similarity_pct >= 70:
            st.warning(f"🎯 **Overall Similarity: {similarity_pct:.1f}%** (Moderately Similar)")
        else:
            st.info(f"🎯 **Overall Similarity: {similarity_pct:.1f}%** (Low Similarity)")
    
    st.divider()
    
    # Detailed breakdown scores
    st.markdown("#### 📊 **Similarity Breakdown**")
    
    # Create comparison metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        measures_score = breakdown.get('measures_score', 0) * 100
        st.metric(
            label="📈 Measures",
            value=f"{measures_score:.1f}%",
            delta=f"Weight: 40%",
            help="Similarity of DAX measures and calculations"
        )
    
    with col2:
        visuals_score = breakdown.get('visuals_score', 0) * 100
        st.metric(
            label="📊 Visuals",
            value=f"{visuals_score:.1f}%",
            delta=f"Weight: 30%",
            help="Similarity of chart types and visualizations"
        )
    
    with col3:
        data_model_score = breakdown.get('data_model_score', 0) * 100
        st.metric(
            label="🏗️ Data Model", 
            value=f"{data_model_score:.1f}%",
            delta=f"Weight: 20%",
            help="Similarity of tables, relationships, and data structure"
        )
    
    with col4:
        layout_score = breakdown.get('layout_score', 0) * 100
        st.metric(
            label="🎨 Layout",
            value=f"{layout_score:.1f}%", 
            delta=f"Weight: 10%",
            help="Similarity of dashboard layout and positioning"
        )
    
    with col5:
        filters_score = breakdown.get('filters_score', 0) * 100
        st.metric(
            label="🔽 Filters",
            value=f"{filters_score:.1f}%",
            delta=f"Additional",
            help="Similarity of filters and slicers"
        )
    
    st.divider()
    
    # Side-by-side dashboard details
    st.markdown("#### 🔍 **Dashboard Details Comparison**")
    
    # Find dashboard data from processed_dashboards
    dashboard1_data = None
    dashboard2_data = None
    
    if processed_dashboards:
        for dashboard in processed_dashboards:
            if dashboard['dashboard_name'] == dashboard1_name:
                dashboard1_data = dashboard
            elif dashboard['dashboard_name'] == dashboard2_name:
                dashboard2_data = dashboard
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"##### 📋 **{dashboard1_name}**")
        if dashboard1_data:
            render_dashboard_summary(dashboard1_data, side="left")
        else:
            st.info("Dashboard details not available")
    
    with col2:
        st.markdown(f"##### 📋 **{dashboard2_name}**")
        if dashboard2_data:
            render_dashboard_summary(dashboard2_data, side="right")
        else:
            st.info("Dashboard details not available")
    
    st.divider()
    
    # Consolidation recommendations
    st.markdown("#### 💡 **Consolidation Recommendations**")
    
    if similarity_pct >= 85:
        st.success("🚀 **High Priority for Merging**")
        st.markdown("""
        **Recommended Action:** Merge these dashboards immediately
        
        **Rationale:** 
        - Very high overall similarity (85%+)
        - Likely serving duplicate purposes
        - Strong consolidation candidate
        
        **Benefits:**
        - Eliminate redundancy
        - Reduce maintenance overhead  
        - Improve user experience consistency
        - Lower licensing costs
        """)
    elif similarity_pct >= 70:
        st.warning("🔍 **Moderate Priority for Review**")
        st.markdown("""
        **Recommended Action:** Manual review for partial consolidation
        
        **Rationale:**
        - Moderate similarity (70-84%)
        - May have overlapping but distinct purposes
        - Consolidation opportunities exist
        
        **Next Steps:**
        - Detailed business requirements review
        - Identify shared components for standardization
        - Consider partial merging of similar sections
        """)
    else:
        st.info("📝 **Low Priority**")
        st.markdown("""
        **Recommended Action:** Monitor for future changes
        
        **Rationale:**
        - Low similarity (<70%)
        - Likely serve different business purposes
        - Minimal consolidation benefit
        
        **Considerations:**
        - Keep as separate dashboards
        - May benefit from common design standards
        - Review periodically as requirements evolve
        """)

def render_dashboard_summary(dashboard_data, side="left"):
    """Render summary information for a single dashboard"""
    
    # Basic information
    st.write(f"**Dashboard ID:** `{dashboard_data.get('dashboard_id', 'N/A')}`")
    
    # Visual analysis summary
    if 'visual_analysis' in dashboard_data:
        visual_data = dashboard_data['visual_analysis']
        st.write(f"**Total Visuals:** {visual_data.get('total_visuals', 0)}")
        
        # Visual types breakdown
        visual_types = visual_data.get('visual_types', {})
        if visual_types:
            st.write("**Visual Types:**")
            for vtype, count in visual_types.items():
                st.write(f"  • {vtype}: {count}")
        
        # KPIs
        kpis = visual_data.get('kpis', [])
        if kpis:
            st.write(f"**KPIs:** {len(kpis)}")
    
    # Metadata summary
    if 'metadata_summary' in dashboard_data:
        metadata = dashboard_data['metadata_summary']
        st.write(f"**Measures:** {metadata.get('total_measures', 0)}")
        st.write(f"**Tables:** {metadata.get('total_tables', 0)}")
        st.write(f"**Relationships:** {metadata.get('total_relationships', 0)}")
        
        complexity = metadata.get('complexity_score', 0)
        if complexity > 7:
            st.write(f"**Complexity:** 🔴 High ({complexity:.1f}/10)")
        elif complexity > 4:
            st.write(f"**Complexity:** 🟡 Medium ({complexity:.1f}/10)")
        else:
            st.write(f"**Complexity:** 🟢 Low ({complexity:.1f}/10)")
    
    # Screenshot preview (if available)
    if 'views' in dashboard_data and dashboard_data['views']:
        first_view = dashboard_data['views'][0]
        if 'screenshot_data' in first_view:
            try:
                # Decode base64 screenshot
                import base64
                screenshot_data = base64.b64decode(first_view['screenshot_data'])
                st.image(screenshot_data, caption=f"Preview: {first_view.get('view_name', 'View 1')}", use_column_width=True)
            except Exception:
                st.info("Screenshot preview not available")

# Stage 5: Results
def render_results():
    st.header("📈 Analysis Results")
    
    if not st.session_state.analysis_results:
        st.error("No analysis results found. Please run the analysis first.")
        return
    
    results = st.session_state.analysis_results
    
    # Summary metrics
    st.subheader("📊 Analysis Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Dashboards Analyzed", results['data'].get('dashboards_processed', 0))
    with col2:
        st.metric("Total Views", results['data'].get('total_views', 0))
    with col3:
        st.metric("Similarity Pairs", results['data'].get('similarity_pairs', 0))
    with col4:
        st.metric("Consolidation Groups", results['data'].get('consolidation_groups', 0))
    
    st.divider()
    
    # Get detailed results from API
    try:
        API_KEY = os.getenv("API_KEY", "supersecrettoken123")
        API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # Get similarity matrix
        similarity_response = requests.get(
            f"{API_BASE_URL}/api/v1/similarity-matrix",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        
        if similarity_response.status_code == 200:
            similarity_data = similarity_response.json()
            
            # Display similarity matrix
            st.subheader("🔍 Interactive Dashboard Similarity Matrix")
            
            # Create similarity matrix visualization
            if similarity_data.get('similarity_scores'):
                scores = similarity_data['similarity_scores']
                
                # Extract dashboard names and create matrix
                dashboard_names = list(set([s['dashboard1_name'] for s in scores] + [s['dashboard2_name'] for s in scores]))
                n_dashboards = len(dashboard_names)
                
                if n_dashboards > 1:
                    # Create similarity matrix
                    similarity_matrix = [[0 for _ in range(n_dashboards)] for _ in range(n_dashboards)]
                    
                    # Fill diagonal with 100%
                    for i in range(n_dashboards):
                        similarity_matrix[i][i] = 100
                    
                    # Fill matrix with similarity scores
                    for score in scores:
                        i = dashboard_names.index(score['dashboard1_name'])
                        j = dashboard_names.index(score['dashboard2_name'])
                        similarity_matrix[i][j] = score['total_score'] * 100
                        similarity_matrix[j][i] = score['total_score'] * 100
                    
                    # Create interactive heatmap
                    fig = px.imshow(
                        similarity_matrix,
                        labels=dict(x="Dashboard", y="Dashboard", color="Similarity %"),
                        x=dashboard_names,
                        y=dashboard_names,
                        color_continuous_scale="Blues",
                        title="Click on a cell to see detailed breakdown"
                    )
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Interactive dashboard pair selection
                    st.subheader("🔬 Detailed Similarity Comparison")
                    
                    # Dashboard pair selector
                    col1, col2 = st.columns(2)
                    with col1:
                        dashboard1 = st.selectbox("Select First Dashboard", dashboard_names, key="dash1_select")
                    with col2:
                        dashboard2 = st.selectbox("Select Second Dashboard", 
                                                [name for name in dashboard_names if name != dashboard1], 
                                                key="dash2_select")
                    
                    if dashboard1 and dashboard2:
                        # Find the similarity score for this pair
                        selected_score = None
                        for score in scores:
                            if ((score['dashboard1_name'] == dashboard1 and score['dashboard2_name'] == dashboard2) or
                                (score['dashboard1_name'] == dashboard2 and score['dashboard2_name'] == dashboard1)):
                                selected_score = score
                                break
                        
                        if selected_score:
                            render_detailed_comparison(selected_score, st.session_state.processed_dashboards)
                        else:
                            st.info("No similarity data available for this pair.")
                    
                    st.divider()
                    
                    # Consolidation recommendations
                    st.subheader("🎯 Consolidation Recommendations")
                    
                    candidates = []
                    for score in scores:
                        similarity_pct = score['total_score'] * 100
                        if similarity_pct >= 70:
                            candidates.append({
                                'Dashboard 1': score['dashboard1_name'],
                                'Dashboard 2': score['dashboard2_name'],
                                'Similarity': f"{similarity_pct:.1f}%",
                                'Action': 'Merge' if similarity_pct >= 85 else 'Review',
                                'breakdown': score.get('breakdown', {})
                            })
                    
                    if candidates:
                        # Display recommendations with expandable details
                        for i, candidate in enumerate(candidates):
                            with st.expander(f"🔗 {candidate['Dashboard 1']} ↔ {candidate['Dashboard 2']} - {candidate['Similarity']} ({candidate['Action']})"):
                                col1, col2, col3 = st.columns(3)
                                
                                breakdown = candidate['breakdown']
                                with col1:
                                    st.metric("Measures Similarity", f"{breakdown.get('measures_score', 0) * 100:.1f}%")
                                    st.metric("Visuals Similarity", f"{breakdown.get('visuals_score', 0) * 100:.1f}%")
                                with col2:
                                    st.metric("Data Model Similarity", f"{breakdown.get('data_model_score', 0) * 100:.1f}%")
                                    st.metric("Layout Similarity", f"{breakdown.get('layout_score', 0) * 100:.1f}%")
                                with col3:
                                    st.metric("Filters Similarity", f"{breakdown.get('filters_score', 0) * 100:.1f}%")
                                
                                # Action recommendation details
                                if candidate['Action'] == 'Merge':
                                    st.success("💡 **Recommendation:** These dashboards are highly similar and should be considered for merging.")
                                    st.write("**Benefits:** Reduced maintenance overhead, improved consistency, simplified user experience.")
                                else:
                                    st.warning("💡 **Recommendation:** These dashboards show significant similarity and should be reviewed for potential consolidation.")
                                    st.write("**Next Steps:** Manual review recommended to identify consolidation opportunities.")
                        
                        # Summary metrics
                        st.divider()
                        merge_count = len([c for c in candidates if c['Action'] == 'Merge'])
                        review_count = len([c for c in candidates if c['Action'] == 'Review'])
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("🚀 High Similarity (Merge)", merge_count)
                        with col2:
                            st.metric("🔍 Medium Similarity (Review)", review_count)
                        with col3:
                            potential_reduction = merge_count + (review_count // 2)
                            st.metric("📉 Potential Dashboard Reduction", potential_reduction)
                    else:
                        st.info("No high-similarity pairs found (threshold: 70%)")
            
    except Exception as e:
        st.error(f"Error fetching detailed results: {str(e)}")
    
    # Report generation
    st.subheader("📄 Generate Reports")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Download JSON Report", type="secondary"):
            try:
                API_KEY = os.getenv("API_KEY", "supersecrettoken123")
                API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
                
                report_response = requests.post(
                    f"{API_BASE_URL}/api/v1/generate-report?format=json",
                    headers={"Authorization": f"Bearer {API_KEY}"}
                )
                
                if report_response.status_code == 200:
                    report_data = report_response.json()
                    st.download_button(
                        label="📥 Download JSON Report",
                        data=json.dumps(report_data, indent=2),
                        file_name=f"dashboard_consolidation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                else:
                    st.error("Failed to generate JSON report")
            except Exception as e:
                st.error(f"Error generating JSON report: {str(e)}")
    
    with col2:
        if st.button("📊 Generate Excel Report", type="secondary"):
            st.info("Excel report generation will be available in the next update.")
    
    # Start new analysis
    st.divider()
    if st.button("🔄 Start New Analysis", type="primary"):
        # Reset session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# API Credentials Stage
def render_api_credentials():
    st.header("🔐 Power BI API Credentials")
    
    st.write("""
    Enter your Azure AD application credentials to connect to Power BI Service.
    If you don't have these credentials, contact your Power BI administrator.
    """)
    
    with st.form("credentials_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            tenant_id = st.text_input(
                "Tenant ID",
                value=st.session_state.api_credentials.get('tenant_id', ''),
                help="Your Azure AD tenant ID (GUID)"
            )
            
            client_id = st.text_input(
                "Client ID",
                value=st.session_state.api_credentials.get('client_id', ''),
                help="Azure AD app registration client ID"
            )
        
        with col2:
            client_secret = st.text_input(
                "Client Secret",
                type="password",
                value=st.session_state.api_credentials.get('client_secret', ''),
                help="Azure AD app registration client secret"
            )
            
            st.write("**Required Permissions:**")
            st.write("• Dataset.ReadWrite.All")
            st.write("• Report.ReadWrite.All")
            st.write("• Workspace.ReadWrite.All")
        
        submit_credentials = st.form_submit_button("Connect to Power BI", type="primary")
        
        if submit_credentials:
            if tenant_id and client_id and client_secret:
                st.session_state.api_credentials = {
                    'tenant_id': tenant_id,
                    'client_id': client_id,
                    'client_secret': client_secret
                }
                
                # Test connection
                try:
                    with st.spinner("Testing connection to Power BI Service..."):
                        # Import PowerBI client here to avoid issues if not available
                        from power_bi_api_client import PowerBIAPIClient
                        
                        pbi_client = PowerBIAPIClient(
                            tenant_id=tenant_id,
                            client_id=client_id,
                            client_secret=client_secret,
                            mock_mode=False
                        )
                        
                        # Test authentication
                        workspaces = pbi_client.get_workspaces()
                        
                        st.success("✅ Connection successful!")
                        st.session_state.pbi_client = pbi_client
                        st.session_state.stage = 'workspace_selection'
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Connection failed: {str(e)}")
                    st.info("💡 **Tip:** Try using Mock Mode for testing by setting POWERBI_CLIENT_ID in your .env file to 'mock'")
                    
                    # Fallback to mock mode
                    if st.button("Use Mock Mode for Testing", key="mock_mode"):
                        try:
                            from power_bi_api_client import PowerBIAPIClient
                            pbi_client = PowerBIAPIClient(mock_mode=True)
                            st.session_state.pbi_client = pbi_client
                            st.session_state.stage = 'workspace_selection'
                            st.rerun()
                        except Exception as mock_error:
                            st.error(f"Mock mode also failed: {str(mock_error)}")
            else:
                st.error("Please fill in all credential fields.")
    
    # Navigation
    if st.button("← Back to Method Choice", key="back_to_method_from_creds"):
        st.session_state.stage = 'method_choice'
        st.rerun()

# Workspace Selection Stage  
def render_workspace_selection():
    st.header("🏢 Select Workspaces and Reports")
    
    st.write("Choose the workspaces and reports you want to analyze for consolidation opportunities.")
    
    try:
        pbi_client = st.session_state.pbi_client
        
        # Get workspaces
        with st.spinner("Loading workspaces..."):
            workspaces = pbi_client.get_workspaces()
        
        if workspaces:
            st.subheader("📂 Available Workspaces")
            
            workspace_options = {ws['name']: ws['id'] for ws in workspaces}
            selected_workspace_names = st.multiselect(
                "Select workspaces to analyze:",
                options=list(workspace_options.keys()),
                default=st.session_state.selected_workspaces,
                help="Choose one or more workspaces containing the reports you want to compare"
            )
            
            st.session_state.selected_workspaces = selected_workspace_names
            
            if selected_workspace_names:
                st.divider()
                st.subheader("📊 Available Reports")
                
                all_reports = []
                for workspace_name in selected_workspace_names:
                    workspace_id = workspace_options[workspace_name]
                    
                    with st.spinner(f"Loading reports from {workspace_name}..."):
                        reports = pbi_client.get_reports(workspace_id)
                    
                    for report in reports:
                        report['workspace_name'] = workspace_name
                        all_reports.append(report)
                
                if all_reports:
                    report_options = {}
                    for report in all_reports:
                        display_name = f"{report['name']} ({report['workspace_name']})"
                        report_options[display_name] = {
                            'id': report['id'],
                            'workspace_id': report.get('workspace_id'),
                            'workspace_name': report['workspace_name']
                        }
                    
                    selected_report_names = st.multiselect(
                        "Select reports to compare:",
                        options=list(report_options.keys()),
                        default=st.session_state.selected_reports,
                        help="Choose 2 or more reports to compare for similarity"
                    )
                    
                    st.session_state.selected_reports = selected_report_names
                    
                    if len(selected_report_names) >= 2:
                        st.success(f"✅ Selected {len(selected_report_names)} reports for analysis")
                        
                        # Show summary
                        st.subheader("📋 Analysis Summary")
                        st.info(f"""
                        **Workspaces:** {len(selected_workspace_names)}  
                        **Reports:** {len(selected_report_names)}  
                        **Analysis Type:** Automated metadata extraction and visual comparison
                        """)
                        
                        # Navigation
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("← Back to Credentials", key="back_to_creds"):
                                st.session_state.stage = 'api_credentials'
                                st.rerun()
                        
                        with col2:
                            if st.button("Start Analysis →", type="primary", key="start_api_analysis"):
                                st.session_state.stage = 'analysis'
                                st.rerun()
                    else:
                        st.warning("Please select at least 2 reports to compare.")
                else:
                    st.warning("No reports found in the selected workspaces.")
            
        else:
            st.error("No workspaces found. Please check your permissions.")
    
    except Exception as e:
        st.error(f"Error loading workspace data: {str(e)}")
        if st.button("← Back to Credentials", key="back_to_creds_error"):
            st.session_state.stage = 'api_credentials'
            st.rerun()

# Main app
def main():
    load_custom_css()
    init_session_state()
    
    render_header()
    render_progress()
    render_sidebar()
    
    if st.session_state.stage == 'method_choice':
        render_method_choice()
    elif st.session_state.stage == 'dashboard_config':
        render_dashboard_config()
    elif st.session_state.stage == 'file_upload':
        render_file_upload()
    elif st.session_state.stage == 'processing':
        render_processing()
    elif st.session_state.stage == 'review':
        render_review()
    elif st.session_state.stage == 'api_credentials':
        render_api_credentials()
    elif st.session_state.stage == 'workspace_selection':
        render_workspace_selection()
    elif st.session_state.stage == 'analysis':
        render_analysis()
    elif st.session_state.stage == 'results':
        render_results()

if __name__ == "__main__":
    main()