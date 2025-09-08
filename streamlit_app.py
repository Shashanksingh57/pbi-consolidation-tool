# streamlit_app.py - Refactored Power BI Dashboard Consolidation Tool with Batch Workflow

import os
import io
import json
import re
import requests
import shutil
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
import time

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
    
    .detailed-analysis-box {
        background-color: #f8f9fa;
        border-left: 4px solid #0C62FB;
        padding: 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    
    .confidence-score {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    
    .confidence-high { background-color: #d4edda; color: #155724; }
    .confidence-medium { background-color: #fff3cd; color: #856404; }
    .confidence-low { background-color: #f8d7da; color: #721c24; }
    
    .visual-element-card {
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.25rem 0;
        background-color: #ffffff;
    }
    
    /* Removed visibility hidden styles that might cause blank page */
    </style>
    """, unsafe_allow_html=True)

# ─── OUTPUT MANAGEMENT FUNCTIONS ───────────────────────────────────────────────

def create_run_directory(execution_mode: str) -> Path:
    """Create a unique timestamped directory for this run"""
    base_dir = Path("/Users/shashank.singh/Library/CloudStorage/OneDrive-Slalom/Desktop/AI PBI Consolidation Test Cases Review")
    
    # Create base directory if it doesn't exist
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped run directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    mode_suffix = execution_mode.replace(" ", "").replace("&", "")
    run_dir = base_dir / f"Run_{timestamp}_{mode_suffix}"
    
    # Create directory structure
    run_dir.mkdir(exist_ok=True)
    (run_dir / "profiles").mkdir(exist_ok=True)
    (run_dir / "analysis_details").mkdir(exist_ok=True)
    (run_dir / "screenshots").mkdir(exist_ok=True)
    (run_dir / "confidence_reports").mkdir(exist_ok=True)
    (run_dir / "logs").mkdir(exist_ok=True)
    
    if "Compare" in execution_mode:
        (run_dir / "similarity_analysis").mkdir(exist_ok=True)
        (run_dir / "recommendations").mkdir(exist_ok=True)
        (run_dir / "reports").mkdir(exist_ok=True)
    
    return run_dir

def run_pre_execution_checks(execution_mode: str, processed_dashboards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run comprehensive pre-execution validation and setup"""
    checks_result = {
        "success": True,
        "warnings": [],
        "errors": [],
        "info": []
    }
    
    # 1. API Connectivity Check
    try:
        API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
        API_KEY = os.getenv("API_KEY", "supersecrettoken123")
        response = requests.get(f"{API_BASE_URL}/", headers={"Authorization": f"Bearer {API_KEY}"}, timeout=5)
        if response.status_code == 200:
            checks_result["info"].append("✅ Backend API connectivity verified")
        else:
            checks_result["errors"].append(f"❌ Backend API returned status {response.status_code}")
            checks_result["success"] = False
    except Exception as e:
        checks_result["errors"].append(f"❌ Cannot connect to backend API: {str(e)}")
        checks_result["success"] = False
    
    # 2. OpenAI API Check (for Extract mode)
    if "Extract" in execution_mode or "Full" in execution_mode:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            checks_result["info"].append("✅ OpenAI API key configured")
        else:
            checks_result["warnings"].append("⚠️ OpenAI API key not found - visual analysis may fail")
    
    # 3. Storage Space Check
    try:
        base_path = "/Users/shashank.singh/Library/CloudStorage/OneDrive-Slalom/Desktop/AI PBI Consolidation Test Cases Review"
        free_space_gb = shutil.disk_usage(base_path)[2] / (1024**3)
        if free_space_gb > 1:
            checks_result["info"].append(f"✅ Available disk space: {free_space_gb:.1f} GB")
        else:
            checks_result["warnings"].append(f"⚠️ Low disk space: {free_space_gb:.1f} GB")
    except Exception as e:
        checks_result["warnings"].append(f"⚠️ Cannot check disk space: {str(e)}")
    
    # 4. Profile Data Check (for Compare mode)
    if "Compare" in execution_mode and not "Full" in execution_mode:
        if hasattr(st.session_state, 'extracted_profiles') and st.session_state.extracted_profiles:
            profile_count = len(st.session_state.extracted_profiles)
            if profile_count >= 2:
                checks_result["info"].append(f"✅ Found {profile_count} profiles ready for comparison")
            else:
                checks_result["errors"].append("❌ Need at least 2 profiles for comparison")
                checks_result["success"] = False
        else:
            checks_result["errors"].append("❌ No extracted profiles found - run Extract & Profile first")
            checks_result["success"] = False
    
    # 5. Input File Validation (for Extract mode)
    if "Extract" in execution_mode or "Full" in execution_mode:
        if hasattr(st.session_state, 'uploaded_files') and st.session_state.uploaded_files:
            file_count = sum(len(data.get('views', []) + data.get('metadata', []))
                           for data in st.session_state.uploaded_files.values())
            checks_result["info"].append(f"✅ Found {file_count} files ready for processing")
        else:
            checks_result["errors"].append("❌ No uploaded files found")
            checks_result["success"] = False
    
    # Convert to expected format for UI
    ui_checks = {}
    
    # Convert errors to failed checks
    for i, error in enumerate(checks_result["errors"]):
        ui_checks[f"Error {i+1}"] = {"passed": False, "message": error}
    
    # Convert info to passed checks
    for i, info in enumerate(checks_result["info"]):
        ui_checks[f"Check {i+1}"] = {"passed": True, "message": info}
    
    # Convert warnings to passed checks with warning message
    for i, warning in enumerate(checks_result["warnings"]):
        ui_checks[f"Warning {i+1}"] = {"passed": True, "message": warning}
    
    return ui_checks

def export_profiles_to_directory(output_dir: Path, processed_dashboards: List[Dict[str, Any]]) -> None:
    """Export dashboard profiles to JSON files in the specified directory"""
    try:
        # Create profiles subdirectory
        profiles_dir = output_dir / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        
        # Export each dashboard profile
        for dashboard in processed_dashboards:
            dashboard_name = dashboard.get('dashboard_name', 'Unknown')
            safe_name = re.sub(r'[^\w\-_]', '_', dashboard_name)
            
            profile_file = profiles_dir / f"{safe_name}_profile.json"
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(dashboard, f, indent=2, default=str)
        
        # Create summary file
        summary = {
            "export_timestamp": datetime.now().isoformat(),
            "total_profiles": len(processed_dashboards),
            "dashboard_names": [d.get('dashboard_name', 'Unknown') for d in processed_dashboards],
            "export_mode": "Extract & Profile Only"
        }
        
        summary_file = output_dir / "export_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
            
        st.info(f"📁 Exported {len(processed_dashboards)} profiles to {profiles_dir}")
        
    except Exception as e:
        st.error(f"Failed to export profiles: {str(e)}")

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
    st.write("**Give your dashboards meaningful names instead of 'Dashboard 1', 'Dashboard 2':**")
    
    dashboard_config = {}
    
    for i in range(1, num_dashboards + 1):
        st.markdown(f"### Dashboard {i} Configuration")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            name = st.text_input(
                f"📊 Dashboard {i} Name",
                value=f"Dashboard {i}",
                key=f"dashboard_{i}_name",
                help=f"Enter a descriptive name like 'Sales Performance Dashboard' or 'Financial KPIs'"
            )
        
        with col2:
            num_views = st.number_input(
                f"Number of Views",
                min_value=1,
                max_value=20,
                value=1,
                key=f"dashboard_{i}_views",
                help="How many screenshot pages for this dashboard?"
            )
        
        dashboard_config[f"dashboard_{i}"] = {
            'name': name,
            'views': num_views
        }
        
        st.markdown("---")
    
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
    st.header("⚡ Phase 1: Dashboard Profile Extraction")
    
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
            
            progress_bar.progress(0.3)
            status_text.text("Phase 1: Extracting dashboard profiles...")
            
            # Process each dashboard individually using Phase 1 API
            extracted_profiles = []
            total_dashboards = len(st.session_state.dashboard_config)
            
            for idx, (db_id, config) in enumerate(st.session_state.dashboard_config.items()):
                db_num = db_id.split('_')[1]
                dashboard_name = config['name']
                user_provided_name = config['name'] if config['name'] != f"Dashboard {db_num}" else None
                
                # Update progress
                progress = 0.3 + (idx / total_dashboards) * 0.5
                progress_bar.progress(progress)
                status_text.text(f"Phase 1: Extracting profile for '{dashboard_name}' ({idx+1}/{total_dashboards})")
                
                # Prepare files for this specific dashboard
                dashboard_files = []
                file_data = st.session_state.uploaded_files.get(db_id, {})
                
                # Add view screenshots
                for i, view_file in enumerate(file_data.get('views', [])):
                    view_name = file_data.get('view_names', [f"View {i+1}"])[i]
                    new_filename = f"dashboard_{db_num}_view_{i+1}_{view_name}.{view_file.name.split('.')[-1]}"
                    dashboard_files.append((new_filename, view_file))
                
                # Add metadata files
                for metadata_file in file_data.get('metadata', []):
                    new_filename = f"dashboard_{db_num}_metadata_{metadata_file.name}"
                    dashboard_files.append((new_filename, metadata_file))
                
                # Create files list for this dashboard
                files_list = []
                for filename, file_obj in dashboard_files:
                    files_list.append(('files', (filename, file_obj.getvalue(), file_obj.type)))
                
                # Prepare request data as JSON string
                request_data = {
                    'dashboard_id': f"dashboard_{db_num}",
                    'dashboard_name': dashboard_name,
                    'user_provided_name': user_provided_name,
                    'include_analysis_details': True
                }
                
                # Call Phase 1 API for individual dashboard
                profile_response = requests.post(
                    f"{API_BASE_URL}/api/v1/extract-profile",
                    files=files_list,
                    params={'request_data': json.dumps(request_data)},
                    headers={"Authorization": f"Bearer {API_KEY}"},
                    timeout=300
                )
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    extracted_profiles.append(profile_data['profile'])
                    st.success(f"✅ Profile extracted for '{dashboard_name}'")
                else:
                    st.error(f"❌ Failed to extract profile for '{dashboard_name}': {profile_response.text}")
                    continue
            
            # Store extracted profiles for Phase 2
            st.session_state.extracted_profiles = extracted_profiles
            
            progress_bar.progress(0.9)
            status_text.text("Finalizing results...")
            
            if extracted_profiles:
                # Convert profiles to the format expected by the review stage
                processed_dashboards = []
                for profile in extracted_profiles:
                    processed_dashboards.append({
                        'dashboard_id': profile['dashboard_id'],
                        'dashboard_name': profile.get('user_provided_name') or profile['dashboard_name'],
                        'visual_elements_count': len(profile.get('visual_elements', [])),
                        'total_pages': profile.get('total_pages', 1),
                        'metadata_summary': {
                            'total_visual_elements': len(profile.get('visual_elements', [])),
                            'total_kpi_cards': len(profile.get('kpi_cards', [])),
                            'total_filters': len(profile.get('filters', [])),
                            'measure_count': len(profile.get('measures', [])),
                            'table_count': len(profile.get('tables', [])),
                            'visual_types_distribution': profile.get('analysis_details', {}).get('visual_analysis_summary', {}).get('visual_types_distribution', {})
                        },
                        'extraction_confidence': profile.get('extraction_confidence', {}),
                        'analysis_details': profile.get('analysis_details', {})
                    })
                
                st.session_state.processed_dashboards = processed_dashboards
                progress_bar.progress(1.0)
                status_text.text("✅ Phase 1 completed successfully!")
                
                st.success(f"Profile extraction complete! {len(extracted_profiles)} dashboards processed. Click below to review the results.")
                if st.button("Review Extracted Profiles →", type="primary"):
                    st.session_state.stage = 'review'
                    st.rerun()
            else:
                st.error("No dashboard profiles were successfully extracted.")
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
    
    st.write("📋 **Extract & Profile Complete!** Review the extracted profiles and choose your next step:")
    
    # Execution Mode Selection
    st.subheader("🎯 Choose Analysis Mode")
    
    execution_mode = st.radio(
        "Select what you want to execute:",
        options=[
            "Compare & Recommend Only",
            "Full Re-Analysis", 
            "Export Profiles Only"
        ],
        format_func=lambda x: {
            "Compare & Recommend Only": "🔍 **Compare & Recommend** - Find similarities using current profiles",
            "Full Re-Analysis": "🔄 **Full Re-Analysis** - Re-extract profiles + find similarities", 
            "Export Profiles Only": "📁 **Export Profiles** - Save current profiles to files"
        }[x],
        help="Choose your execution mode based on what you want to accomplish"
    )
    
    # Show overall summary
    total_profiles = len(st.session_state.processed_dashboards)
    avg_confidence = 0
    if hasattr(st.session_state, 'extracted_profiles'):
        confidences = [profile.get('extraction_confidence', {}).get('overall', 0) for profile in st.session_state.extracted_profiles]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Profiles Extracted", total_profiles)
    with col2:
        st.metric("🎯 Average Confidence", f"{avg_confidence:.1%}" if avg_confidence else "N/A")
    with col3:
        st.metric("🔄 Ready for Phase 2", "Yes" if total_profiles > 1 else "Need 2+ dashboards")
    
    st.divider()
    
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
                st.metric("Measures Found", metadata_summary.get('measure_count', 0))
                st.metric("Tables Found", metadata_summary.get('table_count', 0))
                st.metric("KPI Cards", metadata_summary.get('total_kpi_cards', 0))
                st.metric("Filters", metadata_summary.get('total_filters', 0))
                
                # Show extraction confidence
                confidence = dashboard.get('extraction_confidence', {})
                if confidence:
                    overall_conf = confidence.get('overall', 0)
                    st.metric("🎯 Extraction Confidence", f"{overall_conf:.1%}")
            
            # Transparency Section - Detailed Analysis Data
            with st.expander("🔍 **Detailed Analysis Data** (Transparency)", expanded=False):
                analysis_details = dashboard.get('analysis_details', {})
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("📊 GPT-4 Vision Analysis")
                    visual_summary = analysis_details.get('visual_analysis_summary', {})
                    if visual_summary:
                        st.json(visual_summary)
                    else:
                        st.write("No detailed visual analysis data available")
                
                with col_b:
                    st.subheader("🧮 DAX Analysis Metrics") 
                    dax_metrics = analysis_details.get('dax_complexity_metrics', {})
                    if dax_metrics:
                        st.json(dax_metrics)
                    else:
                        st.write("No DAX complexity metrics available")
                
                st.subheader("📋 Raw Extraction Data")
                raw_data = analysis_details.get('raw_visual_extraction', [])
                if raw_data:
                    st.write(f"Found {len(raw_data)} raw visual elements:")
                    for i, element in enumerate(raw_data[:3]):  # Show first 3
                        with st.expander(f"Element {i+1}: {element.get('visual_type', 'Unknown')}", expanded=False):
                            st.json(element)
                    if len(raw_data) > 3:
                        st.write(f"... and {len(raw_data) - 3} more elements")
                else:
                    st.write("No raw extraction data available")
                
                # Processing metadata
                processing_meta = analysis_details.get('processing_metadata', {})
                if processing_meta:
                    st.subheader("⚙️ Processing Metadata")
                    st.json(processing_meta)
            
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
        st.success(f"✅ Phase 1 Complete! Ready to run Phase 2 similarity scoring on {total_dashboards} profiles.")
    else:
        st.warning("⚠️ Need at least 2 dashboard profiles for Phase 2 similarity comparison.")
    
    # Pre-execution validation
    st.divider()
    st.subheader("🔍 Pre-Execution Validation")
    
    # Run validation checks
    validation_results = run_pre_execution_checks(execution_mode, st.session_state.processed_dashboards)
    
    # Display validation results
    for check, result in validation_results.items():
        if result["passed"]:
            st.success(f"✅ {check}: {result['message']}")
        else:
            st.error(f"❌ {check}: {result['message']}")
    
    # Check if all validations passed
    all_checks_passed = all(result["passed"] for result in validation_results.values())
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Processing", key="back_to_processing"):
            st.session_state.stage = 'processing'
            st.rerun()
    
    with col2:
        button_disabled = not all_checks_passed
        
        if execution_mode == "Export Profiles Only":
            if st.button("📁 Export Profiles", type="primary", disabled=button_disabled, key="export_profiles"):
                # Create output directory
                output_dir = create_run_directory(execution_mode)
                
                # Export profiles to the directory
                export_profiles_to_directory(output_dir, st.session_state.processed_dashboards)
                
                st.success(f"✅ Profiles exported to: {output_dir}")
                
        elif execution_mode == "Compare & Recommend Only":
            if st.button("🔍 Compare & Recommend →", type="primary", disabled=button_disabled, key="run_comparison"):
                # Create output directory
                st.session_state.output_dir = create_run_directory(execution_mode)
                st.session_state.stage = 'analysis'
                st.rerun()
                
        elif execution_mode == "Full Re-Analysis":
            if st.button("🔄 Re-Analyze Everything →", type="primary", disabled=button_disabled, key="run_full_analysis"):
                # Create output directory
                st.session_state.output_dir = create_run_directory(execution_mode)
                # Reset processing state to force re-analysis
                st.session_state.processed_dashboards = []
                st.session_state.extracted_profiles = []
                st.session_state.analysis_results = {}
                st.session_state.stage = 'processing'
                st.rerun()

# Stage 6: Analysis (Phase 2)
def render_analysis():
    st.header("🔄 Phase 2: Similarity Scoring")
    
    if not st.session_state.analysis_results:
        analysis_method = st.session_state.get('analysis_method', 'Local Batch Analysis')
        
        if analysis_method == "REST API Analysis":
            st.write("Running Phase 2 on your selected reports using automated similarity algorithms...")
            render_api_analysis()
        else:
            st.write("🧮 **Phase 2**: Running mathematical similarity comparison on extracted profiles...")
            render_local_analysis()
    else:
        st.success("✅ Analysis completed!")
        if st.button("View Results →", type="primary"):
            st.session_state.stage = 'results'
            st.rerun()

def render_local_analysis():
    """Handle local file-based similarity analysis using Phase 2 API"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Check if we have extracted profiles from Phase 1
        if not hasattr(st.session_state, 'extracted_profiles') or not st.session_state.extracted_profiles:
            st.error("No extracted profiles found from Phase 1. Please go back and complete the profile extraction stage.")
            if st.button("← Back to Review", key="back_to_review_error"):
                st.session_state.stage = 'review'
                st.rerun()
            return
        
        progress_bar.progress(0.2)
        status_text.text("Phase 2: Initializing similarity scoring...")
        
        # Extract profile IDs from extracted profiles
        profile_ids = [profile['dashboard_id'] for profile in st.session_state.extracted_profiles]
        
        if len(profile_ids) < 2:
            st.error("Need at least 2 profiles for similarity analysis.")
            if st.button("← Back to Review", key="back_insufficient"):
                st.session_state.stage = 'review'
                st.rerun()
            return
        
        progress_bar.progress(0.5)
        status_text.text(f"Phase 2: Running similarity analysis on {len(profile_ids)} profiles...")
        
        # Call the Phase 2 scoring API
        API_KEY = os.getenv("API_KEY", "supersecrettoken123")
        API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/score-profiles",
            json={
                'profile_ids': profile_ids,
                'similarity_config': {
                    'similarity_threshold': 0.7,
                    'weights': {
                        'measures': 0.4,
                        'visuals': 0.3,
                        'data_model': 0.2,
                        'layout': 0.1
                    }
                },
                'include_detailed_breakdown': True
            },
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=300
        )
        
        progress_bar.progress(0.9)
        status_text.text("Processing similarity results...")
        
        if response.status_code == 200:
            phase2_results = response.json()
            # Store both Phase 2 results and original results format for compatibility
            st.session_state.analysis_results = {
                'phase2_results': phase2_results,
                'consolidated_groups': phase2_results.get('consolidation_groups', []),
                'similarity_scores': phase2_results.get('detailed_scores', []),
                'similarity_matrix': phase2_results.get('similarity_matrix', [])
            }
            progress_bar.progress(1.0)
            status_text.text("✅ Phase 2 similarity analysis completed successfully!")
            
            # Show quick summary
            num_groups = len(phase2_results.get('consolidation_groups', []))
            processing_time = phase2_results.get('processing_time', 0)
            
            st.success(f"Phase 2 Complete! Found {num_groups} consolidation groups in {processing_time:.1f}s. Click below to view detailed results.")
            if st.button("View Consolidation Results →", type="primary"):
                st.session_state.stage = 'results'
                st.rerun()
        else:
            st.error(f"Phase 2 similarity analysis failed: {response.text}")
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
# ─── ENHANCED ANALYSIS FUNCTIONS ────────────────────────────────────────────

def get_confidence_badge(score):
    """Generate confidence score badge HTML"""
    if score >= 0.8:
        return '<span class="confidence-score confidence-high">High Confidence</span>'
    elif score >= 0.6:
        return '<span class="confidence-score confidence-medium">Medium Confidence</span>'
    else:
        return '<span class="confidence-score confidence-low">Low Confidence</span>'

def render_detailed_dashboard_analysis(dashboard_id: str):
    """Render detailed analysis for a specific dashboard"""
    try:
        API_KEY = os.getenv("API_KEY", "supersecrettoken123")
        API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # Get detailed profile information
        response = requests.get(
            f"{API_BASE_URL}/api/v1/profiles/{dashboard_id}/details",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        
        if response.status_code == 200:
            details = response.json()
            profile = details['profile']
            
            st.markdown(f"""
            <div class="detailed-analysis-box">
                <h4>🔍 Detailed Analysis: {profile.get('user_provided_name', profile.get('dashboard_name', 'Unknown Dashboard'))}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Analysis confidence scores
            confidence_scores = details.get('confidence_scores', {})
            if confidence_scores:
                st.subheader("📊 Analysis Confidence")
                cols = st.columns(len(confidence_scores))
                for i, (phase, score) in enumerate(confidence_scores.items()):
                    with cols[i]:
                        st.metric(
                            phase.replace('_', ' ').title(),
                            f"{score*100:.1f}%",
                            help=f"Confidence in the {phase.replace('_', ' ')} extraction"
                        )
            
            # Visual Elements Breakdown
            visual_breakdown = details.get('visual_breakdown', {})
            if visual_breakdown.get('raw_elements'):
                st.subheader("🎨 Visual Elements Detected by GPT-4 Vision")
                
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Elements", visual_breakdown['total_elements'])
                with col2:
                    st.metric("Element Types", len(visual_breakdown['elements_by_type']))
                with col3:
                    complexity = min(visual_breakdown['total_elements'] / 10, 1.0)
                    st.metric("Visual Complexity", f"{complexity:.2f}")
                
                # Element type distribution
                if visual_breakdown['elements_by_type']:
                    st.write("**Visual Element Distribution:**")
                    element_types = visual_breakdown['elements_by_type']
                    
                    # Create bar chart
                    if element_types:
                        fig = px.bar(
                            x=list(element_types.keys()),
                            y=list(element_types.values()),
                            title="Visual Elements by Type",
                            labels={'x': 'Element Type', 'y': 'Count'},
                            color_discrete_sequence=['#0C62FB']
                        )
                        fig.update_layout(height=300)
                        st.plotly_chart(fig, use_container_width=True)
                
                # Detailed element list (expandable)
                with st.expander("🔍 Raw Visual Elements (GPT-4 Vision Analysis)", expanded=False):
                    for i, element in enumerate(visual_breakdown['raw_elements']):
                        st.markdown(f"""
                        <div class="visual-element-card">
                            <strong>Element {i+1}: {element.get('visual_type', 'Unknown').title()}</strong><br>
                            <em>Title:</em> {element.get('title', 'No title detected')}<br>
                            <em>Page:</em> {element.get('page_name', 'Unknown page')}<br>
                            <em>Data Fields:</em> {', '.join(element.get('data_fields', [])) or 'None detected'}<br>
                            <em>Position:</em> {element.get('position', 'Not specified')}
                        </div>
                        """, unsafe_allow_html=True)
            
            # Data Model Breakdown
            data_model = details.get('data_model_breakdown', {})
            if data_model:
                st.subheader("🏗️ Data Model Analysis")
                
                # Measures analysis
                measures = data_model.get('measures', [])
                if measures:
                    st.write(f"**📈 DAX Measures ({len(measures)} found):**")
                    with st.expander("View All Measures", expanded=False):
                        for measure in measures[:10]:  # Show first 10
                            st.markdown(f"""
                            **{measure.get('measure_name', 'Unknown')}**
                            - Table: {measure.get('table_name', 'Unknown')}
                            - Formula: `{measure.get('dax_formula', 'No formula')[:100]}...`
                            """)
                        if len(measures) > 10:
                            st.write(f"... and {len(measures) - 10} more measures")
                
                # Tables analysis
                tables = data_model.get('tables', [])
                if tables:
                    st.write(f"**📋 Data Tables ({len(tables)} found):**")
                    table_data = []
                    for table in tables:
                        table_data.append({
                            'Table Name': table.get('table_name', 'Unknown'),
                            'Columns': table.get('column_count', 0),
                            'Rows': table.get('row_count', 'Unknown'),
                            'Type': table.get('table_type', 'Unknown')
                        })
                    
                    if table_data:
                        df_tables = pd.DataFrame(table_data)
                        st.dataframe(df_tables, use_container_width=True)
                
                # Relationships analysis
                relationships = data_model.get('relationships', [])
                if relationships:
                    st.write(f"**🔗 Relationships ({len(relationships)} found):**")
                    with st.expander("View Relationships", expanded=False):
                        for rel in relationships:
                            st.write(f"• {rel.get('from_table', 'Unknown')}.{rel.get('from_column', 'Unknown')} → {rel.get('to_table', 'Unknown')}.{rel.get('to_column', 'Unknown')} ({rel.get('relationship_type', 'Unknown')})")
            
            # Processing metadata
            analysis_details = details.get('analysis_details', {})
            if analysis_details:
                with st.expander("⚙️ Processing Information", expanded=False):
                    processing_meta = analysis_details.get('processing_metadata', {})
                    if processing_meta:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Processing Time:** {processing_meta.get('total_processing_time', 0):.2f}s")
                            st.write(f"**Analysis Version:** {processing_meta.get('analysis_model_version', 'Unknown')}")
                        with col2:
                            st.write(f"**Timestamp:** {processing_meta.get('extraction_timestamp', 'Unknown')}")
                            
                    # Complexity metrics
                    dax_metrics = analysis_details.get('dax_complexity_metrics', {})
                    if dax_metrics:
                        st.write("**DAX Complexity Metrics:**")
                        complexity_indicators = dax_metrics.get('complexity_indicators', {})
                        for metric, value in complexity_indicators.items():
                            st.write(f"• {metric.replace('_', ' ').title()}: {value}")
        
        else:
            st.error(f"Could not load detailed analysis: {response.status_code}")
            
    except Exception as e:
        st.error(f"Error loading detailed analysis: {str(e)}")

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
        st.metric("Dashboards Analyzed", results.get('data', {}).get('dashboards_processed', 0))
    with col2:
        st.metric("Total Views", results.get('data', {}).get('total_views', 0))
    with col3:
        st.metric("Similarity Pairs", results.get('data', {}).get('similarity_pairs', 0))
    with col4:
        st.metric("Consolidation Groups", results.get('data', {}).get('consolidation_groups', 0))
    
    st.divider()
    
    # Enhanced Dashboard Profiles Section with Detailed Analysis
    st.subheader("🔍 Dashboard Analysis Details")
    st.write("Click on any dashboard below to view the detailed AI analysis including extracted visual elements, measures, and confidence scores.")
    
    # Get dashboard profiles from API
    try:
        API_KEY = os.getenv("API_KEY", "supersecrettoken123")
        API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # Get all dashboard profiles
        profiles_response = requests.get(
            f"{API_BASE_URL}/api/v1/dashboard-profiles",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        
        if profiles_response.status_code == 200:
            profiles_data = profiles_response.json()
            dashboard_profiles = profiles_data.get('profiles', [])
            
            if dashboard_profiles:
                # Create expandable sections for each dashboard
                cols = st.columns(min(len(dashboard_profiles), 3))
                for i, profile in enumerate(dashboard_profiles):
                    with cols[i % 3]:
                        display_name = profile.get('user_provided_name', profile.get('dashboard_name', 'Unknown Dashboard'))
                        
                        # Create a button-like expander for each dashboard
                        if st.button(f"📊 {display_name}", key=f"dashboard_detail_{i}", use_container_width=True):
                            st.session_state[f'show_details_{profile["dashboard_id"]}'] = not st.session_state.get(f'show_details_{profile["dashboard_id"]}', False)
                        
                        # Show basic info
                        st.caption(f"ID: {profile['dashboard_id']}")
                        if profile.get('complexity_score'):
                            st.caption(f"Complexity: {profile['complexity_score']:.1f}/10")
                
                # Display detailed analysis if any dashboard is selected
                for profile in dashboard_profiles:
                    if st.session_state.get(f'show_details_{profile["dashboard_id"]}', False):
                        st.divider()
                        render_detailed_dashboard_analysis(profile['dashboard_id'])
                        st.divider()
            
            else:
                st.info("No dashboard profiles found. Run analysis first.")
        
        else:
            st.warning("Could not load dashboard profiles.")
    
    except Exception as e:
        st.error(f"Error loading dashboard profiles: {str(e)}")
    
    st.divider()
    
    # Get detailed results from API
    try:
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