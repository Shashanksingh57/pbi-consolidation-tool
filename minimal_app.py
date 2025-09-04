# Minimal working version to isolate the problem
import streamlit as st
import os

st.set_page_config(
    page_title="Power BI Dashboard Consolidation Tool",
    page_icon="📊",
    layout="wide"
)

# Test 1: Basic components
st.title("🧪 Minimal Test - Step by Step")

try:
    st.write("✅ Step 1: Basic write works")
    
    # Test 2: CSS
    st.markdown("""
    <style>
    .stButton > button {
        background-color: #0C62FB;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    st.write("✅ Step 2: CSS works")
    
    # Test 3: Session state
    if 'test_stage' not in st.session_state:
        st.session_state.test_stage = 'setup'
    st.write(f"✅ Step 3: Session state works - {st.session_state.test_stage}")
    
    # Test 4: Header HTML
    st.markdown("""
    <div style='background: linear-gradient(135deg, #0C62FB 0%, #0952D0 100%); 
                padding: 1rem; border-radius: 10px;'>
        <h2 style='color: white; margin: 0;'>📊 Header Test</h2>
    </div>
    """, unsafe_allow_html=True)
    st.write("✅ Step 4: HTML header works")
    
    # Test 5: Columns
    col1, col2 = st.columns(2)
    with col1:
        st.info("Column 1")
    with col2:
        st.warning("Column 2")
    st.write("✅ Step 5: Columns work")
    
    # Test 6: Sidebar
    with st.sidebar:
        st.write("Sidebar test")
        if st.button("Test Button"):
            st.success("Button clicked!")
    st.write("✅ Step 6: Sidebar works")
    
    # Test 7: Number input
    test_num = st.number_input("Test number input", min_value=1, max_value=10, value=2)
    st.write(f"✅ Step 7: Number input works - {test_num}")
    
    # Test 8: File uploader
    test_file = st.file_uploader("Test file upload", type=['png', 'jpg'])
    if test_file:
        st.success(f"✅ File uploaded: {test_file.name}")
    else:
        st.write("✅ Step 8: File uploader widget works")
        
    st.success("🎉 All basic components are working!")
    
    # Now test the specific functions that might be problematic
    st.header("🔍 Testing Our Custom Functions")
    
    # Import and test our functions one by one
    import importlib.util
    spec = importlib.util.spec_from_file_location("main_app", "./streamlit_app.py")
    main_app = importlib.util.module_from_spec(spec)
    
    st.write("✅ Step 9: Import successful")
    
    # Test initialize_session_state
    main_app.initialize_session_state()
    st.write("✅ Step 10: initialize_session_state works")
    
    # Test get_stage
    stage = main_app.get_stage()
    st.write(f"✅ Step 11: get_stage works - {stage}")
    
except Exception as e:
    st.error(f"❌ Error at step: {str(e)}")
    import traceback
    st.code(traceback.format_exc())

st.write("📝 If you see this message, the app is running successfully!")