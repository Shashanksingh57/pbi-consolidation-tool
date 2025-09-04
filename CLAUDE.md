# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Power BI Dashboard Consolidation Tool that identifies and consolidates duplicate dashboards using AI-powered analysis. The application uses FastAPI for the backend API and Streamlit for the frontend interface, with GPT-4 Vision for intelligent visual analysis and custom similarity algorithms for dashboard comparison.

Built as an extension of agent-bi-assistant-v2, following the same architectural patterns and design principles.

## Common Development Commands

### Running the Application

**Quick Start (both services)**:
```bash
cd pbi-consolidation-tool
python run.py
```

**Run Services Separately**:
```bash
# Backend API (Terminal 1) - with extended timeouts for AI processing
cd pbi-consolidation-tool
uvicorn main:app --reload --timeout-keep-alive 900 --host 0.0.0.0 --port 8000

# Frontend UI (Terminal 2)
cd pbi-consolidation-tool
streamlit run streamlit_app.py --server.port 8501
```

### Installation
```bash
cd pbi-consolidation-tool
python -m venv venv
source venv/bin/activate  # macOS/Linux
# OR
venv\\Scripts\\activate  # Windows
pip install -r requirements.txt
```

### Environment Setup
Create `.env` file with:
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
API_KEY=supersecrettoken123
GPT_MODEL=gpt-4-vision-preview
```

## High-Level Architecture

### Application Flow
1. **Dashboard Inventory** → User uploads screenshots and DAX Studio metadata
2. **Visual Analysis** → GPT-4 Vision extracts visual elements and layout
3. **Similarity Analysis** → Multi-dimensional comparison algorithm
4. **Consolidation Recommendations** → Automated grouping and action planning
5. **Report Generation** → JSON/Excel outputs for business decisions

### Core Components

**Backend (FastAPI)**:
- `main.py`: API endpoints orchestration
- `/api/v1/capture-visual`: GPT-4 Vision screenshot analysis
- `/api/v1/upload-metadata`: DAX Studio CSV processing
- `/api/v1/analyze-similarity`: Dashboard comparison engine
- `/api/v1/generate-report`: Multi-format report generation
- Authentication via Bearer token in Authorization header

**Frontend (Streamlit)**:
- `streamlit_app.py`: 4-step workflow interface
- Progressive dashboard with session state management
- Custom blue (#0C62FB) branded theme matching agent-bi-assistant-v2
- Interactive similarity matrix and consolidation recommendations

**Analysis Modules**:
- `analyzers/visual_analyzer.py`: GPT-4 Vision integration
- `analyzers/dax_analyzer.py`: DAX formula parsing and comparison
- `analyzers/similarity.py`: Multi-factor similarity algorithms
- `utils/report_generator.py`: JSON/Excel report generation

### Similarity Algorithm Components
- **Visual Similarity** (30%): Chart types, layout patterns, KPI cards
- **Measure Similarity** (40%): DAX formulas, function usage, complexity
- **Data Model Similarity** (20%): Tables, relationships, structure
- **Layout Similarity** (10%): Page organization, element positioning

### Key Dependencies
- **FastAPI + Uvicorn**: High-performance API framework
- **Streamlit + Plotly**: Interactive web UI with visualizations
- **OpenAI SDK**: GPT-4 Vision API integration
- **Pandas + OpenPyXL**: Data processing and Excel generation
- **Pillow + OpenCV**: Image processing
- **Pydantic**: Data validation and serialization

### Important Notes
- Extends agent-bi-assistant-v2 architectural patterns
- Requires OpenAI API key with GPT-4 Vision access
- Supports DAX Studio CSV exports for metadata
- Multi-page dashboard analysis capability
- Configurable similarity weights and thresholds
- In-memory storage (replace with database for production)
- Authentication required for all API endpoints
- Both services support hot reload during development

## File Processing

### Supported Formats
- **Images**: PNG, JPG, JPEG (max 10MB)
- **Metadata**: DAX Studio CSV exports
- **Output**: JSON reports, Excel workbooks

### DAX Studio Export Requirements

**Three CSV exports required for manual upload mode:**

1. **Measures Export:** `EVALUATE INFO.MEASURES()`
   - MeasureName
   - Expression (DAX formula)  
   - TableName
   - Description (optional)
   - FormatString (optional)

2. **Tables Export:** `EVALUATE INFO.TABLES()`
   - TableName
   - RowCount (optional)
   - TableType (optional)

3. **Relationships Export:** `EVALUATE INFO.RELATIONSHIPS()`
   - FromTable
   - FromColumn  
   - ToTable
   - ToColumn
   - RelationshipType (Many-to-One, One-to-Many, etc.)

## Configuration

### Environment Variables
```
OPENAI_API_KEY=sk-...           # Required for GPT-4 Vision
API_KEY=supersecrettoken123     # API authentication
GPT_MODEL=gpt-4-vision-preview  # Vision model
SIMILARITY_THRESHOLD_MERGE=0.85 # High similarity threshold
SIMILARITY_THRESHOLD_REVIEW=0.70 # Medium similarity threshold
MAX_FILE_SIZE_MB=10             # File upload limit

# Power BI API Integration (Optional - can use Mock Mode)
POWERBI_CLIENT_ID=12345678-1234-1234-1234-123456789abc    # Azure AD App Client ID
POWERBI_CLIENT_SECRET=your-client-secret                  # Azure AD App Secret  
POWERBI_TENANT_ID=abcdefgh-abcd-abcd-abcd-abcdefghijkl   # Azure AD Tenant ID
```

### Similarity Weights (Configurable)
Default weights in `analyzers/similarity.py`:
```python
{
    'measures': 0.4,     # DAX formulas and calculations
    'visuals': 0.3,      # Chart types and visualizations
    'data_model': 0.2,   # Tables and relationships
    'layout': 0.1        # Page structure
}
```

## Power BI API Integration

The application now supports direct integration with Power BI Service via REST APIs, eliminating the need for manual file uploads.

### Azure AD App Registration Setup

1. **Register Azure AD Application:**
   ```bash
   # Navigate to Azure AD > App registrations > New registration
   # Name: "PBI Dashboard Consolidation Tool"  
   # Redirect URI: Not required (daemon app)
   # API Permissions: Power BI Service (Datasets.ReadWrite.All, Reports.ReadWrite.All)
   ```

2. **Configure API Permissions:**
   - Add `Power BI Service` permissions:
     - `Dataset.ReadWrite.All` (Admin consent required)
     - `Report.ReadWrite.All` (Admin consent required)
     - `Workspace.ReadWrite.All` (Admin consent required)

3. **Create Client Secret:**
   ```bash
   # Azure AD > App registrations > Your app > Certificates & secrets
   # Create new client secret, copy the value immediately
   ```

### Power BI API Usage Modes

**1. Full API Mode (Production):**
```bash
# Set in .env file
POWERBI_CLIENT_ID=your-actual-client-id
POWERBI_CLIENT_SECRET=your-actual-secret  
POWERBI_TENANT_ID=your-tenant-id
```

**2. Mock Mode (Development/Testing):**
```python
# No credentials required - uses mock data
client = PowerBIAPIClient(mock_mode=True)
```

### Supported Operations

- **Workspace Discovery:** List all accessible Power BI workspaces
- **Report Enumeration:** Get reports within selected workspaces  
- **Dataset Analysis:** Extract measures, tables, relationships via DAX queries
- **Metadata Extraction:** Automated dashboard profiling without manual uploads
- **Batch Processing:** Analyze multiple reports simultaneously

### Data Source Selection

The Streamlit UI now provides two options:

1. **📤 Manual Upload:** Traditional screenshot + CSV workflow
2. **☁️ Power BI Service (REST API):** Direct cloud integration

When using API mode:
- Connect with Azure AD credentials or enable Mock Mode
- Browse and select workspaces
- Choose specific reports for analysis  
- Automated extraction of DAX metadata
- Real-time progress tracking

## API Authentication

All endpoints require Bearer token authentication:
```bash
curl -H "Authorization: Bearer supersecrettoken123" \
     http://localhost:8000/api/v1/dashboard-profiles
```

## Development Guidelines

### Adding New Similarity Metrics
1. Extend `SimilarityBreakdown` model in `models.py`
2. Add comparison method in `analyzers/similarity.py`
3. Update weight configuration in `SimilarityEngine.__init__`
4. Modify frontend to display new metric in `streamlit_app.py`

### Adding New File Types
1. Update `supported_formats` in `utils/file_handlers.py`
2. Add parsing logic in appropriate analyzer module
3. Extend `DashboardProfile` model if needed
4. Update frontend file upload component

### Extending Reports
1. Add new format in `utils/report_generator.py`
2. Create corresponding API endpoint in `main.py`
3. Add download option in `streamlit_app.py` step 4

## Testing

### Manual Testing
```bash
# Health check
curl http://localhost:8000/

# Upload test dashboard
curl -X POST "http://localhost:8000/api/v1/capture-visual?dashboard_id=test&dashboard_name=Test" \
  -H "Authorization: Bearer supersecrettoken123" \
  -F "file=@test_dashboard.png"
```

### Sample Data
Use `utils/file_handlers.py` `create_sample_data()` for testing without real files.

## Troubleshooting

### Common Issues
- **OpenAI API errors**: Check API key, rate limits, and model availability
- **File upload failures**: Verify file size limits and formats
- **Similarity analysis errors**: Ensure at least 2 complete dashboard profiles
- **Memory issues**: Process smaller batches or increase system resources

### Debug Mode
```bash
export DEBUG=true
uvicorn main:app --log-level debug
```

## Production Considerations

### Scalability Improvements Needed
- Replace in-memory storage with database (PostgreSQL recommended)
- Implement background job queue for large analyses (Celery/Redis)
- Add caching layer for repeated analyses (Redis)
- File storage service for uploaded images (S3/MinIO)
- Load balancing for multiple API instances

### Security Enhancements
- Rate limiting on API endpoints
- File content validation beyond size/format
- Audit logging for analysis activities
- Role-based access control for enterprise use

### Performance Optimizations
- Async/await for I/O operations
- Batch processing for multiple dashboard uploads
- Image optimization and compression
- Database indexing for similarity lookups

## Integration Notes

This tool is designed to integrate with the existing agent-bi-assistant-v2 ecosystem:
- Follows same API patterns and response formats
- Uses identical authentication mechanisms
- Shares UI design language and component structure
- Can be deployed alongside existing services
- Compatible with same deployment infrastructure

Any new updates or features should maintain consistency with the parent project's patterns and conventions.