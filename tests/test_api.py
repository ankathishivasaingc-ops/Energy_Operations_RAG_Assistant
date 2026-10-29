"""API integration tests for FastAPI application endpoints.

Tests /api/demo, /api/health, /api/documents, /api/metrics,
and /api/run with valid, invalid, boundary, and malformed inputs.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_api_demo_preserved():
    """Verify GET /api/demo maintains backward compatibility with original schema."""
    resp = client.get("/api/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_study"] == "Energy Operations Document RAG Assistant"
    assert "status" in data
    assert "expected_outcome" in data
    assert "engine_info" in data


def test_api_health():
    """Verify GET /api/health returns healthy status and document count."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["indexed_documents"] == 4
    assert len(data["topics"]) == 4


def test_api_documents():
    """Verify GET /api/documents lists all four operational documents."""
    resp = client.get("/api/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_documents"] == 4
    files = {d["source_file"] for d in data["documents"]}
    assert "solar_inverter_sop.md" in files
    assert "wind_turbine_maintenance.md" in files
    assert "hydro_safety_brief.md" in files
    assert "grid_operations_note.md" in files


def test_api_metrics():
    """Verify GET /api/metrics returns query tracking metrics."""
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_queries" in data
    assert "average_latency_ms" in data


def test_api_run_valid_solar():
    """Verify POST /api/run returns structured grounded response for solar question."""
    payload = {"text": "What should be checked for inverter derating?"}
    resp = client.post("/api/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["input"] == payload["text"]
    assert "Solar Inverter SOP" in data["result"]
    assert len(data["citations"]) > 0
    assert data["citations"][0]["source_file"] == "solar_inverter_sop.md"
    assert "disclaimer" in data
    assert "latency_ms" in data


def test_api_run_valid_wind():
    """Verify POST /api/run returns structured grounded response for wind question."""
    payload = {"text": "How should gearbox vibration be investigated?"}
    resp = client.post("/api/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["citations"][0]["source_file"] == "wind_turbine_maintenance.md"


def test_api_run_empty_question():
    """Verify POST /api/run rejects empty question with 400 Bad Request."""
    resp = client.post("/api/run", json={"text": ""})
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_api_run_whitespace_question():
    """Verify POST /api/run rejects whitespace-only question with 400 Bad Request."""
    resp = client.post("/api/run", json={"text": "   \n\t  "})
    assert resp.status_code == 400
    assert "whitespace" in resp.json()["detail"].lower()


def test_api_run_oversized_question():
    """Verify POST /api/run rejects questions exceeding 500 characters."""
    long_q = "How do we inspect the inverter? " * 30  # > 500 chars
    resp = client.post("/api/run", json={"text": long_q})
    assert resp.status_code in [400, 422]


def test_api_run_malformed_json():
    """Verify API handles invalid JSON payloads gracefully."""
    resp = client.post(
        "/api/run",
        content="not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_api_run_unsupported_refusal():
    """Verify POST /api/run safely refuses out-of-domain questions with insufficient_evidence."""
    payload = {"text": "What is the capital of Australia?"}
    resp = client.post("/api/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "insufficient_evidence"
    assert "insufficient evidence" in data["result"].lower()
    assert len(data["citations"]) == 0
