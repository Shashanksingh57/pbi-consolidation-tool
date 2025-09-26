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
            # Use the user-provided name, not the generic db_id
            dashboard_name = config.get('name', db_id)
            st.sidebar.write(f"• {dashboard_name}: {config['views']} views")
    
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
        # Combined Local Analysis section
        st.subheader("📁 Local Analysis")

        st.write("""
        **Analyze dashboards from local files.** Choose between manual upload or automated extraction.

        **Use this when:**
        - Working with local .pbix files
        - No cloud API access required
        - Need full control over the process
        """)

        # Add spacing to match right column height
        st.write("")  # Extra line for alignment

    with col2:
        # Power BI Service section
        st.subheader("☁️ Power BI Service")

        st.write("""
        **Enterprise-scale automated analysis.** Connect to Power BI Service for real-time workspace analysis.

        **Use this when:**
        - You have a Power BI Pro or Premium license
        - You need to analyze many dashboards across one or more workspaces
        - You want to automate the data extraction process
        """)

    # Buttons in separate row to ensure alignment
    col1_btn, col2_btn = st.columns(2)

    with col1_btn:
        if st.button("🖥️ Start Local Analysis", type="primary", key="local_analysis", use_container_width=True):
            st.session_state.analysis_method = "Local Analysis"
            st.session_state.stage = 'local_mode_selection'
            st.rerun()

    with col2_btn:
        if st.button("☁️ Start Power BI Service", type="primary", key="rest_api", use_container_width=True):
            st.session_state.analysis_method = "REST API Analysis"
            st.session_state.stage = 'api_credentials'
            st.rerun()

# Stage 1.5: Local Mode Selection
def render_local_mode_selection():
    st.header("📁 Local Analysis - Choose Method")

    st.write("Select how you want to analyze your local Power BI files:")

    # Create two cards for the sub-modes
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📤 Manual Upload")

        # Platform availability
        st.success("✅ Available on: Windows, Mac, Linux")

        # Prerequisites with expandable details
        with st.expander("📋 Prerequisites & Requirements"):
            st.write("""
            **Required Files:**
            - Dashboard screenshots (PNG/JPG)
            - DAX Studio exports (CSV):
              - Measures export
              - Tables export
              - Relationships export

            **Tools Needed:**
            - DAX Studio (free)
            - Screenshot tool

            **Best for:**
            - Small number of dashboards (1-10)
            - Quick one-time analysis
            - When .pbix files are not available
            """)

        st.write("""
        Upload screenshots and metadata exports manually.
        Full control over what gets analyzed.
        """)

    with col2:
        st.markdown("### 🔧 pbi-tools Extraction")

        # Platform availability with warning
        st.warning("⚠️ Windows Only - Requires pbi-tools")

        # Prerequisites with expandable details
        with st.expander("📋 Prerequisites & Requirements"):
            st.write("""
            **System Requirements:**
            - Windows 10/11
            - .NET Framework 4.7.2+
            - pbi-tools CLI installed

            **Required Files:**
            - .pbix or .pbit files
            - Dashboard screenshots (for visual analysis)

            **Installation:**
            1. Download: [pbi-tools releases](https://github.com/pbi-tools/pbi-tools/releases)
            2. Extract ZIP to folder
            3. Add to system PATH
            4. Verify: `pbi-tools version`

            **Best for:**
            - Large number of dashboards (10+)
            - Automated batch processing
            - Complete metadata extraction
            """)

        st.write("""
        Automatically extract metadata from .pbix files.
        Bulk process entire folders of reports.
        """)

        import platform
        is_windows = platform.system() == "Windows"

        if not is_windows:
            st.info("🔄 Demo mode will be used (not on Windows)")

    # Buttons in separate row to ensure alignment
    col1_btn, col2_btn = st.columns(2)

    with col1_btn:
        if st.button("📤 Use Manual Upload", type="primary", key="manual_mode", use_container_width=True):
            st.session_state.analysis_sub_method = "Manual Upload"
            st.session_state.stage = 'dashboard_config'
            st.rerun()

    with col2_btn:
        if st.button(
            "🔧 Use pbi-tools" if is_windows else "🔧 Use pbi-tools (Demo)",
            type="primary" if is_windows else "secondary",
            key="pbi_tools_mode",
            use_container_width=True
        ):
            st.session_state.analysis_sub_method = "pbi-tools"
            st.session_state.stage = 'folder_selection'
            st.rerun()

    # Back button
    st.markdown("---")
    if st.button("← Back to Analysis Methods"):
        st.session_state.stage = 'method_choice'
        st.rerun()

# Stage 2A: Folder Selection for Local Batch Mode
def render_folder_selection():
    st.header("📁 Local Batch Mode - Folder Selection")

    # Import the pbi-tools wrapper
    import platform
    from pbi_tools_wrapper import PBIToolsWrapper, MockPBIToolsWrapper

    # Check if running on Windows
    is_windows = platform.system() == "Windows"

    if not is_windows:
        st.warning("⚠️ **Note:** pbi-tools only runs on Windows. Using mock mode for demonstration.")
        pbi_wrapper = MockPBIToolsWrapper()
    else:
        pbi_wrapper = PBIToolsWrapper()

        # Check if pbi-tools is installed
        if not pbi_wrapper.check_installation():
            st.error("❌ pbi-tools is not installed or not in PATH")
            st.info("""
            **To install pbi-tools:**
            1. Download from: https://github.com/pbi-tools/pbi-tools/releases
            2. Extract the ZIP file
            3. Add the folder to your system PATH
            4. Restart this application
            """)
            if st.button("← Back to Method Selection"):
                st.session_state.stage = 'method_choice'
                st.rerun()
            return

    st.write("""
    Select a folder containing your Power BI files (.pbix/.pbit).
    The tool will automatically discover all files and extract their metadata.
    """)

    # Folder path selection
    st.write("**Select folder containing your .pbix/.pbit files:**")

    col1, col2 = st.columns([3, 1])

    with col1:
        folder_path = st.text_input(
            "Folder path:",
            value=st.session_state.get('selected_folder_path',
                   "C:\\Users\\YourName\\Documents\\PowerBI Files" if is_windows else "/Users/YourName/Documents/PowerBI Files"),
            help="Full path to the folder containing your .pbix/.pbit files"
        )

    with col2:
        st.write("")  # Spacing
        if st.button("📁 Browse", help="Open folder browser dialog"):
            try:
                if is_windows:
                    import tkinter as tk
                    from tkinter import filedialog

                    # Create a root window and hide it
                    root = tk.Tk()
                    root.withdraw()
                    root.wm_attributes('-topmost', 1)

                    # Open folder dialog
                    selected_folder = filedialog.askdirectory(
                        title="Select folder containing Power BI files",
                        initialdir=folder_path if os.path.exists(folder_path) else "C:\\"
                    )

                    if selected_folder:
                        st.session_state.selected_folder_path = selected_folder
                        st.rerun()

                    root.destroy()
                else:
                    st.info("💡 Folder browser is only available on Windows. Please enter the path manually on Mac/Linux.")

            except Exception as e:
                st.error(f"Could not open folder browser: {str(e)}")
                st.info("💡 Please enter the folder path manually in the text field above.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Method Selection"):
            st.session_state.stage = 'method_choice'
            st.rerun()

    with col2:
        if st.button("Scan Folder", type="primary"):
            # Use the session state folder path if available
            current_folder = st.session_state.get('selected_folder_path', folder_path)
            if current_folder and os.path.exists(current_folder):
                with st.spinner("Scanning folder for Power BI files..."):
                    # Discover files
                    pbi_files = pbi_wrapper.discover_pbi_files(current_folder)

                    if pbi_files:
                        st.session_state.discovered_files = pbi_files
                        st.session_state.folder_path = current_folder
                        st.session_state.pbi_wrapper = pbi_wrapper
                        st.session_state.stage = 'pbi_extraction'
                        st.rerun()
                    else:
                        st.error("No .pbix or .pbit files found in the selected folder")
            else:
                st.error("Please enter a valid folder path")

    # Show example folder structure
    with st.expander("📋 Example Folder Structure"):
        st.code("""
        PowerBI Files/
        ├── Sales Dashboard.pbix
        ├── Finance Report.pbix
        ├── Templates/
        │   └── Monthly Report.pbit
        └── Archives/
            ├── Q1 2024 Dashboard.pbix
            └── Q2 2024 Dashboard.pbix
        """)

# Stage 2B: PBI File Extraction
def render_pbi_extraction():
    st.header("🔄 Extracting Dashboard Metadata")

    if 'discovered_files' not in st.session_state:
        st.error("No files discovered. Please go back to folder selection.")
        if st.button("← Back to Folder Selection"):
            st.session_state.stage = 'folder_selection'
            st.rerun()
        return

    pbi_files = st.session_state.discovered_files
    pbi_wrapper = st.session_state.pbi_wrapper

    st.write(f"**Found {len(pbi_files)} Power BI file(s)** in the selected folder:")

    # Display discovered files
    file_df = pd.DataFrame(pbi_files)
    file_df['size_mb'] = file_df['size_mb'].round(2)
    st.dataframe(file_df[['name', 'type', 'size_mb', 'relative_path']], use_container_width=True)

    if st.button("Extract Metadata from All Files", type="primary"):
        extraction_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, file_info in enumerate(pbi_files):
            progress = (idx + 1) / len(pbi_files)
            progress_bar.progress(progress)
            status_text.text(f"Extracting from: {file_info['name']}")

            metadata, error = pbi_wrapper.extract_metadata(file_info['path'])
            extraction_results.append({
                "file_info": file_info,
                "metadata": metadata,
                "error": error
            })

        # Store results and move to screenshot upload
        st.session_state.extraction_results = extraction_results
        st.session_state.stage = 'screenshot_mapping'
        st.rerun()

    if st.button("← Back to Folder Selection"):
        st.session_state.stage = 'folder_selection'
        st.rerun()

# Stage 2C: Screenshot Mapping
def render_screenshot_mapping():
    st.header("📸 Upload Dashboard Screenshots")

    if 'extraction_results' not in st.session_state:
        st.error("No extraction results found.")
        if st.button("← Back"):
            st.session_state.stage = 'folder_selection'
            st.rerun()
        return

    extraction_results = st.session_state.extraction_results
    st.write(f"""
    **Metadata extracted successfully!** Now upload screenshots for each dashboard to enable visual analysis.
    Screenshots help identify visual elements that cannot be extracted from the .pbix files.
    """)

    # Create tabs for each dashboard
    dashboard_names = [result['file_info']['name'] for result in extraction_results]
    tabs = st.tabs(dashboard_names)

    screenshot_uploads = {}

    for tab, result in zip(tabs, extraction_results):
        with tab:
            file_info = result['file_info']
            metadata = result['metadata']

            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(f"📊 {file_info['name']}")

                # Show extraction status
                if result['error']:
                    st.error(f"⚠️ Extraction had issues: {result['error']}")
                else:
                    st.success("✅ Metadata extracted successfully")

                # Show metadata summary
                if metadata.get('measures'):
                    st.metric("Measures", len(metadata['measures']))
                if metadata.get('tables'):
                    st.metric("Tables", len(metadata['tables']))
                if metadata.get('pages'):
                    st.metric("Pages", len(metadata['pages']))

            with col2:
                st.write("**Upload Screenshot:**")
                uploaded_file = st.file_uploader(
                    f"Screenshot for {file_info['name']}",
                    type=['png', 'jpg', 'jpeg'],
                    key=f"screenshot_{file_info['name']}"
                )

                if uploaded_file:
                    screenshot_uploads[file_info['name']] = uploaded_file
                    st.image(uploaded_file, width=200)

    # Show progress
    uploaded_count = len(screenshot_uploads)
    total_count = len(extraction_results)
    st.progress(uploaded_count / total_count)
    st.write(f"Screenshots uploaded: {uploaded_count}/{total_count}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back to Extraction"):
            st.session_state.stage = 'pbi_extraction'
            st.rerun()

    with col2:
        if st.button("Continue to Analysis →", type="primary"):
            # Combine extraction results with screenshots
            combined_profiles = []
            pbi_wrapper = st.session_state.pbi_wrapper

            for result in extraction_results:
                file_name = result['file_info']['name']
                screenshot = screenshot_uploads.get(file_name)

                # Convert to dashboard profile
                profile = pbi_wrapper.convert_to_dashboard_profile(
                    result['metadata'],
                    screenshot_path=screenshot if screenshot else None
                )
                combined_profiles.append(profile)

            # Store profiles and proceed
            st.session_state.extracted_profiles = combined_profiles
            st.session_state.stage = 'processing'
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
                
                # Update progress with more granular status
                progress = 0.3 + (idx / total_dashboards) * 0.5
                progress_bar.progress(progress)
                status_text.text(f"Phase 1: Processing '{dashboard_name}' ({idx+1}/{total_dashboards})...")
                
                # Show sub-status
                sub_status = st.empty()
                sub_status.info(f"📸 Processing visuals for '{dashboard_name}'...")
                
                # Prepare files for this specific dashboard
                dashboard_files = []
                file_data = st.session_state.uploaded_files.get(db_id, {})
                
                # Add view screenshots and prepare view summaries
                view_summaries = []
                for i, view_file in enumerate(file_data.get('views', [])):
                    view_name = file_data.get('view_names', [f"View {i+1}"])[i]
                    new_filename = f"dashboard_{db_num}_view_{i+1}_{view_name}.{view_file.name.split('.')[-1]}"
                    dashboard_files.append((new_filename, view_file))
                    
                    # Store base64 encoded image for preview
                    import base64
                    view_file.seek(0)
                    view_data = base64.b64encode(view_file.read()).decode('utf-8')
                    view_summaries.append({
                        'name': view_name,
                        'data': view_data
                    })
                    view_file.seek(0)  # Reset for later use
                
                # Add metadata files
                if file_data.get('metadata'):
                    sub_status.info(f"📊 Processing metadata for '{dashboard_name}'...")
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
                    profile = profile_data['profile']
                    # Add view summaries to profile
                    profile['view_summaries'] = view_summaries
                    extracted_profiles.append(profile)
                    sub_status.success(f"✅ Successfully extracted profile for '{dashboard_name}'")
                else:
                    sub_status.error(f"❌ Failed to extract profile for '{dashboard_name}': {profile_response.text}")
                    continue
            
            # Store extracted profiles for Phase 2
            st.session_state.extracted_profiles = extracted_profiles
            
            progress_bar.progress(0.9)
            status_text.text("Finalizing results...")
            
            if extracted_profiles:
                # Convert profiles to the format expected by the review stage
                processed_dashboards = []
                # Ensure consistent naming throughout the workflow
                for profile in extracted_profiles:
                    display_name = profile.get('user_provided_name') or profile['dashboard_name']
                    processed_dashboards.append({
                        'dashboard_id': profile['dashboard_id'],
                        'dashboard_name': display_name,  # Use consistent display name
                        'user_provided_name': profile.get('user_provided_name'),  # Keep original for reference
                        'visual_elements_count': len(profile.get('visual_elements', [])),
                        'total_pages': profile.get('total_pages', 1),
                        'view_summaries': profile.get('view_summaries', []),
                        'metadata_summary': {
                            'total_visual_elements': len(profile.get('visual_elements', [])),
                            'total_kpi_cards': len(profile.get('kpi_cards', [])),
                            'total_filters': len(profile.get('filters', [])),
                            'measure_count': len(profile.get('measures', [])),
                            'table_count': len(profile.get('tables', [])),
                            'visual_types_distribution': profile.get('analysis_details', {}).get('visual_analysis_summary', {}).get('visual_types_distribution', {})
                        },
                        'extraction_confidence': profile.get('extraction_confidence', {}),
                        'analysis_details': profile.get('analysis_details', {}),
                        'visual_elements': profile.get('visual_elements', []),
                        'kpi_cards': profile.get('kpi_cards', []),
                        'filters': profile.get('filters', []),
                        'measures': profile.get('measures', []),
                        'tables': profile.get('tables', []),
                        'relationships': profile.get('relationships', [])
                    })
                
                # Store full dashboard profiles for detailed comparison
                # CRITICAL: Store complete data for detailed analysis
                st.session_state.processed_dashboards = processed_dashboards
                st.session_state.full_dashboard_profiles = extracted_profiles  # Store complete profiles
                st.session_state.dashboard_profiles_by_name = {}
                st.session_state.dashboard_profiles_by_id = {}
                
                # Create comprehensive lookup dictionaries for easy access
                # Map both processed dashboards AND full profiles
                for i, dashboard in enumerate(processed_dashboards):
                    name = dashboard['dashboard_name']
                    id = dashboard['dashboard_id']
                    # Store both processed and full profile data
                    dashboard_with_full_data = {
                        **dashboard,
                        'full_profile': extracted_profiles[i] if i < len(extracted_profiles) else None
                    }
                    st.session_state.dashboard_profiles_by_name[name] = dashboard_with_full_data
                    st.session_state.dashboard_profiles_by_id[id] = dashboard_with_full_data
                
                # Also create a mapping from original profile data
                for profile in extracted_profiles:
                    profile_name = profile.get('user_provided_name') or profile.get('dashboard_name')
                    profile_id = profile.get('dashboard_id')
                    if profile_name and profile_name not in st.session_state.dashboard_profiles_by_name:
                        st.session_state.dashboard_profiles_by_name[profile_name] = profile
                    if profile_id and profile_id not in st.session_state.dashboard_profiles_by_id:
                        st.session_state.dashboard_profiles_by_id[profile_id] = profile
                progress_bar.progress(1.0)
                status_text.text("✅ Phase 1 completed successfully!")
                
                st.success(f"Profile extraction complete! {len(extracted_profiles)} dashboards processed.")
                time.sleep(1)  # Brief pause to show success
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
        time.sleep(1)  # Brief pause to show success
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
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📊 Profiles Extracted", total_profiles)
    with col2:
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
                
                # Removed filters display as backend doesn't support it
            
            with col2:
                st.subheader("🗂️ Metadata Summary")
                st.metric("Measures Found", metadata_summary.get('measure_count', 0))
                st.metric("Tables Found", metadata_summary.get('table_count', 0))
                
                # Show screenshot preview if available (moved here to avoid duplication)
                if 'view_summaries' in dashboard:
                    view_summaries = dashboard.get('view_summaries', [])
                    if view_summaries and len(view_summaries) > 0:
                        first_view = view_summaries[0]
                        if 'data' in first_view:
                            import base64
                            try:
                                img_data = base64.b64decode(first_view['data'])
                                st.image(img_data, caption=f"Preview - {first_view.get('name', 'View 1')}", use_container_width=True)
                            except Exception as e:
                                st.info("Screenshot preview not available")
            
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
        time.sleep(1)  # Brief pause to show success
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
            
            # Ensure dashboard IDs are included in similarity scores
            for score in st.session_state.analysis_results['similarity_scores']:
                # Extract dashboard IDs from names if not present
                if 'dashboard1_id' not in score and hasattr(st.session_state, 'extracted_profiles'):
                    for profile in st.session_state.extracted_profiles:
                        profile_name = profile.get('user_provided_name') or profile.get('dashboard_name')
                        if profile_name == score['dashboard1_name']:
                            score['dashboard1_id'] = profile['dashboard_id']
                        if profile_name == score['dashboard2_name']:
                            score['dashboard2_id'] = profile['dashboard_id']
            progress_bar.progress(1.0)
            status_text.text("✅ Phase 2 similarity analysis completed successfully!")
            
            # Show quick summary
            num_groups = len(phase2_results.get('consolidation_groups', []))
            processing_time = phase2_results.get('processing_time', 0)
            
            st.success(f"Phase 2 Complete! Found {num_groups} consolidation groups in {processing_time:.1f}s.")
            time.sleep(1)  # Brief pause to show success
            st.session_state.stage = 'results'
            st.rerun()
        else:
            st.error(f"Phase 2 similarity analysis failed: {response.text}")
            st.warning("Generating mock similarity data for testing...")
            
            # Create mock similarity data for testing
            extracted_profiles = st.session_state.get('extracted_profiles', [])
            if len(extracted_profiles) >= 2:
                mock_scores = []
                for i in range(len(extracted_profiles)):
                    for j in range(i + 1, len(extracted_profiles)):
                        profile1 = extracted_profiles[i]
                        profile2 = extracted_profiles[j]
                        
                        name1 = profile1.get('user_provided_name') or profile1.get('dashboard_name', f'Dashboard {i+1}')
                        name2 = profile2.get('user_provided_name') or profile2.get('dashboard_name', f'Dashboard {j+1}')
                        
                        mock_scores.append({
                            'dashboard1_name': name1,
                            'dashboard2_name': name2,
                            'dashboard1_id': profile1.get('dashboard_id'),
                            'dashboard2_id': profile2.get('dashboard_id'),
                            'total_score': 0.75 + (i * 0.05),  # Mock similarity score
                            'breakdown': {
                                'measures_score': 0.8,
                                'visuals_score': 0.7,
                                'data_model_score': 0.75,
                                'layout_score': 0.6
                            }
                        })
                
                # Store mock results
                st.session_state.analysis_results = {
                    'phase2_results': {
                        'detailed_scores': mock_scores,
                        'consolidation_groups': [],
                        'processing_time': 1.0
                    },
                    'similarity_scores': mock_scores,
                    'consolidated_groups': [],
                    'similarity_matrix': []
                }
                
                progress_bar.progress(1.0)
                status_text.text("✅ Mock similarity analysis completed!")
                st.success("Mock data generated for testing. Click below to view results.")
                time.sleep(1)
                st.session_state.stage = 'results'
                st.rerun()
            else:
                if st.button("← Back to Review", key="back_to_review_error"):
                    st.session_state.stage = 'review'
                    st.rerun()
    
    except Exception as e:
        st.error(f"Error during similarity analysis: {str(e)}")
        st.warning("Generating mock similarity data due to error...")
        
        # Create mock similarity data for testing in case of error
        extracted_profiles = st.session_state.get('extracted_profiles', [])
        if len(extracted_profiles) >= 2:
            mock_scores = []
            for i in range(len(extracted_profiles)):
                for j in range(i + 1, len(extracted_profiles)):
                    profile1 = extracted_profiles[i]
                    profile2 = extracted_profiles[j]
                    
                    name1 = profile1.get('user_provided_name') or profile1.get('dashboard_name', f'Dashboard {i+1}')
                    name2 = profile2.get('user_provided_name') or profile2.get('dashboard_name', f'Dashboard {j+1}')
                    
                    mock_scores.append({
                        'dashboard1_name': name1,
                        'dashboard2_name': name2,
                        'dashboard1_id': profile1.get('dashboard_id'),
                        'dashboard2_id': profile2.get('dashboard_id'),
                        'total_score': 0.75 + (i * 0.05),  # Mock similarity score
                        'breakdown': {
                            'measures_score': 0.8,
                            'visuals_score': 0.7,
                            'data_model_score': 0.75,
                            'layout_score': 0.6
                        }
                    })
            
            # Store mock results
            st.session_state.analysis_results = {
                'phase2_results': {
                    'detailed_scores': mock_scores,
                    'consolidation_groups': [],
                    'processing_time': 1.0
                },
                'similarity_scores': mock_scores,
                'consolidated_groups': [],
                'similarity_matrix': []
            }
            
            st.success("Mock data generated for testing purposes.")
            time.sleep(1)
            st.session_state.stage = 'results'
            st.rerun()
        else:
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
            time.sleep(2)  # Brief pause to show demo message
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
    dashboard1_id = similarity_score.get('dashboard1_id')
    dashboard2_id = similarity_score.get('dashboard2_id')
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
    
    # ENHANCED: Find dashboard data with comprehensive lookup
    dashboard1_data = None
    dashboard2_data = None
    
    # Debug information
    st.write(f"🔍 Looking for: '{dashboard1_name}' and '{dashboard2_name}'")
    if hasattr(st.session_state, 'dashboard_profiles_by_name'):
        st.write(f"Available profiles by name: {list(st.session_state.dashboard_profiles_by_name.keys())}")
    
    # Method 1: Use lookup dictionaries (primary method)
    if hasattr(st.session_state, 'dashboard_profiles_by_name') and st.session_state.dashboard_profiles_by_name:
        dashboard1_data = st.session_state.dashboard_profiles_by_name.get(dashboard1_name)
        dashboard2_data = st.session_state.dashboard_profiles_by_name.get(dashboard2_name)
        if dashboard1_data:
            st.write(f"✅ Found {dashboard1_name} in profiles_by_name")
        if dashboard2_data:
            st.write(f"✅ Found {dashboard2_name} in profiles_by_name")
    
    # Method 2: Try by ID lookup
    if (not dashboard1_data or not dashboard2_data) and hasattr(st.session_state, 'dashboard_profiles_by_id'):
        if dashboard1_id and not dashboard1_data:
            dashboard1_data = st.session_state.dashboard_profiles_by_id.get(dashboard1_id)
            if dashboard1_data:
                st.write(f"✅ Found {dashboard1_name} by ID: {dashboard1_id}")
        if dashboard2_id and not dashboard2_data:
            dashboard2_data = st.session_state.dashboard_profiles_by_id.get(dashboard2_id)
            if dashboard2_data:
                st.write(f"✅ Found {dashboard2_name} by ID: {dashboard2_id}")
    
    # Method 3: Search in processed_dashboards (direct access)
    if (not dashboard1_data or not dashboard2_data) and processed_dashboards:
        st.write(f"Searching in processed_dashboards: {len(processed_dashboards)} items")
        for dashboard in processed_dashboards:
            dash_name = dashboard.get('dashboard_name')
            dash_id = dashboard.get('dashboard_id')
            if not dashboard1_data and (dash_id == dashboard1_id or dash_name == dashboard1_name):
                dashboard1_data = dashboard
                st.write(f"✅ Found {dashboard1_name} in processed_dashboards")
            elif not dashboard2_data and (dash_id == dashboard2_id or dash_name == dashboard2_name):
                dashboard2_data = dashboard
                st.write(f"✅ Found {dashboard2_name} in processed_dashboards")
    
    # Method 4: Final fallback - search full profiles
    if (not dashboard1_data or not dashboard2_data) and hasattr(st.session_state, 'full_dashboard_profiles'):
        st.write(f"Searching in full_dashboard_profiles: {len(st.session_state.full_dashboard_profiles)} items")
        for profile in st.session_state.full_dashboard_profiles:
            profile_name = profile.get('user_provided_name') or profile.get('dashboard_name')
            profile_id = profile.get('dashboard_id')
            if not dashboard1_data and (profile_id == dashboard1_id or profile_name == dashboard1_name):
                dashboard1_data = profile
                st.write(f"✅ Found {dashboard1_name} in full_dashboard_profiles")
            elif not dashboard2_data and (profile_id == dashboard2_id or profile_name == dashboard2_name):
                dashboard2_data = profile
                st.write(f"✅ Found {dashboard2_name} in full_dashboard_profiles")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"##### 📋 **{dashboard1_name}**")
        if dashboard1_data:
            render_dashboard_summary(dashboard1_data, side="left")
        else:
            st.warning(f"⚠️ Dashboard details not available for '{dashboard1_name}'")
    
    with col2:
        st.markdown(f"##### 📋 **{dashboard2_name}**")
        if dashboard2_data:
            render_dashboard_summary(dashboard2_data, side="right")
        else:
            st.warning(f"⚠️ Dashboard details not available for '{dashboard2_name}'")
    
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
    
    # Basic information - show the name that the user will recognize
    display_name = dashboard_data.get('user_provided_name') or dashboard_data.get('dashboard_name', 'N/A')
    st.write(f"**Name:** {display_name}")
    st.write(f"**ID:** `{dashboard_data.get('dashboard_id', 'N/A')}`")
    
    # Check different possible data structures
    # Try to get visual elements count
    visual_count = 0
    if 'visual_elements' in dashboard_data:
        visual_count = len(dashboard_data['visual_elements'])
    elif 'visual_elements_count' in dashboard_data:
        visual_count = dashboard_data['visual_elements_count']
    elif 'visual_analysis' in dashboard_data:
        visual_count = dashboard_data['visual_analysis'].get('total_visuals', 0)
    
    st.write(f"**Total Visuals:** {visual_count}")
    
    # Try to get visual types breakdown
    visual_types = {}
    if 'analysis_details' in dashboard_data:
        visual_types = dashboard_data['analysis_details'].get('visual_analysis_summary', {}).get('visual_types_distribution', {})
    elif 'visual_analysis' in dashboard_data:
        visual_types = dashboard_data['visual_analysis'].get('visual_types', {})
    
    if visual_types:
        st.write("**Visual Types:**")
        for vtype, count in visual_types.items():
            st.write(f"  • {vtype}: {count}")
    
    # KPIs
    kpi_count = 0
    if 'kpi_cards' in dashboard_data:
        kpi_count = len(dashboard_data['kpi_cards'])
    elif 'visual_analysis' in dashboard_data:
        kpis = dashboard_data['visual_analysis'].get('kpis', [])
        kpi_count = len(kpis)
    
    # Removed KPI display as backend doesn't calculate this
    
    # Metadata summary
    measures_count = 0
    tables_count = 0
    
    if 'measures' in dashboard_data:
        measures_count = len(dashboard_data['measures'])
    elif 'metadata_summary' in dashboard_data:
        measures_count = dashboard_data['metadata_summary'].get('total_measures', 0)
        
    if 'tables' in dashboard_data:
        tables_count = len(dashboard_data['tables'])
    elif 'metadata_summary' in dashboard_data:
        tables_count = dashboard_data['metadata_summary'].get('total_tables', 0)
    
    st.write(f"**Measures:** {measures_count}")
    st.write(f"**Tables:** {tables_count}")
    
    # Show relationships if available
    relationships_count = 0
    if 'relationships' in dashboard_data:
        relationships_count = len(dashboard_data['relationships'])
    elif 'metadata_summary' in dashboard_data:
        relationships_count = dashboard_data['metadata_summary'].get('total_relationships', 0)
    
    if relationships_count > 0:
        st.write(f"**Relationships:** {relationships_count}")
    
    # Show complexity if available
    if 'metadata_summary' in dashboard_data:
        complexity = dashboard_data['metadata_summary'].get('complexity_score', 0)
        if complexity > 0:
            if complexity > 7:
                st.write(f"**Complexity:** 🔴 High ({complexity:.1f}/10)")
            elif complexity > 4:
                st.write(f"**Complexity:** 🟡 Medium ({complexity:.1f}/10)")
            else:
                st.write(f"**Complexity:** 🟢 Low ({complexity:.1f}/10)")
    
    # Show a small screenshot preview if available
    if 'view_summaries' in dashboard_data:
        view_summaries = dashboard_data.get('view_summaries', [])
        if view_summaries and len(view_summaries) > 0:
            first_view = view_summaries[0]
            if 'data' in first_view:
                import base64
                try:
                    img_data = base64.b64decode(first_view['data'])
                    st.image(img_data, caption="Dashboard Preview", use_container_width=True)
                except Exception:
                    pass

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
    
    # Debug: Show results structure
    with st.expander("🔍 Debug: Analysis Results Structure", expanded=False):
        st.json(results)
    
    # Summary metrics - handle both data structures
    st.subheader("📊 Analysis Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    # Handle different data structures
    if 'data' in results:  # API mode structure
        data = results['data']
        dashboards_count = data.get('dashboards_processed', 0)
        views_count = data.get('total_views', 0)
        pairs_count = data.get('similarity_pairs', 0)
        groups_count = data.get('consolidation_groups', 0)
    elif 'phase2_results' in results:  # Local analysis mode structure
        phase2 = results['phase2_results']
        similarity_scores = results.get('similarity_scores', [])
        consolidated_groups = results.get('consolidated_groups', [])
        
        # Calculate metrics from similarity scores
        unique_dashboards = set()
        for s in similarity_scores:
            unique_dashboards.add(s.get('dashboard1_name', ''))
            unique_dashboards.add(s.get('dashboard2_name', ''))
        
        dashboards_count = len(unique_dashboards)
        views_count = sum([d.get('total_pages', 1) for d in st.session_state.get('processed_dashboards', [])])
        pairs_count = len(similarity_scores)
        groups_count = len(consolidated_groups)
    else:  # Try to get from processed_dashboards as fallback
        processed = st.session_state.get('processed_dashboards', [])
        dashboards_count = len(processed)
        views_count = sum([d.get('total_pages', 1) for d in processed])
        pairs_count = 0  # Will be calculated from similarity data
        groups_count = 0
    
    with col1:
        st.metric("Dashboards Analyzed", dashboards_count)
    with col2:
        st.metric("Total Views", views_count)
    with col3:
        st.metric("Similarity Pairs", pairs_count)
    with col4:
        st.metric("Consolidation Groups", groups_count)
    
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
            
            # Try to get similarity scores from multiple sources
            scores = []
            if similarity_data.get('similarity_scores'):
                scores = similarity_data['similarity_scores']
            elif hasattr(st.session_state, 'analysis_results') and st.session_state.analysis_results:
                # Try to get from session state analysis results
                if 'similarity_scores' in st.session_state.analysis_results:
                    scores = st.session_state.analysis_results['similarity_scores']
                elif 'phase2_results' in st.session_state.analysis_results:
                    phase2 = st.session_state.analysis_results['phase2_results']
                    scores = phase2.get('detailed_scores', [])
            
            # Create similarity matrix visualization
            if scores:
                
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
    elif st.session_state.stage == 'local_mode_selection':
        render_local_mode_selection()
    elif st.session_state.stage == 'folder_selection':
        render_folder_selection()
    elif st.session_state.stage == 'pbi_extraction':
        render_pbi_extraction()
    elif st.session_state.stage == 'screenshot_mapping':
        render_screenshot_mapping()
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