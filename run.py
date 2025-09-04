# run.py - Quick start script for both services

import subprocess
import sys
import time
import os
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import uvicorn
        import streamlit
        import fastapi
        import openai
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {str(e)}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_environment():
    """Check if environment is properly configured"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("Please copy .env.example to .env and configure your API keys")
        return False
    
    # Load and check required variables
    from dotenv import load_dotenv
    load_dotenv()
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key or openai_key.startswith("sk-your-"):
        print("❌ OPENAI_API_KEY not configured in .env")
        return False
    
    print("✅ Environment configuration looks good")
    return True

def start_backend():
    """Start the FastAPI backend"""
    print("🚀 Starting FastAPI backend on http://localhost:8000")
    return subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "main:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000",
        "--timeout-keep-alive", "900"
    ])

def start_frontend():
    """Start the Streamlit frontend"""
    print("🖥️ Starting Streamlit frontend on http://localhost:8501")
    return subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", 
        "streamlit_app.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ])

def main():
    """Main function to start both services"""
    print("=" * 60)
    print("Power BI Dashboard Consolidation Tool")
    print("=" * 60)
    
    # Pre-flight checks
    if not check_requirements():
        sys.exit(1)
    
    if not check_environment():
        sys.exit(1)
    
    try:
        # Start backend
        backend_process = start_backend()
        time.sleep(3)  # Give backend time to start
        
        # Check if backend started successfully
        if backend_process.poll() is not None:
            print("❌ Failed to start backend")
            sys.exit(1)
        
        # Start frontend
        frontend_process = start_frontend()
        time.sleep(2)  # Give frontend time to start
        
        # Check if frontend started successfully  
        if frontend_process.poll() is not None:
            print("❌ Failed to start frontend")
            backend_process.terminate()
            sys.exit(1)
        
        print("\n" + "=" * 60)
        print("✅ Both services started successfully!")
        print("📖 Backend API: http://localhost:8000")
        print("🔧 API Docs: http://localhost:8000/docs") 
        print("🖥️ Frontend UI: http://localhost:8501")
        print("=" * 60)
        print("\nPress Ctrl+C to stop both services")
        
        # Wait for user interruption
        try:
            backend_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping services...")
            
    except Exception as e:
        print(f"❌ Error starting services: {str(e)}")
        sys.exit(1)
    
    finally:
        # Cleanup processes
        try:
            if 'backend_process' in locals():
                backend_process.terminate()
            if 'frontend_process' in locals():
                frontend_process.terminate()
        except:
            pass
        
        print("👋 Services stopped")

if __name__ == "__main__":
    main()