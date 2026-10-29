"""Unit tests for EnergyRAGEngine.

Tests document ingestion, text normalization, sentence splitting,
chunking, TF-IDF vectorization, cosine similarity retrieval, ranking,
tied scores, threshold refusals, and citation generation.
"""

from pathlib import Path
import pytest
from backend.rag_engine import EnergyRAGEngine, DocumentChunk, detect_topic

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def engine():
    """Engine initialized with the actual operational documents."""
    return EnergyRAGEngine(data_dir=DATA_DIR)


def test_detect_topic():
    """Verify topic detection logic for renewable domains."""
    assert detect_topic("solar_inverter_sop.md", "Solar Inverter SOP") == "Solar PV Operations"
    assert detect_topic("wind_turbine_maintenance.md", "Wind Turbine Maintenance") == "Wind Turbine Operations"
    assert detect_topic("hydro_safety_brief.md", "Hydro Safety Brief") == "Hydroelectric Operations"
    assert detect_topic("grid_operations_note.md", "Grid Operations Note") == "Grid & Dispatch Operations"


def test_normalize_text(engine):
    """Verify text normalization preserves technical units and cleans excess whitespace."""
    raw = "  If inverter   temperature   exceeds \r\n 75C, inspect cooling   fans. \n\n\n\n Done.  "
    clean = engine.normalize_text(raw)
    assert "inverter temperature exceeds" in clean
    assert "75C" in clean
    assert "\n\n\n" not in clean


def test_split_into_sentences(engine):
    """Verify splitting into sentences handles headings and body lines correctly."""
    doc = "# Test Title\nFirst sentence. Second sentence here! Third one?"
    sentences = engine.split_into_sentences(doc)
    assert len(sentences) == 3
    assert sentences[0] == "First sentence."
    assert sentences[1] == "Second sentence here!"
    assert sentences[2] == "Third one?"


def test_load_documents(engine):
    """Verify all 4 operational markdown documents are discovered and loaded."""
    assert len(engine.documents) == 4
    expected_files = {
        "solar_inverter_sop.md",
        "wind_turbine_maintenance.md",
        "grid_operations_note.md",
        "hydro_safety_brief.md",
    }
    assert set(engine.documents.keys()) == expected_files


def test_create_chunks_from_document(engine):
    """Verify chunk generation produces stable IDs and source attribution."""
    content = "# Solar Inverter SOP\nStep 1 is check temperature. Step 2 is check fans."
    chunks = engine.create_chunks_from_document("solar_inverter_sop.md", content)
    assert len(chunks) >= 1
    chunk = chunks[0]
    assert chunk.source_file == "solar_inverter_sop.md"
    assert chunk.document_title == "Solar Inverter SOP"
    assert chunk.chunk_id.startswith("solar_inverter_sop_chunk_")


def test_empty_document_handling(engine):
    """Verify empty document produces no chunks and does not cause errors."""
    chunks = engine.create_chunks_from_document("empty.md", "")
    assert chunks == []
    chunks_whitespace = engine.create_chunks_from_document("whitespace.md", "   \n\n   ")
    assert chunks_whitespace == []


def test_query_validation(engine):
    """Verify validation rejects null, empty, whitespace, and oversized inputs."""
    ok, _ = engine.validate_query("Valid question?")
    assert ok is True

    ok_empty, msg = engine.validate_query("")
    assert ok_empty is False
    assert "empty" in msg

    ok_ws, msg = engine.validate_query("    \t\n  ")
    assert ok_ws is False

    ok_long, msg = engine.validate_query("x" * 501)
    assert ok_long is False
    assert "too long" in msg


def test_retrieval_solar(engine):
    """Verify solar query retrieves solar_inverter_sop.md with top score."""
    retrieved = engine.retrieve("What should be checked for inverter derating?")
    assert len(retrieved) > 0
    top_chunk, score = retrieved[0]
    assert top_chunk.source_file == "solar_inverter_sop.md"
    assert score > 0.15


def test_retrieval_wind(engine):
    """Verify wind query retrieves wind_turbine_maintenance.md."""
    retrieved = engine.retrieve("How should gearbox vibration be investigated?")
    assert len(retrieved) > 0
    top_chunk, score = retrieved[0]
    assert top_chunk.source_file == "wind_turbine_maintenance.md"
    assert score > 0.15


def test_retrieval_grid(engine):
    """Verify grid query retrieves grid_operations_note.md."""
    retrieved = engine.retrieve("What factors should be reviewed for generation deviation?")
    assert len(retrieved) > 0
    top_chunk, score = retrieved[0]
    assert top_chunk.source_file == "grid_operations_note.md"
    assert score > 0.15


def test_retrieval_hydro(engine):
    """Verify hydro query retrieves hydro_safety_brief.md."""
    retrieved = engine.retrieve("What checks are needed before spillway gate inspection?")
    assert len(retrieved) > 0
    top_chunk, score = retrieved[0]
    assert top_chunk.source_file == "hydro_safety_brief.md"
    assert score > 0.15


def test_tied_scores_deterministic(engine):
    """Verify ranking tie-breaking is deterministic."""
    # Retrieval should be stable across repeated identical calls
    r1 = engine.retrieve("temperature inspection")
    r2 = engine.retrieve("temperature inspection")
    assert [c.chunk_id for c, _ in r1] == [c.chunk_id for c, _ in r2]
    assert [s for _, s in r1] == [s for _, s in r2]


def test_unsupported_question_refusal(engine):
    """Verify out-of-domain questions receive structured insufficient-evidence refusal."""
    res = engine.query("What is the recipe for baking a chocolate cake?")
    assert res.status == "insufficient_evidence"
    assert "Insufficient evidence" in res.answer
    assert len(res.citations) == 0


def test_citations_contain_valid_excerpts(engine):
    """Verify all citations map to actual document text in data files."""
    res = engine.query("inverter temperature and cooling fans")
    assert res.status == "success"
    assert len(res.citations) > 0
    for citation in res.citations:
        source_text = engine.documents[citation.source_file]
        assert citation.excerpt in source_text
