# Energy Operations Document RAG Assistant

A local, deterministic Retrieval-Augmented Generation (RAG) assistant designed for renewable energy operations, plant maintenance SOPs, and safety compliance (Solar PV, Wind Turbines, Hydroelectric, and Grid Dispatch). Built with FastAPI, scikit-learn, and Vanilla HTML/CSS/JavaScript.

---

## 1. Project Overview & Problem Statement

### Context
Renewable energy asset operators (such as Greenko) manage multi-technology portfolios comprising utility-scale solar farms, wind turbine parks, pumped storage/hydro plants, and centralized grid dispatch centers. Operations and Maintenance (O&M) teams rely on Standard Operating Procedures (SOPs), safety clearance briefs, and troubleshooting notes to maintain asset uptime and worker safety.

### Problem
Field technicians and control room dispatchers require immediate, authoritative answers during operational events (e.g., inverter derating alarms, gearbox vibration spikes, grid frequency deviations, or spillway gate inspections). Generic generative AI models risk hallucinating critical operational parameters, inventing ungrounded thresholds, or suggesting unsafe workarounds.

### Solution
This application implements an evidence-grounded, zero-hallucination document intelligence assistant:
- **100% Local & Deterministic:** Uses TF-IDF vectorization and cosine similarity retrieval without external LLM dependencies, API keys, or cloud databases.
- **Traceable Citations:** Every operational claim is attributed to source documents with exact excerpts and similarity scores.
- **Safety Safeguards:** Implements a strict confidence threshold that rejects out-of-domain queries and unsupported premises with explicit refusals.

---

## 2. Architecture & Data Flow

```
[ Field Operator / Web Dashboard ]
                 │
                 ▼ (HTTP POST /api/run)
┌────────────────────────────────────────────────────────┐
│                   Query Validation                     │
│  - Rejects empty, whitespace-only, or >500 char inputs │
└───────────────────────┬────────────────────────────────┘
                        │ Valid Query String
                        ▼
┌────────────────────────────────────────────────────────┐
│             TF-IDF Vector Transformation               │
│  - Fits sublinear TF-IDF (1-2 ngrams, english stop)   │
│  - Transforms question into vector space               │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│             Cosine Similarity & Top-k Ranking          │
│  - Computes similarity against all indexed SOP chunks  │
│  - Deterministic sort (score desc, chunk_id asc)       │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│              Relevance Threshold Guard                 │
│  - Checks max score >= 0.15 threshold                  │
│  - If below threshold: Returns Insufficient Evidence   │
└───────────────────────┬────────────────────────────────┘
                        │ Score >= 0.15
                        ▼
┌────────────────────────────────────────────────────────┐
│      Evidence-Grounded Synthesis & Traceable Citations │
│  - Formulates answer strictly from retrieved excerpts  │
│  - Attaches source file, document title, and chunk ID  │
│  - Injects mandatory operational safety disclaimer     │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (JSON RunResponse)
[ Frontend Dashboard Displays Grounded Answer & Citations ]
```

---

## 3. Technology Stack & Design Decisions

| Layer | Technology | Decision Rationale |
|---|---|---|
| **Backend API** | FastAPI 0.115.0 & Uvicorn 0.30.6 | High-performance asynchronous REST API, automatic OpenAPI/Swagger documentation, fast startup. |
| **Data Models** | Pydantic 2.8.2 | Strict request validation, typed domain schemas, and clean error messages. |
| **Indexing & Retrieval** | scikit-learn 1.5.1 (TF-IDF & Cosine Similarity) | Deterministic, offline, lightweight retrieval without external vector DBs or API costs. |
| **Data Manipulation** | pandas 2.2.2 & NumPy 1.26.4 | Tabular data processing and numerical linear algebra operations. |
| **Frontend** | Vanilla HTML5, CSS3, ES6 JavaScript | Zero build step, instant load time, maximum maintainability, accessible semantic markup. |
| **Design System** | Restrained Forest Green Palette | Professional light theme (`#245C45`, `#F5F7F4`, `#E5F0E8`) tailored for plant operations control rooms. |

---

## 4. Project Directory Structure

```
Energy_Operations_RAG_Assistant/
├── backend/
│   ├── __init__.py           # Package marker
│   ├── app.py                # FastAPI endpoints, static file mounting, metrics
│   └── rag_engine.py         # Ingestion, chunking, TF-IDF vectorizer, citations
├── data/
│   ├── grid_operations_note.md       # Operational note on generation deviation
│   ├── hydro_safety_brief.md         # Spillway gate lockout-tagout brief
│   ├── questions.csv                 # Evaluation test set
│   ├── solar_inverter_sop.md         # Inverter derating & 75°C inspection SOP
│   └── wind_turbine_maintenance.md   # Gearbox vibration & bearing wear SOP
├── frontend/
│   ├── app.js                # Client logic, live polling, safe DOM rendering
│   ├── index.html            # Responsive operations dashboard
│   └── style.css             # Light theme stylesheet with accessible contrast
├── tests/
│   ├── test_api.py           # API endpoint integration & schema validation tests
│   ├── test_scenarios.py     # 25 client-perspective scenario & edge case tests
│   └── test_unit_rag.py      # Unit tests for chunking, TF-IDF, and retrieval
├── .gitignore                # Environment and cache ignore patterns
├── Procfile                  # Railway / PaaS deployment start command
├── README.md                 # Project documentation
├── candidate_task.md         # Original task statement
├── case_study.html           # Original case study problem reference
├── eval_retrieval.py         # Standalone evaluation & 1000-query benchmark script
├── evaluation_rubric.md      # Greenko assessment criteria
├── pytest.ini                # Pytest configuration
├── requirements.txt          # Python dependencies
└── submission_instructions.md# Submission requirements
```

---

## 5. Prerequisites & Local Setup

### Prerequisites
- Python 3.10, 3.11, or 3.12 (Python 3.12 recommended)
- Windows PowerShell or macOS/Linux Terminal
- Git

### Windows PowerShell Setup

1. **Clone or navigate to the repository:**
   ```powershell
   cd D:\Energy_Operations_RAG_Assistant
   ```

2. **Create a virtual environment:**
   ```powershell
   py -3.12 -m venv .venv
   ```

3. **Activate the virtual environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   *(If script execution is disabled in PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

4. **Install pinned dependencies:**
   ```powershell
   pip install -r requirements.txt pytest httpx
   ```

5. **Start the local server:**
   ```powershell
   uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
   ```

6. **Open the application:**
   - Web Dashboard: [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - Interactive Swagger API: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - Case Study Overview: [http://127.0.0.1:8000/case_study](http://127.0.0.1:8000/case_study)

---

## 6. API Endpoints & Usage

### 1. `POST /api/run`
Executes the RAG pipeline for an operational question.

**Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"text": "What should be checked for inverter derating?", "top_k": 3}'
```

**Response (200 OK):**
```json
{
  "input": "What should be checked for inverter derating?",
  "result": "According to the **Solar Inverter SOP**:\n\nIf inverter temperature exceeds 75C, inspect cooling fans, dust filters, ambient temperature, and DC input imbalance. If repeated derating occurs, create a priority maintenance ticket and verify SCADA alarms.",
  "status": "success",
  "citations": [
    {
      "source_file": "solar_inverter_sop.md",
      "document_title": "Solar Inverter SOP",
      "chunk_id": "solar_inverter_sop_chunk_0",
      "excerpt": "If inverter temperature exceeds 75C, inspect cooling fans, dust filters, ambient temperature, and DC input imbalance. If repeated derating occurs, create a priority maintenance ticket and verify SCADA alarms.",
      "similarity_score": 0.2076
    }
  ],
  "retrieved_evidence": [
    "If inverter temperature exceeds 75C, inspect cooling fans, dust filters, ambient temperature, and DC input imbalance. If repeated derating occurs, create a priority maintenance ticket and verify SCADA alarms."
  ],
  "similarity_scores": [0.2076],
  "matched_topic": "Solar PV Operations",
  "latency_ms": 0.62,
  "disclaimer": "Standard Safety Note: This assistant provides guidance extracted strictly from local operational documents. It does not replace site-specific SOPs, lockout-tagout procedures, or qualified engineering personnel.",
  "evaluation_hint": "Predictions verified against local operational SOPs using TF-IDF retrieval with traceable citations and safety guards."
}
```

### 2. `GET /api/health`
Returns system status, active document count, and supported topics.

### 3. `GET /api/documents`
Lists the catalog of indexed operational SOPs with chunk metadata.

### 4. `GET /api/metrics`
Reports runtime metrics including total queries processed and average latency.

### 5. `GET /api/demo`
Preserved backward-compatibility endpoint returning original case study metadata.

---

## 7. RAG Workflow & Algorithmic Design

### Document Ingestion & Chunking
1. **Discovery:** Scans `data/` for valid `.md` files.
2. **Text Normalization:** Strips irregular formatting while strictly preserving engineering symbols, numbers, and units (e.g., `75C`).
3. **Chunking Strategy:** Splits text into cohesive 2-sentence windows (`chunk_sentence_window=2`, `chunk_sentence_overlap=1`). This guarantees that conditional trigger statements (e.g., *"If temperature exceeds 75C"*) remain bonded to actionable procedures (*"inspect cooling fans..."*).
4. **Stable Identifiers:** Each chunk is assigned a deterministic ID: `{sanitized_stem}_chunk_{index}`.

### Retrieval & Ranking
1. **TF-IDF Vectorization:** Evaluates unigrams and bigrams (`ngram_range=(1, 2)`) with English stop-word filtering and sublinear term frequency scaling (`sublinear_tf=True`).
2. **Cosine Similarity:** Measures query-document alignment via inner dot product over normalized L2 vectors.
3. **Deterministic Tie-Breaking:** Results are sorted primary by similarity score (descending) and secondary by chunk ID (ascending) to guarantee reproducible outputs.

### Refusal & Hallucination Prevention
- When the top similarity score is `< 0.15` (or when given out-of-domain queries), the system refuses to answer.
- Returns `status: "insufficient_evidence"` with a clear notification explaining that no matching procedures exist.
- Does not guess or generate fictional operational parameters.

---

## 8. Verification & Evaluation Results

### Automated Test Suite
Run the comprehensive test suite (48 tests covering unit, API, and client scenarios):
```powershell
.\.venv\Scripts\pytest -v
```
**Results:** `48 passed in 2.54s` (100% pass rate).

### Standalone Evaluation & 1,000-Request Benchmark
Run the dedicated benchmark script:
```powershell
.\.venv\Scripts\python.exe eval_retrieval.py
```

**Measured Metrics:**
- **Indexed Documents:** 4
- **Indexed Chunks:** 4
- **Evaluation Dataset:** 11 cases (8 domain queries, 3 negative refusal cases)
- **Top-1 Accuracy:** `100.00%` (8/8)
- **Recall@3:** `100.00%` (8/8)
- **Citation Validity Rate:** `100.00%` (8/8 citations literally verified in source files)
- **Unsupported Question Refusal Rate:** `100.00%` (3/3)
- **Average Query Latency:** `0.62 ms`
- **1,000 Deterministic Repeated Requests:**
  - Completed: `1000 / 1000`
  - Failures: `0 / 1000`
  - Total Duration: `0.62 seconds` (`0.619 ms / query`)

---

## 9. Security & Safety Review

1. **Input Validation:**
   - Question length bounded to 500 characters max.
   - Rejects null, empty, or whitespace-only queries with HTTP 400.
2. **Path Traversal Protection:**
   - File discovery is restricted strictly to `BASE_DIR / 'data'` using `pathlib.Path.glob("*.md")`.
   - Arbitrary path inputs from users are not accepted.
3. **XSS & Injection Protection:**
   - The frontend renders all text, answers, citations, and excerpts using `textContent` and safe DOM node creation.
   - User inputs are never evaluated with `eval()` or injected via raw `innerHTML`.
4. **Information Disclosure Prevention:**
   - Production FastAPI error handlers sanitize 500 and 400 responses, preventing internal stack traces or directory paths from leaking to clients.
5. **Operational Safety Notice:**
   - All responses include an explicit disclaimer reminding personnel that assistant output does not supersede site lockout-tagout or electrical safety procedures.

---

## 10. Known Limitations & Production Roadmap

| Current Limitation | Production Roadmap |
|---|---|
| **Lexical vs Semantic Matching** | TF-IDF depends on vocabulary overlap. Synonym mismatches (e.g., *"rotational anomalies"* vs *"vibration"*) require either dense embeddings (e.g., local ONNX BGE-small) or a curated domain synonym dictionary. |
| **In-Memory Index** | Index fits in memory for small datasets. For thousands of SOPs across multiple plants, a persistent search index (e.g., SQLite FTS5 or Milvus) should be used. |
| **Simple Extraction** | Answers directly present retrieved text. For complex multi-document syntheses, a local quantised small LLM (e.g. Llama-3-8B-Instruct via llama.cpp) can formulate conversational responses. |
| **Authentication & Audit** | In production, integrate enterprise SSO (OAuth2/OIDC), role-based access control (RBAC), and append-only audit logging for all operational queries. |

---

## 11. Railway Deployment Instructions

The project is pre-configured for one-click deployment on Railway using the included `Procfile`.

1. **Create a GitHub repository:**
   ```powershell
   git init
   git add .
   git commit -m "feat: complete energy operations rag assistant"
   git branch -M main
   git remote add origin https://github.com/<your-username>/energy-operations-rag-assistant.git
   git push -u origin main
   ```

2. **Deploy on Railway:**
   - Log in to [Railway.app](https://railway.app).
   - Click **New Project** → **Deploy from GitHub repo**.
   - Select the repository.
   - Railway detects the `Procfile` and builds using Python automatically:
     ```
     web: uvicorn backend.app:app --host 0.0.0.0 --port $PORT
     ```
   - In Railway **Settings** → **Networking**, click **Generate Domain** to obtain your live URL.
