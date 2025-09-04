# Power BI Dashboard Consolidation Tool

An AI-powered tool that identifies and consolidates duplicate Power BI dashboards using GPT-4 Vision and advanced similarity analysis.

## 🎯 Overview

This tool helps organizations reduce dashboard sprawl by:
- Analyzing dashboard screenshots with GPT-4 Vision API
- Processing DAX Studio metadata exports  
- Calculating multi-dimensional similarity scores
- Generating actionable consolidation recommendations
- Producing detailed reports for decision-making

Built as an extension of the agent-bi-assistant-v2 architecture, following the same patterns for FastAPI backend and Streamlit frontend.

## 🏗️ Architecture

### Backend (FastAPI)
- **Visual Analysis**: GPT-4 Vision API integration for screenshot analysis
- **Metadata Processing**: DAX Studio CSV parsing and structure analysis
- **Similarity Engine**: Multi-factor dashboard comparison algorithm
- **Report Generation**: JSON and Excel output formats

### Frontend (Streamlit) 
- **4-Step Workflow**: Inventory → Analysis → Recommendations → Reports
- **Blue Theme**: Consistent with agent-bi-assistant-v2 branding (#0C62FB)
- **Progress Tracking**: Visual indicators and session state management
- **Interactive Results**: Similarity matrix visualization and group management

### Analysis Components
- **Visual Similarity** (30%): Chart types, layout, KPI cards
- **Measure Similarity** (40%): DAX formulas, function usage, naming
- **Data Model Similarity** (20%): Tables, relationships, structure
- **Layout Similarity** (10%): Page organization, element positioning

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key with GPT-4 Vision access
- DAX Studio (for metadata exports)

### Installation

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd pbi-consolidation-tool
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # OR
   venv\\Scripts\\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Environment configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

3. **Run the application**:
   ```bash
   # Terminal 1 - Backend API
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   
   # Terminal 2 - Frontend UI  
   streamlit run streamlit_app.py --server.port 8501
   ```

4. **Access the tool**:
   - Frontend: http://localhost:8501
   - API docs: http://localhost:8000/docs

## 📋 Usage Workflow

### Step 1: Dashboard Inventory
1. **Upload Screenshots**: PNG/JPG files of dashboard pages
2. **Provide Metadata**: DAX Studio CSV exports containing:
   - Measures and DAX formulas
   - Table structures
   - Relationships
   - Data sources

### Step 2: Similarity Analysis  
1. **Configure Weights**: Adjust importance of different similarity factors
2. **Run Analysis**: AI-powered comparison of all dashboard pairs
3. **Review Matrix**: Interactive similarity scores and breakdowns

### Step 3: Consolidation Recommendations
1. **Review Groups**: Automatically identified consolidation opportunities
2. **Action Planning**: Merge, consolidate, or review recommendations
3. **Priority Assessment**: Effort estimates and priority rankings

### Step 4: Report Generation
1. **JSON Export**: Machine-readable analysis data
2. **Excel Report**: Multi-worksheet business report
3. **Action Items**: Prioritized consolidation tasks

## 🔧 API Endpoints

### Dashboard Processing
- `POST /api/v1/capture-visual` - Process dashboard screenshots
- `POST /api/v1/upload-metadata` - Upload DAX Studio exports  
- `GET /api/v1/dashboard-profiles` - View processed dashboards

### Analysis & Results
- `POST /api/v1/analyze-similarity` - Run similarity analysis
- `GET /api/v1/similarity-matrix` - Get comparison results
- `POST /api/v1/generate-report` - Generate consolidated reports

### Management
- `DELETE /api/v1/reset` - Clear all analysis data
- `GET /` - Health check

## 🎛️ Configuration

### Similarity Weights (Configurable)
```json
{
  "measures": 0.4,     // DAX formulas and calculations
  "visuals": 0.3,      // Chart types and visualizations  
  "data_model": 0.2,   // Tables and relationships
  "layout": 0.1        // Page structure and positioning
}
```

### Consolidation Thresholds
- **Merge** (≥85%): Nearly identical dashboards
- **Review** (70-84%): Significant overlap, manual review needed  
- **Ignore** (<70%): Keep separate

### File Limits
- Max image size: 10MB
- Supported formats: PNG, JPG, JPEG, CSV
- Multiple pages per dashboard supported

## 📊 Sample Analysis Output

### Similarity Breakdown
```json
{
  "dashboard1_name": "Sales Performance Dashboard",
  "dashboard2_name": "Regional Sales Report", 
  "total_score": 0.87,
  "breakdown": {
    "measures_score": 0.92,    // High DAX similarity
    "visuals_score": 0.85,     // Similar chart types
    "data_model_score": 0.88,  // Shared tables
    "layout_score": 0.74       // Different layouts
  }
}
```

### Consolidation Recommendation
```json
{
  "action": "merge",
  "reason": "High similarity (87%) indicates nearly identical dashboards",
  "effort_estimate": "medium",
  "priority": 5
}
```

## 🔍 Technical Details

### GPT-4 Vision Analysis
The visual analyzer sends dashboard screenshots to GPT-4 Vision with a structured prompt to extract:
- Visual element types and positions
- KPI cards and metrics
- Filter configurations  
- Layout patterns and structure

### DAX Formula Comparison
The similarity engine uses multiple techniques:
- **Exact matching**: Identical formulas
- **Function analysis**: DAX functions used
- **Fuzzy matching**: Similar structure with variations
- **Complexity scoring**: Nested functions and logic depth

### Similarity Algorithm
Multi-dimensional comparison combining:
1. **Semantic similarity**: Meaning and purpose
2. **Structural similarity**: Organization and relationships  
3. **Visual similarity**: Presentation and layout
4. **Technical similarity**: Implementation details

## 🧪 Testing

### Sample Data Generation
The tool includes sample data generators for testing:
```bash
python -c "from utils.file_handlers import FileHandler; print(FileHandler().create_sample_data())"
```

### API Testing
```bash
# Health check
curl http://localhost:8000/

# Test with sample dashboard
curl -X POST "http://localhost:8000/api/v1/capture-visual?dashboard_id=test&dashboard_name=Test" \
  -H "Authorization: Bearer supersecrettoken123" \
  -F "file=@sample_dashboard.png"
```

## 🎨 UI Customization

The Streamlit frontend follows agent-bi-assistant-v2 design patterns:
- **Brand Blue**: #0C62FB primary color
- **Step Cards**: Progressive workflow visualization  
- **Progress Indicators**: Clear advancement tracking
- **Responsive Layout**: Multi-column layouts for efficiency

Custom CSS classes:
- `.main-header`: Application branding
- `.step-card`: Workflow step containers
- `.stat-card`: Metric displays
- `.similarity-high/medium/low`: Color-coded results

## 🔒 Security & Authentication

- **API Key Authentication**: Bearer token required for all endpoints
- **File Validation**: Size limits and format checking
- **Input Sanitization**: Prevents malicious uploads
- **Rate Limiting**: Prevents API abuse (recommended for production)

## 📈 Performance Considerations

### Optimization Strategies
- **Batch Processing**: Multiple screenshots per request
- **Caching**: Repeated analysis results
- **Async Processing**: Non-blocking API operations
- **Memory Management**: Large file handling

### Scalability
- **Database Integration**: Replace in-memory storage for production
- **Queue System**: Background processing for large analyses
- **Load Balancing**: Multiple API instances
- **CDN Integration**: Asset delivery optimization

## 🛠️ Development

### Project Structure
```
pbi-consolidation-tool/
├── main.py                     # FastAPI application
├── streamlit_app.py            # Streamlit frontend
├── models.py                   # Pydantic data models
├── analyzers/
│   ├── visual_analyzer.py      # GPT-4 Vision integration
│   ├── dax_analyzer.py         # DAX processing
│   └── similarity.py           # Comparison algorithms
├── utils/
│   ├── report_generator.py     # Output formatting
│   └── file_handlers.py        # File processing
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── README.md                   # Documentation
```

### Adding New Features
1. **Extend Models**: Add new Pydantic classes in `models.py`
2. **Create Analyzers**: New analysis modules in `analyzers/`
3. **Add Endpoints**: FastAPI routes in `main.py`
4. **Update UI**: Streamlit components in `streamlit_app.py`

## 📝 License

This project extends agent-bi-assistant-v2 and follows the same licensing terms.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-analysis`
3. Commit changes: `git commit -am 'Add new similarity metric'`
4. Push branch: `git push origin feature/new-analysis`
5. Submit pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section below
2. Review API documentation at `/docs`
3. Submit issues via the project repository

## 🔧 Troubleshooting

### Common Issues

**OpenAI API Errors**:
- Verify API key is valid and has GPT-4 Vision access
- Check rate limits and billing status
- Ensure proper network connectivity

**File Upload Failures**:  
- Confirm file sizes under 10MB limit
- Verify supported formats (PNG, JPG, CSV)
- Check file permissions and accessibility

**Analysis Errors**:
- Validate DAX Studio CSV format
- Ensure at least 2 complete dashboards
- Check API authentication tokens

**Performance Issues**:
- Reduce image file sizes
- Process fewer dashboards per batch  
- Increase API timeout settings

### Debug Mode
Enable debug logging:
```bash
export DEBUG=true
uvicorn main:app --log-level debug
```

---

Built with ❤️ following agent-bi-assistant-v2 architectural patterns and design principles.