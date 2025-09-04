# Super simple working version - build up from basics
import streamlit as st
import os

# Page config
st.set_page_config(
    page_title="Power BI Dashboard Consolidation Tool",
    page_icon="📊",
    layout="wide"
)

# Simple CSS
st.markdown("""
<style>
.stButton > button {
    background-color: #0C62FB;
    color: white;
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)

# Simple header
st.markdown("""
<div style='background: linear-gradient(135deg, #0C62FB 0%, #0952D0 100%); 
            padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
    <h1 style='color: white; margin: 0;'>📊 Power BI Dashboard Consolidation Tool</h1>
    <p style='color: white; opacity: 0.95; margin-top: 0.5rem;'>
        Identify and consolidate duplicate dashboards using AI-powered analysis
    </p>
</div>
""", unsafe_allow_html=True)

# Simple session state
if 'stage' not in st.session_state:
    st.session_state.stage = 'setup'

# Simple sidebar
with st.sidebar:
    st.markdown("### 🔧 Navigation")
    st.write(f"Current Stage: {st.session_state.stage}")
    
    if st.button("Reset"):
        st.session_state.stage = 'setup'
        st.rerun()

# Main content
st.header("📊 Dashboard Consolidation Setup")

col1, col2 = st.columns([2, 1])

with col1:
    num_dashboards = st.number_input(
        "How many dashboards do you want to analyze?",
        min_value=2,
        max_value=10,
        value=2
    )

with col2:
    st.info(f"📊 Comparing {num_dashboards} dashboards")

st.divider()

# Simple form for each dashboard
for i in range(num_dashboards):
    with st.expander(f"Dashboard {i+1}: Configuration", expanded=(i==0)):
        dash_name = st.text_input(f"Dashboard Name", key=f"name_{i}", 
                                  placeholder="e.g., Sales Performance Dashboard")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📸 Screenshots")
            screenshots = st.file_uploader(
                "Upload screenshots", 
                type=['png', 'jpg', 'jpeg'], 
                accept_multiple_files=True,
                key=f"screenshots_{i}"
            )
            if screenshots:
                st.success(f"✓ {len(screenshots)} files uploaded")
        
        with col2:
            st.markdown("### 📊 Metadata")
            csv_file = st.file_uploader(
                "Upload CSV export",
                type=['csv'],
                key=f"csv_{i}"
            )
            if csv_file:
                st.success("✓ CSV uploaded")

st.divider()

if st.button("🚀 Start Analysis", type="primary"):
    st.success("Analysis would start here!")
    st.balloons()

st.write("✅ If you can see this, the working version is functioning correctly!")