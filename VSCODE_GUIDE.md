# Developer Guide: Running in VS Code & Render Continuous Deployment

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11.9-3776AB.svg)](https://www.python.org/)
[![VS Code](https://img.shields.io/badge/IDE-VS%20Code%20F5%20Ready-007ACC.svg)](https://code.visualstudio.com/)
[![Render](https://img.shields.io/badge/Cloud-Render%20Auto--Deploy-46E3B7.svg)](https://render.com/)
[![Tests](https://img.shields.io/badge/pytest-48%20passed-brightgreen.svg)](https://pytest.org/)

This guide provides an end-to-end, visual walkthrough for running the **Energy Operations Document RAG Assistant** inside Visual Studio Code with one-click F5 debugging, interactive API documentation, automated health monitoring, and GitHub-to-Render continuous deployment.

---

## 1. Quickstart (30 Seconds to Launch)

```
┌────────────────────────────────────────────────────────┐
│ 1. Open Folder in VS Code                              │
│ 2. Create Virtual Environment (.venv)                  │
│ 3. Press F5 ➔ Assistant Server Launches Instantly!     │
└────────────────────────────────────────────────────────┘
```

### Step 1: Open Folder in VS Code
- Open Visual Studio Code.
- Press `Ctrl + K, Ctrl + O` (or **File** → **Open Folder...**).
- Select the `Energy_Operations_RAG_Assistant` folder.

### Step 2: Open Integrated Terminal
- Press **`Ctrl + ~`** (or select **Terminal** → **New Terminal**).

### Step 3: Create & Activate Virtual Environment
```powershell
# Create virtual environment (Python 3.11 recommended; Python 3.12 also supported)
py -3.11 -m venv .venv

# Activate the virtual environment in PowerShell
.\.venv\Scripts\Activate.ps1
```
> **Note for PowerShell execution:** If script execution is restricted on your machine, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

### Step 4: Install Dependencies
```powershell
pip install -r requirements-dev.txt
```
*(This installs runtime packages: `fastapi`, `uvicorn`, `pandas`, `numpy`, `scikit-learn`, `pydantic` plus dev tools: `pytest`, `httpx`).*

---

## 2. One-Click F5 Run & Debug Experience

This repository includes a pre-configured [`.vscode/launch.json`](file:///d:/Energy_Operations_RAG_Assistant/.vscode/launch.json) and [`.vscode/settings.json`](file:///d:/Energy_Operations_RAG_Assistant/.vscode/settings.json).

You do **not** need to type complex terminal commands. Simply press **`F5`**!

```
       [ VS Code Run & Debug Menu (Ctrl + Shift + D) ]
       ▼
 ┌────────────────────────────────────────────────────────┐
 │ 🟢 FastAPI: Run Assistant Server (Uvicorn + Reload)    │
 │ 🟢 Pytest: Run All Tests (48 Test Scenarios)           │
 │ 🟢 Benchmark: Run Retrieval Evaluation (1,000 Queries) │
 └────────────────────────────────────────────────────────┘
```

### Configuration 1: `FastAPI: Run Assistant Server`
- **What it does:** Starts the Uvicorn ASGI server hosting the FastAPI backend on `http://127.0.0.1:8000` with live reload enabled.
- **Shortcut:** Press `F5` while selected in the debug dropdown.
- **Features:** Any file modification in `backend/` or `frontend/` auto-reloads the server in real-time. Breakpoints in `backend/app.py` or `backend/rag_engine.py` pause execution for inspection.

### Configuration 2: `Pytest: Run All Tests`
- **What it does:** Runs all 48 integration, scenario, and unit tests.
- **VS Code GUI:** Open the **Testing Explorer** panel on the left sidebar (flask icon). You can run tests individually or view green checkmarks next to each test function.

### Configuration 3: `Benchmark: Run Retrieval Evaluation`
- **What it does:** Executes `eval_retrieval.py` directly in the debug console, displaying Top-1 Accuracy, Recall@3, Citation Validity, and 1,000 sequential request latency.

---

## 3. Interactive API Documentation

FastAPI automatically generates rich, interactive OpenAPI documentation. Once your server is running (via `F5` or `uvicorn`), access the following URLs in your browser:

| Interface | URL | Purpose |
|---|---|---|
| **Web Dashboard** | [`http://127.0.0.1:8000`](http://127.0.0.1:8000) | Primary operator dashboard with energy panorama, topic cards, and live health dot. |
| **Swagger UI** | [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs) | Interactive API playground to test endpoints, schemas, and live queries with "Try it out". |
| **ReDoc UI** | [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc) | Beautiful, human-readable API reference documentation. |
| **OpenAPI JSON** | [`http://127.0.0.1:8000/openapi.json`](http://127.0.0.1:8000/openapi.json) | Raw machine-readable OpenAPI schema. |
| **Case Study Reference** | [`http://127.0.0.1:8000/case_study`](http://127.0.0.1:8000/case_study) | Original case study requirements and evaluation criteria. |

---

### Detailed Endpoint Reference

#### 1. Execute Operational Query: `POST /api/run`
Executes the full RAG pipeline (validation ➔ TF-IDF ➔ cosine ranking ➔ threshold guard ➔ traceable citation generation).

**cURL Command:**
```bash
curl -X POST "http://127.0.0.1:8000/api/run" \
  -H "Content-Type: application/json" \
  -d '{"text": "What should be checked for inverter derating?", "top_k": 3}'
```

**JSON Response (200 OK):**
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
  "latency_ms": 0.72,
  "disclaimer": "Standard Safety Note: This assistant provides guidance extracted strictly from local operational documents. It does not replace site-specific SOPs, lockout-tagout procedures, or qualified engineering personnel.",
  "evaluation_hint": "Predictions verified against local operational SOPs using TF-IDF retrieval with traceable citations and safety guards."
}
```

---

#### 2. Health Check: `GET /api/health`
Monitors system availability, document indexing state, and uptime. Used directly by Render for deployment health probes and by the frontend for live status indicators.

**cURL Command:**
```bash
curl -X GET "http://127.0.0.1:8000/api/health"
```

**JSON Response (200 OK):**
```json
{
  "status": "healthy",
  "indexed_documents": 4,
  "indexed_chunks": 4,
  "topics": [
    "Grid & Dispatch Operations",
    "Hydroelectric Operations",
    "Solar PV Operations",
    "Wind Turbine Operations"
  ],
  "uptime_seconds": 245.8
}
```

---

#### 3. Document Catalog: `GET /api/documents`
Returns all indexed renewable operational SOPs with chunk counts and topics.

**cURL Command:**
```bash
curl -X GET "http://127.0.0.1:8000/api/documents"
```

**JSON Response (200 OK):**
```json
{
  "total_documents": 4,
  "total_chunks": 4,
  "documents": [
    {
      "source_file": "solar_inverter_sop.md",
      "document_title": "Solar Inverter SOP",
      "topic": "Solar PV Operations",
      "chunk_count": 1
    },
    {
      "source_file": "wind_turbine_maintenance.md",
      "document_title": "Wind Turbine Maintenance",
      "topic": "Wind Turbine Operations",
      "chunk_count": 1
    },
    {
      "source_file": "hydro_safety_brief.md",
      "document_title": "Hydro Safety Brief",
      "topic": "Hydroelectric Operations",
      "chunk_count": 1
    },
    {
      "source_file": "grid_operations_note.md",
      "document_title": "Grid Operations Note",
      "topic": "Grid & Dispatch Operations",
      "chunk_count": 1
    }
  ]
}
```

---

#### 4. Operational Metrics: `GET /api/metrics`
Reports query volume, refusal rates, validation error counts, and average response latency.

**cURL Command:**
```bash
curl -X GET "http://127.0.0.1:8000/api/metrics"
```

**JSON Response (200 OK):**
```json
{
  "total_queries": 12,
  "successful_queries": 10,
  "insufficient_evidence_queries": 2,
  "validation_errors": 0,
  "average_latency_ms": 0.81,
  "indexed_documents": 4,
  "indexed_chunks": 4
}
```

---

## 4. The Health Check Architecture: How It Works

The `/api/health` endpoint serves two vital purposes:

### 1. Render Zero-Downtime Deployment Gate
In [`render.yaml`](file:///d:/Energy_Operations_RAG_Assistant/render.yaml):
```yaml
healthCheckPath: /api/health
```
When Render builds and starts the new container, it polls `/api/health`. Only when Uvicorn responds with HTTP 200 `status: healthy` does Render switch traffic from the old instance to the new instance. If indexing fails, Render cancels traffic cutover, preserving 100% uptime.

### 2. Live Frontend Status Heartbeat
In [`frontend/app.js`](file:///d:/Energy_Operations_RAG_Assistant/frontend/app.js):
- The browser polls `/api/health` every 12 seconds.
- **Green Dot (`Backend Online`):** Backend is responsive; document count badge dynamically updates.
- **Red Dot (`Backend Offline`):** If network connectivity is lost, the dot turns red, retry interval drops to 5 seconds, and user is cleanly notified.
- **Automatic Recovery:** Once connectivity is restored, the status immediately flips back to green without requiring a page reload.

---

## 5. Automated GitHub to Render Continuous Deployment

Whenever you push to the `main` branch on GitHub, Render automatically triggers a zero-touch build and deploy.

```
       [ Local VS Code ]
              │
              │ git push origin main
              ▼
   [ GitHub Repository: main ]
              │
              │ Automatic Webhook
              ▼
   [ Render Cloud Builder ]
    1. Reads .python-version (3.11.9)
    2. Installs pre-built binary wheels (5 seconds)
    3. Starts Uvicorn on 0.0.0.0:$PORT
    4. Probes /api/health (200 OK)
              │
              ▼
  [ Live Public HTTPS URL Ready! ]
```

### Automatic Deploy Steps

1. **Commit and push your work:**
   ```powershell
   git add .
   git commit -m "feat: impressive developer guide, render configuration, and api docs"
   git push origin main
   ```

2. **Render Auto-Builds:**
   - Render detects the new commit on branch `main`.
   - It reads [`.python-version`](file:///d:/Energy_Operations_RAG_Assistant/.python-version) and selects **Python 3.11.9**.
   - It runs `pip install -r requirements.txt`.
   - It runs `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`.
   - It verifies `/api/health`.
   - Your assistant is live at `https://<your-service-name>.onrender.com`!
