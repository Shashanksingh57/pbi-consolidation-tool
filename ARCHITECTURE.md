# Power BI Dashboard Consolidation Tool - Architecture

## High-Level Architecture - Dual Mode System

### Mode 1: Local Batch Processing (Manual Upload)
```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│  Streamlit UI (Port 8501)                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │   Upload    │  │  Analysis   │  │   Results   │                      │
│  │ Interface   │  │ Interface   │  │  Display    │                      │
│  │(Screenshots)│  │             │  │             │                      │
│  │& CSV Files  │  │             │  │             │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            API LAYER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  FastAPI Backend (Port 8000)                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ /visual-analysis │  │ /metadata-upload │  │ /similarity-     │      │
│  │                  │  │                  │  │     analysis     │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Mode 2: Power BI API Integration (Cloud Connected)
```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│  Streamlit UI (Port 8501)                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │ Workspace   │  │  Report     │  │   Results   │                      │
│  │ Browser     │  │ Selection   │  │  Display    │                      │
│  │(PBI Service)│  │ & Analysis  │  │             │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            API LAYER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  FastAPI Backend (Port 8000)                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ /pbi-workspaces  │  │ /pbi-reports     │  │ /batch-extract   │      │
│  │ /pbi-datasets    │  │ /pbi-metadata    │  │ /auto-analysis   │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL INTEGRATION                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │ Power BI    │    │ Azure AD    │    │ REST API    │                  │
│  │ Service     │    │ Auth        │    │ Clients     │                  │
│  │ REST APIs   │    │ (OAuth2)    │    │ & Parsers   │                  │
│  └─────────────┘    └─────────────┘    └─────────────┘                  │
│        │                   │                   │                        │
│   Workspaces           Client ID          HTTP Requests                 │
│   Reports             Secret/Tenant       JSON Responses                │
│   Datasets            Bearer Tokens       Error Handling                │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PROCESSING LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │ PBI API     │    │  Metadata   │    │ Similarity  │                  │
│  │ Client      │    │  Processor  │    │  Analyzer   │                  │
│  │      │      │    │      │      │    │      │      │                  │
│  │ Workspace   │    │  DAX Query  │    │ Score Calc  │                  │
│  │ Discovery   │    │ Execution   │    │ & Grouping  │                  │
│  │ & Enumeration│   │ & Parsing   │    │             │                  │
│  └─────────────┘    └─────────────┘    └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA MODELS                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  Dashboard Profile (Unified):                                          │
│  ├── Visual Elements (extracted via DAX queries)                       │
│  ├── DAX Measures (live from dataset)                                  │
│  ├── Data Tables (schema from API)                                     │
│  └── Relationships (model from API)                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. **Frontend (Streamlit UI)**
```
streamlit_app.py
├── Dashboard Upload Section
│   ├── Screenshot Upload (Multiple Pages)
│   └── Metadata Upload (DAX Studio Exports)
├── Analysis Section
│   ├── Visual Analysis Trigger
│   └── Metadata Processing
├── Similarity Analysis Section
│   ├── Dashboard Comparison
│   └── Threshold Configuration
└── Results Section
    ├── Dashboard Profiles Display
    ├── Similarity Matrix
    └── Consolidation Recommendations
```

### 2. **Backend API (FastAPI)**
```
main.py
├── /visual-analysis
│   └── Process dashboard screenshots with GPT-4 Vision
├── /metadata-upload
│   └── Parse DAX Studio metadata exports
├── /similarity-analysis
│   └── Compare dashboard profiles
└── /consolidation-report
    └── Generate consolidation recommendations
```

### 3. **Analysis Modules**
```
analyzers/
├── visual_processor.py
│   ├── analyze_dashboard_screenshot()
│   ├── extract_visual_elements()
│   └── identify_kpi_cards()
├── metadata_processor.py
│   ├── parse_dax_measures()
│   ├── extract_data_model()
│   └── process_relationships()
└── similarity.py
    ├── HeuristicSimilarityEngine
    ├── calculate_visual_similarity()
    ├── calculate_measure_similarity()
    └── generate_consolidation_groups()
```

## Workflow

### Step 1A: Dashboard Profile Creation (Manual Mode)
```
User → Streamlit UI → FastAPI → Processing
 │        │             │          │
 │   Upload Files   Send Files  Analyze
 │        │             │          │
 │        ▼             ▼          ▼
 │   File Upload    API Endpoint  GPT-4 Vision
 │   Interface      /extract      DAX Parser
 │        │        -profile       Data Model
 │        ▼             │          │
 │   Progress        Profile      │
 └─── Display ◄─── Response ◄─────┘
```

### Step 1B: Dashboard Profile Creation (Power BI API Mode)
```
User → Streamlit UI → FastAPI → Power BI API → Processing
 │        │             │          │             │
 │   Select WSP     Authenticate  OAuth Token   Extract
 │   Pick Reports     │ Azure AD     │          │
 │        │             │          ▼             ▼
 │        ▼             ▼      REST Calls    DAX Queries
 │   Workspace      /pbi-auth   Workspaces   Live Data
 │   Browser        /pbi-       Reports      Measures
 │        │         reports     Datasets     Tables
 │        ▼             │          │          │
 │   Progress        Profile      │          │
 └─── Display ◄─── Response ◄─────┴──────────┘

Azure AD App Registration Required:
- Client ID, Secret, Tenant ID
- Power BI Service API Permissions
- Admin Consent for Organization
```

### Step 2: Similarity Analysis
```
Select Dashboards → Calculate Similarity → Generate Report

     User Input          Processing           Output
         │                   │                 │
    ┌─────────┐         ┌─────────┐      ┌─────────┐
    │Dashboard│   →     │Compare  │  →   │Matrix & │
    │Selection│         │Profiles │      │Groups   │
    └─────────┘         └─────────┘      └─────────┘
         │                   │                 │
    Pick 2+ Items      Visual + Measure    Recommendations
                      + Data Model Sim
```

### Step 3: Consolidation Logic
```
Similarity Score → Decision → Priority → Action

    0.85+ (High)  →  MERGE     →  Priority 1  →  Immediate
    0.70+ (Medium)→  REVIEW    →  Priority 2  →  Investigate  
    0.50+ (Low)   →  CONSIDER  →  Priority 3  →  Monitor
    <0.50         →  SEPARATE  →  Priority 4  →  Keep Apart
```

## Data Flow

### Input Processing
1. **Screenshots** → Base64 encoding → GPT-4 Vision API → Visual element extraction
2. **DAX Metadata** → JSON/XML parsing → Measure and model extraction
3. **User Input** → Streamlit forms → API requests

### Profile Generation
```
Dashboard Input
    ├── Visual Analysis
    │   ├── Chart Types
    │   ├── KPI Cards
    │   └── Filters
    └── Metadata Analysis
        ├── DAX Measures
        ├── Data Tables
        └── Relationships
            ↓
    Dashboard Profile (JSON)
```

### Similarity Calculation
```
Profile A + Profile B
    ├── Visual Similarity (30%)
    │   └── Jaccard similarity of visual types
    ├── Measure Similarity (40%)
    │   └── Fuzzy matching of DAX formulas
    └── Data Model Similarity (30%)
        └── Table and relationship comparison
            ↓
    Composite Similarity Score (0-1)
```

## Key Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | Streamlit | Interactive web UI |
| Backend | FastAPI | REST API services |
| AI Analysis | OpenAI GPT-4 Vision | Visual element extraction |
| Data Processing | Pandas | Data manipulation |
| Similarity | FuzzyWuzzy | String matching |
| Models | Pydantic | Data validation |
| Async | Uvicorn | ASGI server |

## Configuration

### Environment Variables (.env)

#### Base Configuration:
```
OPENAI_API_KEY=sk-...           # Required for GPT-4 Vision
API_KEY=supersecrettoken123     # API authentication
GPT_MODEL=gpt-4-vision-preview  # Vision model
```

#### Mode 1: Local Batch Processing
```
API_BASE_URL=http://localhost:8000
# No additional API credentials required
```

#### Mode 2: Power BI API Integration
```
# Azure AD App Registration
POWERBI_CLIENT_ID=12345678-1234-1234-1234-123456789abc
POWERBI_CLIENT_SECRET=your-client-secret-value
POWERBI_TENANT_ID=abcdefgh-abcd-abcd-abcd-abcdefghijkl

# API Endpoints (automatically configured)
POWERBI_BASE_URL=https://api.powerbi.com/v1.0/myorg
POWERBI_AUTH_URL=https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token

# Mock Mode for Development/Testing
POWERBI_MOCK_MODE=true  # Set to false for production
```

### Ports
- **Streamlit UI**: 8501
- **FastAPI Backend**: 8000

## Deployment Architecture

```
Current (Local Development):
┌─────────────────────────────────┐
│      Developer Machine         │
│  ┌─────────────────────────────┐│
│  │ Streamlit UI (Port 8501)    ││
│  └─────────────────────────────┘│
│  ┌─────────────────────────────┐│
│  │ FastAPI Backend (Port 8000) ││
│  └─────────────────────────────┘│
│  ┌─────────────────────────────┐│
│  │ Session Storage (Memory)    ││
│  └─────────────────────────────┘│
└─────────────────────────────────┘

Future (Production):
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Load Balancer│→ │ Web Servers  │→ │   Database   │
│              │  │ (Multiple)   │  │ (Persistent) │
└──────────────┘  └──────────────┘  └──────────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │ Cache Layer  │
                  │ (Redis)      │
                  └──────────────┘
```

## Security Considerations

1. **API Key Management**: OpenAI API keys stored in environment variables
2. **File Upload Validation**: Size limits and format validation
3. **Session Isolation**: Separate session states for concurrent users
4. **Data Privacy**: No persistent storage of uploaded dashboard data

## Performance Optimizations

1. **Caching**: Dashboard profiles cached in session state
2. **Batch Processing**: Multiple screenshots processed in parallel
3. **Lazy Loading**: Metadata processed on-demand
4. **Similarity Matrix**: Pre-computed for dashboard pairs

## Future Enhancements

1. **Database Integration**: Persistent storage of dashboard profiles
2. **Authentication**: User management and access control
3. **Export Formats**: PDF, Excel report generation
4. **Advanced Analytics**: ML-based pattern recognition
5. **Version Control**: Track dashboard profile changes over time