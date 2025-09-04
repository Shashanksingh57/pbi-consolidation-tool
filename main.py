# main.py - Power BI Dashboard Consolidation Tool API

import os
import io
import json
import logging
import time
import base64
from typing import List, Dict, Any, Optional

from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from PIL import Image
import pandas as pd

from models import (
    DashboardProfile, SimilarityScore, ConsolidationGroup,
    VisualAnalysisRequest, MetadataUploadRequest, SimilarityAnalysisRequest,
    ConsolidationReportRequest, AnalysisResponse
)
from analyzers.visual_analyzer import VisualAnalyzer
from analyzers.dax_analyzer import DAXAnalyzer
from analyzers.similarity import SimilarityEngine
from utils.report_generator import ReportGenerator

# Configuration
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=900.0,  # 15 minutes timeout
    max_retries=2
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Power BI Dashboard Consolidation Tool")

# Authentication
security = HTTPBearer()
API_KEY = os.getenv("API_KEY", "supersecrettoken123")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token for authentication"""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Initialize analyzers
visual_analyzer = VisualAnalyzer(client)
dax_analyzer = DAXAnalyzer()
similarity_engine = SimilarityEngine()
report_generator = ReportGenerator()

# In-memory storage for demo (replace with database in production)
dashboard_profiles: Dict[str, DashboardProfile] = {}
similarity_scores: List[SimilarityScore] = []
consolidation_groups: List[ConsolidationGroup] = []

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Power BI Dashboard Consolidation Tool API", "status": "healthy"}

@app.post("/api/v1/capture-visual", dependencies=[Depends(verify_token)])
async def capture_visual_analysis(
    dashboard_id: str,
    files: List[UploadFile] = File(...),
    dashboard_name: str = ""
):
    """Process dashboard screenshots via GPT-4 Vision API"""
    try:
        logger.info(f"Processing visual analysis for dashboard: {dashboard_id}")
        
        # Validate files are images
        for file in files:
            if not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not an image")
        
        # Process each screenshot
        visual_elements = []
        for i, file in enumerate(files):
            # Read image
            image_data = await file.read()
            image = Image.open(io.BytesIO(image_data))
            
            # Analyze with GPT-4 Vision
            page_elements = await visual_analyzer.analyze_dashboard_screenshot(
                image, f"{dashboard_name}_page_{i+1}"
            )
            visual_elements.extend(page_elements)
        
        # Create dashboard profile with visual elements
        profile = DashboardProfile(
            dashboard_id=dashboard_id,
            dashboard_name=dashboard_name,
            visual_elements=visual_elements,
            measures=[],  # Will be filled by metadata upload
            tables=[],    # Will be filled by metadata upload
            data_sources=[]  # Will be filled by metadata upload
        )
        
        # Store profile
        dashboard_profiles[dashboard_id] = profile
        
        return AnalysisResponse(
            success=True,
            message=f"Successfully analyzed {len(files)} screenshots",
            data={
                "dashboard_id": dashboard_id,
                "visual_elements_count": len(visual_elements),
                "pages_processed": len(files)
            }
        )
        
    except Exception as e:
        logger.error(f"Error in visual analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/upload-metadata", dependencies=[Depends(verify_token)])
async def upload_metadata(
    dashboard_id: str,
    file: UploadFile = File(...),
    metadata_type: str = "dax_studio"
):
    """Accept DAX Studio CSV exports and other metadata"""
    try:
        logger.info(f"Processing metadata for dashboard: {dashboard_id}")
        
        if dashboard_id not in dashboard_profiles:
            raise HTTPException(status_code=404, detail="Dashboard profile not found. Please upload screenshots first.")
        
        # Read CSV file
        file_content = await file.read()
        
        # Parse metadata based on type
        if metadata_type == "dax_studio":
            metadata = await dax_analyzer.parse_dax_studio_export(file_content.decode('utf-8'))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported metadata type: {metadata_type}")
        
        # Update dashboard profile with metadata
        profile = dashboard_profiles[dashboard_id]
        profile.measures = metadata.get('measures', [])
        profile.tables = metadata.get('tables', [])
        profile.data_sources = metadata.get('data_sources', [])
        
        dashboard_profiles[dashboard_id] = profile
        
        return AnalysisResponse(
            success=True,
            message="Metadata uploaded successfully",
            data={
                "dashboard_id": dashboard_id,
                "measures_count": len(profile.measures),
                "tables_count": len(profile.tables),
                "data_sources_count": len(profile.data_sources)
            }
        )
        
    except Exception as e:
        logger.error(f"Error in metadata upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/analyze-similarity", dependencies=[Depends(verify_token)])
async def analyze_similarity():
    """Run similarity analysis on all uploaded dashboards"""
    try:
        logger.info("Starting similarity analysis")
        
        if len(dashboard_profiles) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 dashboards to compare")
        
        # Run pairwise comparison
        profiles = list(dashboard_profiles.values())
        global similarity_scores
        similarity_scores = similarity_engine.compare_all_dashboards(profiles)
        
        # Generate consolidation groups
        global consolidation_groups
        consolidation_groups = similarity_engine.generate_consolidation_groups(
            profiles, similarity_scores
        )
        
        return AnalysisResponse(
            success=True,
            message="Similarity analysis completed",
            data={
                "comparisons_made": len(similarity_scores),
                "consolidation_groups": len(consolidation_groups),
                "high_similarity_pairs": len([s for s in similarity_scores if s.total_score > 0.85])
            }
        )
        
    except Exception as e:
        logger.error(f"Error in similarity analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/generate-report", dependencies=[Depends(verify_token)])
async def generate_report(format: str = "json"):
    """Generate consolidation report"""
    try:
        logger.info(f"Generating report in format: {format}")
        
        if not consolidation_groups:
            raise HTTPException(status_code=400, detail="No consolidation analysis found. Run similarity analysis first.")
        
        # Generate report
        if format == "json":
            report = report_generator.generate_json_report(
                dashboard_profiles, similarity_scores, consolidation_groups
            )
        elif format == "excel":
            report = await report_generator.generate_excel_report(
                dashboard_profiles, similarity_scores, consolidation_groups
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
        
        return AnalysisResponse(
            success=True,
            message="Report generated successfully",
            data=report
        )
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard-profiles", dependencies=[Depends(verify_token)])
async def get_dashboard_profiles():
    """Get all uploaded dashboard profiles"""
    return {
        "profiles": list(dashboard_profiles.values()),
        "count": len(dashboard_profiles)
    }

@app.get("/api/v1/similarity-matrix", dependencies=[Depends(verify_token)])
async def get_similarity_matrix():
    """Get similarity matrix for visualization"""
    if not similarity_scores:
        raise HTTPException(status_code=400, detail="No similarity analysis found")
    
    return {
        "similarity_scores": similarity_scores,
        "consolidation_groups": consolidation_groups
    }

@app.delete("/api/v1/reset", dependencies=[Depends(verify_token)])
async def reset_analysis():
    """Reset all analysis data"""
    global dashboard_profiles, similarity_scores, consolidation_groups
    dashboard_profiles.clear()
    similarity_scores.clear()
    consolidation_groups.clear()
    
    return {"message": "Analysis data reset successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)