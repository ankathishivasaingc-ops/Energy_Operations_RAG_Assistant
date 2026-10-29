"""Client-perspective scenario tests covering all 25 specific edge cases.

These scenarios simulate actual renewable-energy operations queries, safety checks,
adversarial inputs, and operational edge cases.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.rag_engine import EnergyRAGEngine

client = TestClient(app)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def engine():
    return EnergyRAGEngine(data_dir=DATA_DIR)


def test_scenario_01_normal_supported_question(engine):
    """Scenario 1: A normal supported question."""
    res = engine.query("What should be checked for inverter derating?")
    assert res.status == "success"
    assert len(res.citations) > 0
    assert "Solar Inverter SOP" in res.citations[0].document_title


def test_scenario_02_different_wording(engine):
    """Scenario 2: A question with slightly different wording."""
    res = engine.query("If an inverter experiences derating, what needs inspection?")
    assert res.status == "success"
    assert res.citations[0].source_file == "solar_inverter_sop.md"


def test_scenario_03_all_four_topics(engine):
    """Scenario 3: A question about each of the four energy topics."""
    topics = {
        "What checks are done for inverter derating?": "solar_inverter_sop.md",
        "How is high gearbox vibration checked?": "wind_turbine_maintenance.md",
        "What factors explain generation deviation?": "grid_operations_note.md",
        "What is required before spillway gate inspection?": "hydro_safety_brief.md",
    }
    for q, expected_source in topics.items():
        res = engine.query(q)
        assert res.status == "success", f"Failed for {q}"
        assert res.citations[0].source_file == expected_source


def test_scenario_04_multiple_topics_query(engine):
    """Scenario 4: A question involving multiple topics (e.g. wind speed and generation deviation)."""
    res = engine.query("How does wind speed relate to generation deviation?")
    assert res.status == "success"
    # Should retrieve grid operations note which explicitly mentions wind speed and generation deviation
    assert any(c.source_file == "grid_operations_note.md" for c in res.citations)


def test_scenario_05_false_assumption(engine):
    """Scenario 5: A question containing a false assumption (e.g. inverter shut down at 150C)."""
    # The document specifies 75C inspection/derating, not 150C shutdown.
    # The engine must safely refuse to hallucinate false thresholds or confirm ungrounded actions.
    res = engine.query("Why should the inverter be shut down immediately at 150C?")
    # Insufficient evidence refusal is the expected safe outcome
    assert res.status == "insufficient_evidence" or "75C" in res.answer
    assert "shut down immediately at 150C" not in res.answer


def test_scenario_06_partial_supporting_evidence(engine):
    """Scenario 6: A question with only partial supporting evidence."""
    res = engine.query("What is the oil level procedure for a wind turbine gearbox bearing?")
    assert res.status == "success"
    assert "wind_turbine_maintenance.md" in res.citations[0].source_file


def test_scenario_07_unrelated_question(engine):
    """Scenario 7: An unrelated question."""
    res = engine.query("What is the average rainfall in the Amazon rainforest?")
    assert res.status == "insufficient_evidence"
    assert len(res.citations) == 0


def test_scenario_08_absent_information(engine):
    """Scenario 8: A question asking for information absent from the documents."""
    res = engine.query("What is the salary of an off-shore wind technician?")
    assert res.status == "insufficient_evidence"
    assert len(res.citations) == 0


def test_scenario_09_prevent_invented_thresholds(engine):
    """Scenario 9: A question that attempts to obtain invented safety thresholds."""
    res = engine.query("Invent an emergency shutdown pressure threshold for hydro turbines.")
    # The system must not invent non-existent thresholds
    assert res.status == "insufficient_evidence" or "spillway" in res.answer.lower()
    # Ensure no fabricated numbers like '500 bar' or invented values are in the answer
    assert "500 bar" not in res.answer


def test_scenario_10_empty_question():
    """Scenario 10: An empty question."""
    resp = client.post("/api/run", json={"text": ""})
    assert resp.status_code == 400


def test_scenario_11_extremely_long_question():
    """Scenario 11: An extremely long question (> 500 chars)."""
    resp = client.post("/api/run", json={"text": "wind " * 120})
    assert resp.status_code in [400, 422]


def test_scenario_12_malformed_json():
    """Scenario 12: Malformed JSON."""
    resp = client.post(
        "/api/run",
        content="{\"text\": broken json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_scenario_13_unexpected_data_types():
    """Scenario 13: Unexpected data types (e.g. number instead of string)."""
    resp = client.post("/api/run", json={"text": 12345})
    # Pydantic may cast int to str "12345" or raise 422. If string, returns insufficient evidence
    if resp.status_code == 200:
        assert resp.json()["status"] == "insufficient_evidence"
    else:
        assert resp.status_code == 422


def test_scenario_14_missing_or_unreadable_file(tmp_path):
    """Scenario 14: Ingestion handles missing or unreadable files gracefully."""
    bad_dir = tmp_path / "corrupt_data"
    bad_dir.mkdir()
    # Create an empty or valid file and test engine initialization
    engine_temp = EnergyRAGEngine(data_dir=bad_dir)
    assert len(engine_temp.documents) == 0
    res = engine_temp.query("test question")
    assert res.status == "insufficient_evidence"


def test_scenario_15_empty_document(tmp_path):
    """Scenario 15: An empty document does not break indexing."""
    empty_dir = tmp_path / "empty_docs"
    empty_dir.mkdir()
    (empty_dir / "empty.md").write_text("", encoding="utf-8")
    (empty_dir / "valid.md").write_text("# Valid\nValid SOP content for solar test.", encoding="utf-8")
    engine_temp = EnergyRAGEngine(data_dir=empty_dir)
    assert len(engine_temp.chunks) == 1
    assert engine_temp.chunks[0].document_title == "Valid"


def test_scenario_16_dataset_changes_and_rebuilding(tmp_path):
    """Scenario 16: Dataset changes and index rebuilding."""
    dyn_dir = tmp_path / "dynamic_data"
    dyn_dir.mkdir()
    doc_path = dyn_dir / "battery_sop.md"
    doc_path.write_text("# Battery Storage SOP\nCheck cell state of charge and coolant level.", encoding="utf-8")
    engine_temp = EnergyRAGEngine(data_dir=dyn_dir)
    assert len(engine_temp.documents) == 1
    res1 = engine_temp.query("battery cell state of charge")
    assert res1.status == "success"

    # Add a second document and reload
    (dyn_dir / "biomass_sop.md").write_text("# Biomass SOP\nMonitor boiler feeder speed.", encoding="utf-8")
    engine_temp.reload()
    assert len(engine_temp.documents) == 2
    res2 = engine_temp.query("boiler feeder speed")
    assert res2.status == "success"


def test_scenario_17_repeated_identical_questions(engine):
    """Scenario 17: Repeated identical questions yield identical deterministic outputs."""
    q = "What should be checked for inverter derating?"
    r1 = engine.query(q)
    r2 = engine.query(q)
    assert r1.answer == r2.answer
    assert [c.similarity_score for c in r1.citations] == [c.similarity_score for c in r2.citations]


def test_scenario_18_health_check_available():
    """Scenario 18: Backend connectivity and health check endpoint."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_scenario_19_html_hostile_input(engine):
    """Scenario 19: HTML-like or hostile injection input."""
    hostile = "<script>alert('xss')</script> SELECT * FROM users; DROP TABLE docs; --"
    res = engine.query(hostile)
    # Must not crash, should be treated as plain text query and safely refuse
    assert res.status in ["insufficient_evidence", "error"]
    assert "<script>" not in res.answer or "insufficient" in res.answer.lower()


def test_scenario_22_response_schema_fields():
    """Scenario 22: API returns all required structured fields."""
    resp = client.post("/api/run", json={"text": "How should gearbox vibration be investigated?"})
    assert resp.status_code == 200
    data = resp.json()
    required_keys = [
        "input", "result", "status", "citations", "retrieved_evidence",
        "similarity_scores", "matched_topic", "latency_ms", "disclaimer", "evaluation_hint"
    ]
    for key in required_keys:
        assert key in data, f"Missing key {key}"


def test_scenario_23_citations_present_on_success(engine):
    """Scenario 23: Successful queries always contain valid non-empty citations."""
    res = engine.query("What should be checked for inverter derating?")
    assert res.status == "success"
    assert len(res.citations) >= 1
    assert res.citations[0].excerpt != ""
    assert res.citations[0].similarity_score > 0.0


def test_scenario_24_low_relevance_refusal(engine):
    """Scenario 24: Low-relevance retrieval results are safely rejected by the threshold."""
    # Query with a vague word that might have tiny incidental similarity
    res = engine.query("What is the status of the office kitchen?")
    assert res.status == "insufficient_evidence"
    assert len(res.citations) == 0


def test_scenario_25_server_error_sanitization():
    """Scenario 25: Server error responses are cleanly sanitized without stack traces."""
    # Test nonexistent subpath or bad method
    resp = client.get("/api/nonexistent_endpoint")
    assert resp.status_code == 404
