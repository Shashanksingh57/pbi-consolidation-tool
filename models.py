# models.py - Pydantic models for Power BI Dashboard Consolidation Tool

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

# ─── Visual Analysis Models ─────────────────────────────────────────────────

class VisualElement(BaseModel):
    """Represents a visual element detected in dashboard screenshot"""
    visual_type: str = Field(..., description="Type of visual (bar, line, table, card, etc.)")
    title: Optional[str] = Field(None, description="Title of the visual")
    position: Dict[str, int] = Field(default_factory=dict, description="Position coordinates (x, y, width, height)")
    data_fields: List[str] = Field(default_factory=list, description="Detected data fields/columns")
    chart_properties: Dict[str, Any] = Field(default_factory=dict, description="Chart-specific properties")
    page_name: str = Field(..., description="Dashboard page this visual belongs to")
    referenced_measures: Optional[List[Dict[str, Any]]] = Field(None, description="Measures linked to this visual with confidence scores")

class KPICard(BaseModel):
    """Represents a KPI card detected in dashboard"""
    title: str = Field(..., description="KPI title")
    value_format: Optional[str] = Field(None, description="Number formatting (currency, percentage, etc.)")
    trend_indicator: Optional[str] = Field(None, description="Trend direction (up, down, neutral)")
    position: Dict[str, int] = Field(default_factory=dict, description="Position on dashboard")

class FilterElement(BaseModel):
    """Represents filter elements detected in dashboard"""
    filter_type: str = Field(..., description="Type of filter (dropdown, slicer, date picker, etc.)")
    field_name: Optional[str] = Field(None, description="Field being filtered")
    filter_values: List[str] = Field(default_factory=list, description="Available filter options if detected")

# ─── DAX and Metadata Models ────────────────────────────────────────────────

class DAXMeasure(BaseModel):
    """Represents a DAX measure from metadata export"""
    measure_name: str = Field(..., description="Name of the measure")
    dax_formula: str = Field(..., description="DAX formula definition")
    table_name: str = Field(..., description="Table containing the measure")
    description: Optional[str] = Field(None, description="Measure description")
    format_string: Optional[str] = Field(None, description="Number formatting")

class DataTable(BaseModel):
    """Represents a data table from metadata export"""
    table_name: str = Field(..., description="Name of the table")
    column_count: int = Field(..., description="Number of columns")
    row_count: Optional[int] = Field(None, description="Number of rows if available")
    columns: List[str] = Field(default_factory=list, description="Column names")
    table_type: str = Field(default="fact", description="Table type (fact, dimension, bridge)")

class DataSource(BaseModel):
    """Represents a data source connection"""
    source_name: str = Field(..., description="Name of the data source")
    source_type: str = Field(..., description="Type (SQL Server, Excel, etc.)")
    connection_details: Optional[Dict[str, str]] = Field(None, description="Connection parameters")

class Relationship(BaseModel):
    """Represents relationships between tables"""
    from_table: str = Field(..., description="Source table")
    to_table: str = Field(..., description="Target table")
    from_column: str = Field(..., description="Source column")
    to_column: str = Field(..., description="Target column")
    relationship_type: str = Field(default="one_to_many", description="Relationship cardinality")

# ─── Enhanced Analysis Models for Transparency ─────────────────────────────

class AnalysisDetails(BaseModel):
    """Detailed analysis information for transparency"""
    visual_analysis_summary: Dict[str, Any] = Field(default_factory=dict, description="GPT-4 Vision analysis summary")
    raw_visual_extraction: List[Dict[str, Any]] = Field(default_factory=list, description="Raw visual element extraction data")
    dax_complexity_metrics: Dict[str, Any] = Field(default_factory=dict, description="DAX formula complexity analysis")
    data_model_metrics: Dict[str, Any] = Field(default_factory=dict, description="Data model analysis metrics")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing timestamps and metadata")

class PageScreenshot(BaseModel):
    """Represents a screenshot of a specific dashboard page"""
    page_name: str = Field(..., description="Name of the dashboard page")
    page_index: int = Field(..., description="Index of the page in the dashboard")
    screenshot_filename: Optional[str] = Field(None, description="Screenshot file name")
    screenshot_data: Optional[bytes] = Field(None, description="Screenshot binary data")
    upload_timestamp: datetime = Field(default_factory=datetime.now, description="When screenshot was uploaded")
    visual_analysis_results: Optional[Dict[str, Any]] = Field(None, description="GPT-4 Vision analysis results for this page")

class DashboardProfile(BaseModel):
    """Complete profile of a Power BI dashboard with enhanced transparency"""
    dashboard_id: str = Field(..., description="Unique identifier for dashboard")
    dashboard_name: str = Field(..., description="Human-readable dashboard name")
    user_provided_name: Optional[str] = Field(None, description="User's custom name for this dashboard")
    created_at: datetime = Field(default_factory=datetime.now, description="Profile creation timestamp")

    # Visual elements (enhanced for transparency)
    visual_elements: List[VisualElement] = Field(default_factory=list)
    kpi_cards: List[KPICard] = Field(default_factory=list)
    filters: List[FilterElement] = Field(default_factory=list)

    # Data model elements
    measures: List[DAXMeasure] = Field(default_factory=list)
    tables: List[DataTable] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    data_sources: List[DataSource] = Field(default_factory=list)

    # Page-specific screenshots and analysis
    page_screenshots: List[PageScreenshot] = Field(default_factory=list, description="Screenshots for each dashboard page")

    # Computed properties
    total_pages: int = Field(default=1, description="Number of dashboard pages")
    complexity_score: Optional[float] = Field(None, description="Computed complexity score")

    # Enhanced transparency features
    analysis_details: AnalysisDetails = Field(default_factory=AnalysisDetails, description="Detailed analysis information")
    extraction_confidence: Dict[str, float] = Field(default_factory=dict, description="Confidence scores for different extraction phases")
    
    def get_display_name(self) -> str:
        """Get the most appropriate display name for the dashboard"""
        return self.user_provided_name or self.dashboard_name
    
    def get_visual_summary(self) -> Dict[str, Any]:
        """Get a summary of visual elements for display"""
        visual_types = {}
        for element in self.visual_elements:
            vtype = element.visual_type
            visual_types[vtype] = visual_types.get(vtype, 0) + 1
        
        return {
            "total_elements": len(self.visual_elements),
            "visual_types": visual_types,
            "kpi_count": len(self.kpi_cards),
            "filter_count": len(self.filters),
            "measure_count": len(self.measures),
            "table_count": len(self.tables),
            "relationship_count": len(self.relationships)
        }

# ─── Similarity Analysis Models ─────────────────────────────────────────────

class SimilarityBreakdown(BaseModel):
    """Detailed breakdown of similarity scores"""
    measures_score: float = Field(..., description="Similarity score for measures (0-1)")
    visuals_score: float = Field(..., description="Similarity score for visuals (0-1)")
    data_model_score: float = Field(..., description="Similarity score for data model (0-1)")
    layout_score: float = Field(..., description="Similarity score for layout (0-1)")
    filters_score: float = Field(..., description="Similarity score for filters (0-1)")

class SimilarityScore(BaseModel):
    """Similarity score between two dashboards"""
    dashboard1_id: str = Field(..., description="First dashboard ID")
    dashboard2_id: str = Field(..., description="Second dashboard ID")
    dashboard1_name: str = Field(..., description="First dashboard name")
    dashboard2_name: str = Field(..., description="Second dashboard name")
    total_score: float = Field(..., description="Overall similarity score (0-1)")
    breakdown: SimilarityBreakdown = Field(..., description="Detailed score breakdown")
    computed_at: datetime = Field(default_factory=datetime.now)

# ─── Consolidation Models ───────────────────────────────────────────────────

class ConsolidationRecommendation(BaseModel):
    """Recommendation for dashboard consolidation"""
    action: str = Field(..., description="Recommended action (merge, consolidate, review)")
    reason: str = Field(..., description="Explanation for recommendation")
    effort_estimate: str = Field(..., description="Estimated effort (low, medium, high)")
    priority: int = Field(..., description="Priority ranking (1-5)")

class ConsolidationGroup(BaseModel):
    """Group of similar dashboards for consolidation"""
    group_id: str = Field(..., description="Unique group identifier")
    dashboard_ids: List[str] = Field(..., description="Dashboard IDs in this group")
    dashboard_names: List[str] = Field(..., description="Dashboard names in this group")
    average_similarity: float = Field(..., description="Average similarity score within group")
    recommendation: ConsolidationRecommendation = Field(..., description="Consolidation recommendation")
    created_at: datetime = Field(default_factory=datetime.now)

# ─── Batch Analysis Models ──────────────────────────────────────────────────

class DashboardView(BaseModel):
    """Represents a single view/page of a dashboard"""
    view_name: str = Field(..., description="Name of the view/page")
    custom_name: Optional[str] = Field(None, description="User-provided custom name for the view")
    screenshot_filename: Optional[str] = Field(None, description="Screenshot file name")
    screenshot_data: Optional[bytes] = Field(None, description="Screenshot binary data")

class DashboardInput(BaseModel):
    """Input model for a single dashboard with multiple views and metadata"""
    dashboard_id: str = Field(..., description="Unique dashboard identifier")
    dashboard_name: str = Field(..., description="Dashboard display name")
    views: List[DashboardView] = Field(..., description="List of dashboard views/pages")
    metadata_files: List[str] = Field(default_factory=list, description="List of metadata file names")
    metadata_data: Optional[Dict[str, bytes]] = Field(None, description="Metadata file contents")

class BatchAnalysisRequest(BaseModel):
    """Request for batch analysis of multiple dashboards"""
    dashboards: List[DashboardInput] = Field(..., description="List of dashboards to analyze")
    analysis_config: Optional['AnalysisConfig'] = Field(None, description="Analysis configuration")

# ─── Decoupled Analysis Models ─────────────────────────────────────────────

class ProfileExtractionRequest(BaseModel):
    """Request for generating a complete dashboard profile (decoupled from scoring)"""
    dashboard_id: str = Field(..., description="Unique dashboard identifier")
    dashboard_name: str = Field(..., description="Dashboard display name")
    user_provided_name: Optional[str] = Field(None, description="User's custom name for the dashboard")
    include_analysis_details: bool = Field(default=True, description="Include detailed analysis data")

class ProfileExtractionResponse(BaseModel):
    """Response containing a complete dashboard profile"""
    success: bool = Field(..., description="Extraction success status")
    profile: Optional[DashboardProfile] = Field(None, description="Extracted dashboard profile")
    extraction_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of extraction process")
    processing_time: float = Field(..., description="Total processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now)

class ScoringRequest(BaseModel):
    """Request for similarity scoring using existing profiles"""
    profile_ids: List[str] = Field(..., description="List of dashboard profile IDs to compare")
    similarity_config: Optional['SimilarityAnalysisRequest'] = Field(None, description="Similarity analysis configuration")
    include_detailed_breakdown: bool = Field(default=True, description="Include detailed similarity breakdown")

class ScoringResponse(BaseModel):
    """Response containing similarity scores and recommendations"""
    success: bool = Field(..., description="Scoring success status")
    similarity_matrix: List[List[float]] = Field(default_factory=list, description="Similarity score matrix")
    detailed_scores: List[SimilarityScore] = Field(default_factory=list, description="Detailed pairwise scores")
    consolidation_groups: List[ConsolidationGroup] = Field(default_factory=list, description="Recommended consolidation groups")
    scoring_metadata: Dict[str, Any] = Field(default_factory=dict, description="Scoring process metadata")
    processing_time: float = Field(..., description="Scoring processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now)

# ─── Request/Response Models ────────────────────────────────────────────────

class VisualAnalysisRequest(BaseModel):
    """Request for visual analysis of dashboard screenshots"""
    dashboard_id: str = Field(..., description="Unique dashboard identifier")
    dashboard_name: Optional[str] = Field(None, description="Dashboard name")

class MetadataUploadRequest(BaseModel):
    """Request for uploading dashboard metadata"""
    dashboard_id: str = Field(..., description="Dashboard identifier")
    metadata_type: str = Field(default="dax_studio", description="Type of metadata export")

class SimilarityAnalysisRequest(BaseModel):
    """Request for similarity analysis"""
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity threshold")
    weights: Optional[Dict[str, float]] = Field(
        default_factory=lambda: {
            "measures": 0.4,
            "visuals": 0.3,
            "data_model": 0.3
        },
        description="Weights for different similarity components"
    )

class ConsolidationReportRequest(BaseModel):
    """Request for consolidation report generation"""
    format: str = Field(default="json", description="Report format (json, excel, pdf)")
    include_details: bool = Field(default=True, description="Include detailed analysis")

class AnalysisResponse(BaseModel):
    """Generic response for analysis operations"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.now)

# ─── Configuration Models ───────────────────────────────────────────────────

class AnalysisConfig(BaseModel):
    """Configuration for analysis parameters"""
    visual_analysis_model: str = Field(default="gpt-4-vision-preview", description="GPT model for visual analysis")
    similarity_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "measures": 0.4,
            "visuals": 0.3,
            "data_model": 0.2,
            "layout": 0.1
        }
    )
    consolidation_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "merge": 0.85,
            "review": 0.70,
            "ignore": 0.50
        }
    )
    max_file_size_mb: int = Field(default=10, description="Maximum file size for uploads")
    supported_image_formats: List[str] = Field(
        default_factory=lambda: ["png", "jpg", "jpeg", "bmp", "tiff"]
    )