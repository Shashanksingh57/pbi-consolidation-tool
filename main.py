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
    ConsolidationReportRequest, AnalysisResponse, BatchAnalysisRequest,
    DashboardInput, DashboardView
)
from analyzers.visual_analyzer import VisualAnalyzer
from analyzers.metadata_processor import MetadataProcessor
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
metadata_processor = MetadataProcessor()
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
            metadata = await metadata_processor.parse_dax_studio_export(file_content.decode('utf-8'))
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

@app.post("/api/v1/process-dashboards", dependencies=[Depends(verify_token)])
async def process_dashboards(files: List[UploadFile] = File(...), dashboard_info: str = None):
    """Process dashboards to extract visual and metadata information"""
    try:
        logger.info(f"Starting dashboard processing with {len(files)} files")
        
        # Parse dashboard info from JSON if provided
        dashboard_names = {}
        if dashboard_info:
            try:
                info = json.loads(dashboard_info)
                dashboard_names = info.get('dashboard_names', {})
            except json.JSONDecodeError:
                logger.warning("Could not parse dashboard_info JSON")
        
        # Organize files by dashboard
        dashboard_files = {}
        
        for file in files:
            # Parse filename to extract dashboard info
            # Expected format: dashboard_X_view_Y.ext or dashboard_X_metadata.csv
            filename = file.filename.lower()
            
            if 'dashboard_' in filename:
                parts = filename.split('_')
                if len(parts) >= 2:
                    dashboard_id = f"dashboard_{parts[1]}"
                    dashboard_num = parts[1]
                    
                    if dashboard_id not in dashboard_files:
                        # Use custom name if provided, otherwise fallback to generic name
                        custom_name = dashboard_names.get(dashboard_num, f"Dashboard {parts[1]}")
                        dashboard_files[dashboard_id] = {
                            'name': custom_name,
                            'views': [],
                            'metadata': []
                        }
                    
                    if 'metadata' in filename:
                        dashboard_files[dashboard_id]['metadata'].append(file)
                    elif 'view' in filename:
                        dashboard_files[dashboard_id]['views'].append(file)
        
        # Process each dashboard
        processed_dashboards = []
        
        for dashboard_id, files_data in dashboard_files.items():
            dashboard_profile = DashboardProfile(
                dashboard_id=dashboard_id,
                dashboard_name=files_data['name']
            )
            
            # Process views (screenshots)
            view_summaries = []
            if files_data['views']:
                visual_results = await visual_analyzer.analyze_multiple_images(
                    files_data['views'], dashboard_id, files_data['name']
                )
                dashboard_profile.visual_elements.extend(visual_results.get('visual_elements', []))
                dashboard_profile.kpi_cards.extend(visual_results.get('kpi_cards', []))
                dashboard_profile.filters.extend(visual_results.get('filters', []))
                dashboard_profile.total_pages = len(files_data['views'])
                
                # Store view summaries for the review stage
                for i, view_file in enumerate(files_data['views']):
                    await view_file.seek(0)
                    file_content = await view_file.read()
                    view_data = base64.b64encode(file_content).decode('utf-8')
                    view_summaries.append({
                        'name': f"View {i+1}",
                        'data': view_data,
                        'type': view_file.content_type
                    })
            
            # Process metadata
            metadata_summary = {}
            if files_data['metadata']:
                metadata_results = await metadata_processor.analyze_metadata_files(
                    files_data['metadata'], dashboard_id
                )
                dashboard_profile.measures.extend(metadata_results.get('measures', []))
                dashboard_profile.tables.extend(metadata_results.get('tables', []))
                dashboard_profile.relationships.extend(metadata_results.get('relationships', []))
                
                metadata_summary = metadata_results.get('summary', {})
            
            # Store in global profiles for later similarity analysis
            dashboard_profiles[dashboard_id] = dashboard_profile
            processed_dashboards.append({
                'profile': dashboard_profile,
                'view_summaries': view_summaries,
                'metadata_summary': metadata_summary
            })
        
        return AnalysisResponse(
            success=True,
            message=f"Dashboard processing completed for {len(processed_dashboards)} dashboards",
            data={
                "dashboards": [
                    {
                        "dashboard_id": item['profile'].dashboard_id,
                        "dashboard_name": item['profile'].dashboard_name,
                        "total_pages": item['profile'].total_pages,
                        "visual_elements_count": len(item['profile'].visual_elements),
                        "measures_count": len(item['profile'].measures),
                        "tables_count": len(item['profile'].tables),
                        "relationships_count": len(item['profile'].relationships),
                        "view_summaries": item['view_summaries'],
                        "metadata_summary": item['metadata_summary']
                    }
                    for item in processed_dashboards
                ]
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing dashboards: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/run-similarity", dependencies=[Depends(verify_token)])
async def run_similarity():
    """Run similarity analysis on processed dashboards"""
    try:
        logger.info("Running similarity analysis on processed dashboards")
        
        if len(dashboard_profiles) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 dashboards for similarity analysis")
        
        # Clear previous similarity results
        similarity_scores.clear()
        consolidation_groups.clear()
        
        # Run similarity analysis
        processed_dashboards = list(dashboard_profiles.values())
        similarity_results = similarity_engine.analyze_batch(processed_dashboards)
        similarity_scores.extend(similarity_results['similarity_scores'])
        consolidation_groups.extend(similarity_results['consolidation_groups'])
        
        return AnalysisResponse(
            success=True,
            message=f"Similarity analysis completed",
            data={
                "dashboards_analyzed": len(processed_dashboards),
                "similarity_pairs": len(similarity_scores),
                "consolidation_groups": len(consolidation_groups)
            }
        )
        
    except Exception as e:
        logger.error(f"Error in similarity analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/batch-analysis", dependencies=[Depends(verify_token)])
async def batch_analysis(files: List[UploadFile] = File(...), dashboard_info: str = None):
    """Legacy batch analysis endpoint - processes and runs similarity in one step"""
    try:
        # First process dashboards
        process_response = await process_dashboards(files, dashboard_info)
        
        if not process_response.success:
            return process_response
        
        # Then run similarity analysis
        similarity_response = await run_similarity()
        
        return AnalysisResponse(
            success=True,
            message=f"Complete batch analysis finished",
            data={
                "dashboards_processed": len(process_response.data.get('dashboards', [])),
                "total_views": sum(d.get('total_pages', 0) for d in process_response.data.get('dashboards', [])),
                "similarity_pairs": len(similarity_scores),
                "consolidation_groups": len(consolidation_groups)
            }
        )
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/api-analysis", dependencies=[Depends(verify_token)])
async def api_analysis(request_data: Dict[str, Any]):
    """Power BI API-based analysis endpoint"""
    try:
        logger.info("Starting Power BI API analysis")
        
        reports_data = request_data.get('reports', [])
        if not reports_data:
            raise HTTPException(status_code=400, detail="No reports data provided")
        
        processed_dashboards = []
        
        for report in reports_data:
            dashboard_id = f"api_{report['name'].replace(' ', '_')}"
            
            dashboard_profile = DashboardProfile(
                dashboard_id=dashboard_id,
                dashboard_name=report['name']
            )
            
            # Mock processing for now - in real implementation:
            # 1. Extract measures from report datasets
            # 2. Get report pages and their visuals
            # 3. Analyze relationships and data model
            
            dashboard_profile.total_pages = len(report.get('pages', ['Page1']))
            
            # Add mock data for demonstration
            dashboard_profile.measures = []  # Would populate from API
            dashboard_profile.visual_elements = []  # Would populate from API
            dashboard_profile.complexity_score = 5.0  # Mock score
            
            dashboard_profiles[dashboard_id] = dashboard_profile
            processed_dashboards.append(dashboard_profile)
        
        # Perform similarity analysis if we have multiple dashboards
        if len(processed_dashboards) > 1:
            similarity_results = similarity_engine.analyze_batch(processed_dashboards)
            similarity_scores.extend(similarity_results['similarity_scores'])
            consolidation_groups.extend(similarity_results['consolidation_groups'])
        
        return AnalysisResponse(
            success=True,
            message=f"API analysis completed for {len(processed_dashboards)} reports",
            data={
                "reports_processed": len(processed_dashboards),
                "total_pages": sum(d.total_pages for d in processed_dashboards),
                "similarity_pairs": len(similarity_scores),
                "consolidation_groups": len(consolidation_groups),
                "analysis_method": "power_bi_api"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in API analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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