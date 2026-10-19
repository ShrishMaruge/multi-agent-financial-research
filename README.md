# Multi-Agent Financial Research System

A full-stack AI-powered financial research platform that helps finance students, MBA candidates, and early-career analysts understand annual reports, 10-K filings, and company financial documents faster.

The system uses specialized AI agents to parse financial reports, extract metrics, detect risks, compare companies, answer research questions with source citations, and generate analyst-style PDF reports.

---

## Problem Statement

Financial reports are long, complex, and time-consuming to analyse manually. Extracting key financial metrics, identifying business risks, comparing companies, and locating supporting evidence requires financial knowledge and significant effort.

This project solves that problem by building a multi-agent financial research workflow. Users upload annual reports, and the system automatically processes the document through specialized agents. Every insight is grounded in the uploaded source document and includes page-level citations where applicable.

---

## Key Features

- Upload and validate company annual reports in PDF format
- Reject unrelated or invalid financial documents
- Create and manage named research sessions
- Extract financial metrics such as revenue, net income, cash, debt, assets, liabilities, margins, and ratios
- Detect financial red flags such as rising debt, liquidity risk, falling margins, auditor concerns, losses, and unusual patterns
- Display red-flag evidence, severity, source page, and confidence information
- Compare selected company reports side-by-side
- Ask research questions in a conversational interface
- Generate source-grounded answers with citations from uploaded reports
- Generate analyst-style PDF reports
- View uploaded annual reports directly in the application
- Store document chunks in a vector database for retrieval-based research

---

## Multi-Agent Architecture

```text
User Uploads Annual Report
            |
            v
     Document Agent
            |
            v
    Extraction Agent
            |
            v
     Red Flag Agent
            |
            v
  Vector Database / Indexed Chunks
            |
            +------------------------+
            |                        |
            v                        v
     Research Agent          Comparison Agent
            |                        |
            +-----------+------------+
                        |
                        v
                  Report Agent
                        |
                        v
             Analyst-Style PDF Report
```

---

## Agents

### 1. Document Agent

Responsible for:

- Validating uploaded PDF files
- Checking whether the document appears to be an annual report or financial filing
- Extracting text page by page using PyMuPDF
- Splitting report text into smaller chunks
- Preparing chunks for semantic search
- Indexing document chunks in ChromaDB

### 2. Extraction Agent

Responsible for:

- Extracting key financial values from report content
- Identifying metrics such as revenue, net income, cash, debt, assets, liabilities, and operating income
- Detecting fiscal year and company information where available
- Storing extracted values with source pages and evidence text
- Calculating or presenting relevant financial ratios when data is available

### 3. Red Flag Agent

Responsible for:

- Detecting financial and accounting risk indicators
- Identifying high debt or rising debt signals
- Detecting liquidity concerns
- Flagging loss-making performance and declining margins
- Identifying auditor qualifications or material weakness references
- Detecting unusual financial statements or warning language
- Returning severity, confidence, source evidence, and source page

### 4. Comparison Agent

Responsible for:

- Comparing selected reports from the same research session
- Building side-by-side financial metric comparisons
- Supporting peer benchmarking
- Highlighting relative differences between companies

### 5. Research Agent

Responsible for:

- Handling multi-part financial questions
- Retrieving relevant report chunks from indexed documents
- Generating source-grounded responses
- Showing evidence and page-level citations
- Preventing unsupported answers through citation validation and fallback responses

### 6. Report Agent

Responsible for:

- Creating a structured analyst-style PDF report
- Generating an executive summary
- Presenting key financial metrics
- Including red-flag findings and risk review
- Producing a downloadable PDF output

---

## Technology Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- PyMuPDF
- ChromaDB
- ReportLab
- OpenAI-compatible optional LLM integration
- Ollama-compatible optional local LLM integration

### Frontend

- React
- Vite
- CSS

### Testing

- Pytest

---

## Project Structure

```text
multi-agent-financial-research/
├── LICENSE
├── README.md
├── .gitignore
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── migrate_red_flag_schema.py
│   ├── tests/
│   │   ├── test_red_flag_agent.py
│   │   ├── test_report_agent.py
│   │   └── test_research_agent.py
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       ├── agents/
│       │   ├── document_agent.py
│       │   ├── extraction_agent.py
│       │   ├── red_flag_agent.py
│       │   ├── comparison_agent.py
│       │   ├── research_agent.py
│       │   └── report_agent.py
│       ├── api/
│       │   ├── sessions.py
│       │   ├── documents.py
│       │   └── analysis.py
│       ├── rag/
│       │   └── vector_store.py
│       ├── services/
│       │   └── document_service.py
│       └── utils/
│           └── pdf_report.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       └── styles.css
└── data/
    ├── uploads/
    └── chroma/
```

---

## Installation

### Prerequisites

Install:

- Python 3.10 or later
- Node.js 18 or later
- npm
- Git

---

## Backend Setup

Open a terminal in the project folder:

```powershell
cd C:\Users\shash\OneDrive\Desktop\multi-agent-financial-research\backend
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` folder:

```text
APP_NAME=Multi Agent Financial Research System
DATABASE_URL=sqlite:///./financial_research.db
UPLOAD_DIR=../data/uploads
CHROMA_DIR=../data/chroma
MAX_FILE_SIZE_MB=30

# Optional LLM configuration
RESEARCH_PROVIDER=fallback
OPENAI_API_KEY=
LLM_MODEL=
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=
```

> The application works with the fallback research mode when no external LLM API key is configured. Add an OpenAI or Ollama configuration only if you want LLM-assisted responses.

Run the backend:

```powershell
uvicorn app.main:app --reload
```

Backend API runs at:

```text
http://127.0.0.1:8000
```

API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

---

## Frontend Setup

Open another terminal:

```powershell
cd C:\Users\shash\OneDrive\Desktop\multi-agent-financial-research\frontend
```

Install frontend dependencies:

```powershell
npm install
```

Start the frontend:

```powershell
npm run dev
```

Open the URL displayed by Vite, usually:

```text
http://127.0.0.1:5173
```

---

## How to Use the Application

1. Start the backend server.
2. Start the frontend server.
3. Open the frontend URL in a browser.
4. Create a new research session.
5. Upload a company annual report or 10-K PDF.
6. Wait for document processing to finish.
7. View extracted financial metrics.
8. Review Red Flag Agent findings.
9. Select two or more completed reports to compare them.
10. Ask research questions in the Research Agent chat interface.
11. Download the generated PDF report.

---

## Processing Workflow

When a report is uploaded, the system uses the following sequence:

```text
1. PDF upload validation
2. Annual-report relevance validation
3. Text extraction from PDF pages
4. Chunk creation
5. Vector database indexing
6. Financial metric extraction
7. Red-flag scanning
8. Database storage
9. Mark document as completed
```

If processing fails, the document status is marked as `failed` and the error is stored for troubleshooting.

---

## Source Grounding and Hallucination Prevention

The system is designed to avoid unsupported financial claims.

- Research responses use retrieved document chunks.
- Each response includes source references.
- Citations are validated against retrieved evidence.
- Unsupported or invalid citations trigger a safe fallback response.
- Red flags include supporting evidence and source pages.
- Financial metrics are stored with source context where available.

This ensures that generated output remains tied to the uploaded financial documents.

---

## Testing

Run backend tests:

```powershell
cd backend
pytest
```

The project includes tests for:

- Red Flag Agent detection logic
- Report Agent generation
- Research Agent multi-part query handling
- Citation validation
- Safe fallback handling for invalid or missing citations

---

## API Overview

| Endpoint | Purpose |
|---|---|
| `POST /api/sessions` | Create a research session |
| `GET /api/sessions` | List research sessions |
| `POST /api/documents/upload` | Upload a financial report |
| `GET /api/documents/session/{session_id}` | List session documents |
| `GET /api/documents/{document_id}/metrics` | Get extracted metrics |
| `GET /api/documents/{document_id}/red-flags` | Get red-flag findings |
| `GET /api/documents/{document_id}/file` | View uploaded PDF |
| `POST /api/analysis/research` | Ask research questions |
| `POST /api/analysis/comparison/documents` | Compare selected reports |
| `GET /api/analysis/report/{document_id}` | Get report data |
| `GET /api/analysis/report/{document_id}/pdf` | Download PDF report |

---

## Current Limitations

- Financial extraction quality depends on PDF text quality and report formatting.
- Scanned PDFs may require OCR support in a future version.
- Some metrics may not be available if they are not clearly stated in the report.
- Comparison quality depends on consistent metric extraction across reports.
- The current Report Agent provides executive summary, key financials, and red-flag content. Company comparison and outlook sections can be extended further in future releases.
- This tool supports academic analysis and should not be treated as professional investment advice.

---

## Future Enhancements

- Add OCR for image-based or scanned annual reports
- Add stronger table extraction from financial statements
- Add charts and financial trend visualizations
- Add industry and sector benchmark data
- Add multi-year trend analysis
- Expand Report Agent with Company Comparison and Outlook sections
- Add user authentication and role-based access
- Add cloud storage and enterprise deployment support
- Add agent performance analytics and evaluation dashboards
- Add background task queues for large document processing

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Author

**Shash Maruge**

GitHub: [ShrishMaruge](https://github.com/ShrishMaruge)

---

## Disclaimer

This project is developed for educational and academic purposes. It does not provide financial, legal, accounting, or investment advice. Users should verify all information against original company filings before making decisions.
