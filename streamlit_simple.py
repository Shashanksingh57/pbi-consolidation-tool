# Simplified version to test the main structure
import streamlit as st

st.set_page_config(
    page_title="Power BI Dashboard Consolidation Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Test CSS loading
st.markdown("""
<style>
.stButton > button {
    background-color: #0C62FB;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# Test header
st.markdown("""
<div style='background: linear-gradient(135deg, #0C62FB 0%, #0952D0 100%); 
            padding: 2rem; 
            border-radius: 10px; 
            margin-bottom: 2rem;'>
    <h1 style='color: white; margin: 0;'>
        📊 Power BI Dashboard Consolidation Tool
    </h1>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'stage' not in st.session_state:
    st.session_state.stage = 'setup'

# Test sidebar
with st.sidebar:
    st.markdown("### 🔧 Navigation")
    if st.button("Test Button"):
        st.success("Button works!")

# Test main content
st.header("🎯 Dashboard Setup")
st.write("This is a test of the main application structure.")

num_dashboards = st.number_input("How many dashboards?", min_value=2, max_value=10, value=2)
st.info(f"You selected {num_dashboards} dashboards")

if st.button("Test Analysis"):
    st.success("Analysis would start here!")
    st.balloons()