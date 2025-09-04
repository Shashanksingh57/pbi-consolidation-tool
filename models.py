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

# ─── Dashboard Profile Models ───────────────────────────────────────────────

class DashboardProfile(BaseModel):
    """Complete profile of a Power BI dashboard"""
    dashboard_id: str = Field(..., description="Unique identifier for dashboard")
    dashboard_name: str = Field(..., description="Human-readable dashboard name")
    created_at: datetime = Field(default_factory=datetime.now, description="Profile creation timestamp")
    
    # Visual elements
    visual_elements: List[VisualElement] = Field(default_factory=list)
    kpi_cards: List[KPICard] = Field(default_factory=list)
    filters: List[FilterElement] = Field(default_factory=list)
    
    # Data model elements
    measures: List[DAXMeasure] = Field(default_factory=list)
    tables: List[DataTable] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    data_sources: List[DataSource] = Field(default_factory=list)
    
    # Computed properties
    total_pages: int = Field(default=1, description="Number of dashboard pages")
    complexity_score: Optional[float] = Field(None, description="Computed complexity score")

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