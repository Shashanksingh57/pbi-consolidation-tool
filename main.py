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
    DashboardInput, DashboardView, ProfileExtractionRequest, ProfileExtractionResponse,
    ScoringRequest, ScoringResponse, AnalysisDetails
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
            metadata = await metadata_processor.parse_dax_studio_export(file_content.decode('utf-8-sig'))
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
                dashboard_name=files_data['name'],
                user_provided_name=files_data['name']  # Store user-provided name
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
                    view_file.seek(0)
                    file_content = view_file.read()
                    view_data = base64.b64encode(file_content).decode('utf-8')
                    view_summaries.append({
                        'name': f"View {i+1}",
                        'data': view_data,
                        'type': view_file.content_type
                    })
            
            # Process metadata
            metadata_summary = {}
            if files_data['metadata']:
                # Read metadata file contents async
                metadata_contents = []
                for metadata_file in files_data['metadata']:
                    file_content = await metadata_file.read()
                    csv_content = file_content.decode('utf-8-sig')
                    metadata_contents.append(csv_content)
                
                # Process with synchronous method
                metadata_results = metadata_processor.analyze_metadata_files(
                    metadata_contents, dashboard_id
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

# ─── NEW DECOUPLED ANALYSIS ENDPOINTS ───────────────────────────────────────

@app.post("/api/v1/extract-profile", dependencies=[Depends(verify_token)], response_model=ProfileExtractionResponse)
async def extract_dashboard_profile(
    files: List[UploadFile] = File(...),
    request_data: str = None
):
    """Extract complete dashboard profile (Phase 1: Data Extraction)"""
    start_time = time.time()
    
    try:
        # Parse request data
        extraction_request = ProfileExtractionRequest(
            dashboard_id="dashboard_temp",
            dashboard_name="Temp Dashboard"
        )
        
        if request_data:
            try:
                data = json.loads(request_data)
                extraction_request = ProfileExtractionRequest(**data)
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse request_data: {e}")
        
        logger.info(f"Extracting profile for dashboard: {extraction_request.dashboard_name}")
        
        # Initialize analyzers
        visual_analyzer = VisualAnalyzer(client)
        metadata_processor = MetadataProcessor()
        
        # Separate files by type
        image_files = []
        metadata_files = []
        
        for file in files:
            content_type = file.content_type or ""
            filename = file.filename.lower()
            
            if content_type.startswith('image/') or filename.endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(file)
            elif filename.endswith('.csv'):
                metadata_files.append(file)
        
        # Create dashboard profile with enhanced transparency
        profile = DashboardProfile(
            dashboard_id=extraction_request.dashboard_id,
            dashboard_name=extraction_request.dashboard_name,
            user_provided_name=extraction_request.user_provided_name,
            total_pages=len(image_files)
        )
        
        analysis_details = AnalysisDetails()
        extraction_summary = {
            "total_files_processed": len(files),
            "image_files_count": len(image_files),
            "metadata_files_count": len(metadata_files),
            "extraction_phases": []
        }
        
        # Phase 1: Visual Analysis
        if image_files:
            logger.info("Starting visual analysis phase...")
            phase_start = time.time()
            
            try:
                visual_result = await visual_analyzer.analyze_multiple_images(
                    image_files, 
                    extraction_request.dashboard_id,
                    extraction_request.dashboard_name
                )
                
                profile.visual_elements = visual_result.get('visual_elements', [])
                profile.kpi_cards = visual_result.get('kpi_cards', [])
                profile.filters = visual_result.get('filters', [])
                
                # Store detailed analysis for transparency
                analysis_details.visual_analysis_summary = visual_result.get('summary', {})
                analysis_details.raw_visual_extraction = [
                    element.model_dump() for element in profile.visual_elements
                ]
                
                profile.extraction_confidence['visual_analysis'] = 0.85  # Mock confidence score
                
                phase_time = time.time() - phase_start
                extraction_summary["extraction_phases"].append({
                    "phase": "visual_analysis",
                    "duration_seconds": phase_time,
                    "elements_extracted": len(profile.visual_elements),
                    "success": True
                })
                
                logger.info(f"Visual analysis completed in {phase_time:.2f}s: {len(profile.visual_elements)} elements")
                
            except Exception as e:
                logger.error(f"Visual analysis failed: {str(e)}")
                extraction_summary["extraction_phases"].append({
                    "phase": "visual_analysis",
                    "duration_seconds": time.time() - phase_start,
                    "error": str(e),
                    "success": False
                })
        
        # Phase 2: Metadata Analysis
        if metadata_files:
            logger.info("Starting metadata analysis phase...")
            phase_start = time.time()
            
            try:
                for metadata_file in metadata_files:
                    metadata_content = await metadata_file.read()
                    csv_data = metadata_content.decode('utf-8')
                    
                    # Process metadata using enhanced processor
                    metadata_result = metadata_processor.parse_dax_studio_export(csv_data)
                    
                    profile.measures.extend(metadata_result.get('measures', []))
                    profile.tables.extend(metadata_result.get('tables', []))
                    profile.relationships.extend(metadata_result.get('relationships', []))
                    profile.data_sources.extend(metadata_result.get('data_sources', []))
                
                # Store metadata analysis details
                analysis_details.dax_complexity_metrics = {
                    "total_measures": len(profile.measures),
                    "total_tables": len(profile.tables),
                    "total_relationships": len(profile.relationships),
                    "complexity_indicators": {
                        "avg_measure_length": sum(len(m.dax_formula) for m in profile.measures) / len(profile.measures) if profile.measures else 0,
                        "unique_functions_used": len(set()),  # Would be calculated from DAX formulas
                        "max_table_columns": max(t.column_count for t in profile.tables) if profile.tables else 0
                    }
                }
                
                profile.extraction_confidence['metadata_analysis'] = 0.90
                
                phase_time = time.time() - phase_start
                extraction_summary["extraction_phases"].append({
                    "phase": "metadata_analysis",
                    "duration_seconds": phase_time,
                    "measures_extracted": len(profile.measures),
                    "tables_extracted": len(profile.tables),
                    "relationships_extracted": len(profile.relationships),
                    "success": True
                })
                
                logger.info(f"Metadata analysis completed in {phase_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Metadata analysis failed: {str(e)}")
                extraction_summary["extraction_phases"].append({
                    "phase": "metadata_analysis",
                    "duration_seconds": time.time() - phase_start,
                    "error": str(e),
                    "success": False
                })
        
        # Phase 3: Complexity Scoring
        complexity_start = time.time()
        try:
            # Calculate complexity score
            visual_complexity = len(profile.visual_elements) * 0.5
            data_complexity = len(profile.measures) * 0.3 + len(profile.tables) * 0.2
            profile.complexity_score = min((visual_complexity + data_complexity) / 10, 10.0)
            
            analysis_details.processing_metadata = {
                "total_processing_time": time.time() - start_time,
                "extraction_timestamp": profile.created_at.isoformat(),
                "analysis_model_version": "v2.0_enhanced",
                "confidence_scores": profile.extraction_confidence
            }
            
            profile.analysis_details = analysis_details
            
            extraction_summary["extraction_phases"].append({
                "phase": "complexity_calculation",
                "duration_seconds": time.time() - complexity_start,
                "complexity_score": profile.complexity_score,
                "success": True
            })
            
        except Exception as e:
            logger.error(f"Complexity calculation failed: {str(e)}")
            extraction_summary["extraction_phases"].append({
                "phase": "complexity_calculation",
                "duration_seconds": time.time() - complexity_start,
                "error": str(e),
                "success": False
            })
        
        # Store profile for future scoring
        dashboard_profiles[profile.dashboard_id] = profile
        
        total_time = time.time() - start_time
        logger.info(f"Profile extraction completed in {total_time:.2f}s for {profile.get_display_name()}")
        
        return ProfileExtractionResponse(
            success=True,
            profile=profile,
            extraction_summary=extraction_summary,
            processing_time=total_time
        )
        
    except Exception as e:
        logger.error(f"Error in profile extraction: {str(e)}")
        return ProfileExtractionResponse(
            success=False,
            profile=None,
            extraction_summary={"error": str(e)},
            processing_time=time.time() - start_time
        )

@app.post("/api/v1/score-profiles", dependencies=[Depends(verify_token)], response_model=ScoringResponse)
async def score_dashboard_profiles(request: ScoringRequest):
    """Calculate similarity scores from existing profiles (Phase 2: Similarity Scoring)"""
    start_time = time.time()
    
    try:
        logger.info(f"Scoring {len(request.profile_ids)} dashboard profiles")
        
        # Validate profile IDs exist
        profiles = []
        for profile_id in request.profile_ids:
            if profile_id not in dashboard_profiles:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Dashboard profile '{profile_id}' not found. Available: {list(dashboard_profiles.keys())}"
                )
            profiles.append(dashboard_profiles[profile_id])
        
        if len(profiles) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 profiles required for similarity analysis"
            )
        
        # Initialize similarity engine
        similarity_engine = SimilarityEngine()
        
        # Configure weights from request if provided
        if request.similarity_config and request.similarity_config.weights:
            similarity_engine.weights = request.similarity_config.weights
        
        # Calculate similarity matrix
        logger.info("Calculating similarity scores...")
        similarity_results = similarity_engine.calculate_similarity_matrix(profiles)
        
        detailed_scores = []
        similarity_matrix = []
        
        # Process results
        for i, profile1 in enumerate(profiles):
            row = []
            for j, profile2 in enumerate(profiles):
                if i <= j:
                    # Calculate detailed similarity
                    similarity_score = similarity_engine.calculate_detailed_similarity(profile1, profile2)
                    
                    if i < j:  # Only store unique pairs
                        detailed_scores.append(similarity_score)
                        # Store in global state for backwards compatibility
                        similarity_scores.append(similarity_score)
                    
                    row.append(similarity_score.total_score)
                else:
                    # Symmetric matrix
                    row.append(similarity_matrix[j][i])
            similarity_matrix.append(row)
        
        # Generate consolidation groups
        consolidation_groups_result = similarity_engine.generate_consolidation_groups(detailed_scores)
        
        # Update global state for backwards compatibility
        consolidation_groups.extend(consolidation_groups_result)
        
        # Prepare scoring metadata
        scoring_metadata = {
            "profiles_analyzed": len(profiles),
            "total_comparisons": len(detailed_scores),
            "similarity_weights": similarity_engine.weights,
            "consolidation_threshold": request.similarity_config.similarity_threshold if request.similarity_config else 0.7,
            "high_similarity_pairs": len([s for s in detailed_scores if s.total_score >= 0.85]),
            "medium_similarity_pairs": len([s for s in detailed_scores if 0.70 <= s.total_score < 0.85]),
            "processing_timestamp": time.time()
        }
        
        total_time = time.time() - start_time
        logger.info(f"Scoring completed in {total_time:.2f}s: {len(detailed_scores)} comparisons, {len(consolidation_groups_result)} groups")
        
        return ScoringResponse(
            success=True,
            similarity_matrix=similarity_matrix,
            detailed_scores=detailed_scores,
            consolidation_groups=consolidation_groups_result,
            scoring_metadata=scoring_metadata,
            processing_time=total_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in scoring profiles: {str(e)}")
        return ScoringResponse(
            success=False,
            similarity_matrix=[],
            detailed_scores=[],
            consolidation_groups=[],
            scoring_metadata={"error": str(e)},
            processing_time=time.time() - start_time
        )

@app.get("/api/v1/profiles/{profile_id}/details", dependencies=[Depends(verify_token)])
async def get_profile_details(profile_id: str):
    """Get detailed analysis information for a specific profile (transparency endpoint)"""
    try:
        if profile_id not in dashboard_profiles:
            raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
        
        profile = dashboard_profiles[profile_id]
        
        return {
            "success": True,
            "profile": profile,
            "visual_breakdown": {
                "total_elements": len(profile.visual_elements),
                "elements_by_type": profile.get_visual_summary()["visual_types"],
                "raw_elements": [element.model_dump() for element in profile.visual_elements]
            },
            "data_model_breakdown": {
                "measures": [measure.model_dump() for measure in profile.measures],
                "tables": [table.model_dump() for table in profile.tables],
                "relationships": [rel.model_dump() for rel in profile.relationships]
            },
            "analysis_details": profile.analysis_details.model_dump(),
            "confidence_scores": profile.extraction_confidence
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile details: {str(e)}")
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