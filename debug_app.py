import streamlit as st

st.title("🔍 Debug App")

try:
    st.write("Step 1: Basic import test...")
    import os
    import json
    import requests
    import pandas as pd
    st.success("✅ Basic imports OK")
    
    st.write("Step 2: Plotly import test...")
    import plotly.express as px
    import plotly.graph_objects as go
    st.success("✅ Plotly imports OK")
    
    st.write("Step 3: Session state test...")
    if 'test' not in st.session_state:
        st.session_state.test = "working"
    st.success(f"✅ Session state OK: {st.session_state.test}")
    
    st.write("Step 4: Complex UI test...")
    col1, col2 = st.columns(2)
    with col1:
        st.info("Column 1")
    with col2:
        st.warning("Column 2")
    
    with st.sidebar:
        st.write("Sidebar test")
    
    st.success("✅ All basic tests passed!")
    
    # Test the specific functions that might be causing issues
    st.write("Step 5: Testing our custom functions...")
    
    def test_initialize_session_state():
        if 'stage' not in st.session_state:
            st.session_state.stage = 'setup'
        return "✅ Session state init OK"
    
    st.write(test_initialize_session_state())
    
except Exception as e:
    st.error(f"❌ Error at step: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
    
st.write("🎉 Debug complete!")