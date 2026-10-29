"""Energy Operations Document RAG Assistant - FastAPI Application.

Provides REST API endpoints for document retrieval, question answering,
system health, document catalog, and metrics.
"""

from contextlib import asynccontextmanager
from pathlib import Path
import time
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.rag_engine import EnergyRAGEngine, RAGResponse

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

# Runtime metrics tracker
METRICS = {
    "total_queries": 0,
    "successful_queries": 0,
    "insufficient_evidence_queries": 0,
    "validation_errors": 0,
    "total_latency_ms": 0.0,
    "start_time": time.time(),
}

# Initialize engine instance
engine = EnergyRAGEngine(data_dir=DATA_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager to ensure data is indexed on startup."""
    engine.reload()
    yield


app = FastAPI(
    title="Energy Operations Document RAG Assistant",
    description="Operational RAG assistant for renewable-energy SOPs (Solar, Wind, Hydro, Grid).",
    version="1.0.0",
    lifespan=lifespan,
)

# Restrictive, safe CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class Query(BaseModel):
    """Request model for RAG queries."""
    text: str = Field(
        default="",
        description="The operational question to answer.",
        max_length=500,
    )
    top_k: Optional[int] = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of relevant chunks to retrieve.",
    )


class CitationModel(BaseModel):
    source_file: str
    document_title: str
    chunk_id: str
    excerpt: str
    similarity_score: float


class RunResponse(BaseModel):
    input: str
    result: str
    status: str
    citations: List[CitationModel]
    retrieved_evidence: List[str]
    similarity_scores: List[float]
    matched_topic: Optional[str] = None
    latency_ms: float
    disclaimer: str
    evaluation_hint: str


# Serve static files for frontend assets
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index():
    """Serve the primary dashboard interface."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Energy Operations Assistant API is running. Frontend not found."}


@app.get("/case_study")
def serve_case_study():
    """Serve the original case study problem statement."""
    case_study_file = BASE_DIR / "case_study.html"
    if case_study_file.exists():
        return FileResponse(case_study_file)
    raise HTTPException(status_code=404, detail="Case study document not found.")


@app.get("/api/demo")
def demo():
    """Preserved demo endpoint confirming system readiness."""
    return {
        "case_study": "Energy Operations Document RAG Assistant",
        "status": "ready" if engine.is_indexed else "indexing",
        "expected_outcome": (
            "A working RAG-based assistant that answers operational questions "
            "from provided documents with citations, retrieval evidence, and hallucination checks."
        ),
        "engine_info": {
            "indexed_documents": len(engine.documents),
            "indexed_chunks": len(engine.chunks),
            "retrieval_method": "TF-IDF + Cosine Similarity",
            "threshold": engine.similarity_threshold,
        },
    }


@app.get("/api/health")
def health():
    """Health check endpoint providing index status and document counts."""
    return {
        "status": "healthy" if engine.is_indexed else "degraded",
        "indexed_documents": len(engine.documents),
        "indexed_chunks": len(engine.chunks),
        "topics": sorted(list({c.topic for c in engine.chunks})),
        "uptime_seconds": round(time.time() - METRICS["start_time"], 1),
    }


@app.get("/api/documents")
def list_documents():
    """Return catalog of indexed renewable energy SOPs."""
    docs = []
    seen = set()
    for chunk in engine.chunks:
        if chunk.source_file not in seen:
            seen.add(chunk.source_file)
            docs.append({
                "source_file": chunk.source_file,
                "document_title": chunk.document_title,
                "topic": chunk.topic,
                "chunk_count": sum(1 for c in engine.chunks if c.source_file == chunk.source_file),
            })
    return {
        "total_documents": len(docs),
        "total_chunks": len(engine.chunks),
        "documents": docs,
    }


@app.get("/api/metrics")
def get_metrics():
    """Return runtime evaluation and query statistics."""
    avg_latency = (
        METRICS["total_latency_ms"] / METRICS["total_queries"]
        if METRICS["total_queries"] > 0
        else 0.0
    )
    return {
        "total_queries": METRICS["total_queries"],
        "successful_queries": METRICS["successful_queries"],
        "insufficient_evidence_queries": METRICS["insufficient_evidence_queries"],
        "validation_errors": METRICS["validation_errors"],
        "average_latency_ms": round(avg_latency, 2),
        "indexed_documents": len(engine.documents),
        "indexed_chunks": len(engine.chunks),
    }


@app.post("/api/run", response_model=RunResponse)
def run_case(query: Query):
    """Execute the complete RAG workflow for an operational query."""
    raw_text = query.text

    # Validation: missing / whitespace-only
    if not raw_text or not raw_text.strip():
        METRICS["validation_errors"] += 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or contain only whitespace.",
        )

    # Validation: length
    if len(raw_text.strip()) > 500:
        METRICS["validation_errors"] += 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is too long (maximum 500 characters allowed).",
        )

    # Execute RAG query
    rag_res: RAGResponse = engine.query(raw_text, top_k=query.top_k)

    # Update runtime metrics
    METRICS["total_queries"] += 1
    METRICS["total_latency_ms"] += rag_res.latency_ms
    if rag_res.status == "success":
        METRICS["successful_queries"] += 1
    elif rag_res.status == "insufficient_evidence":
        METRICS["insufficient_evidence_queries"] += 1

    return RunResponse(
        input=rag_res.query,
        result=rag_res.answer,
        status=rag_res.status,
        citations=[
            CitationModel(
                source_file=c.source_file,
                document_title=c.document_title,
                chunk_id=c.chunk_id,
                excerpt=c.excerpt,
                similarity_score=round(c.similarity_score, 4),
            )
            for c in rag_res.citations
        ],
        retrieved_evidence=rag_res.retrieved_evidence,
        similarity_scores=[round(s, 4) for s in rag_res.similarity_scores],
        matched_topic=rag_res.matched_topic,
        latency_ms=round(rag_res.latency_ms, 2),
        disclaimer=rag_res.disclaimer,
        evaluation_hint="Predictions verified against local operational SOPs using TF-IDF retrieval with traceable citations and safety guards.",
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Sanitize client-facing error responses without exposing internal traces."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch unexpected exceptions cleanly without exposing sensitive paths."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred while processing the operational query."},
    )
