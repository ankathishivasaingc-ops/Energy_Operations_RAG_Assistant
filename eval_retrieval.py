"""Evaluation script for Energy Operations Document RAG Assistant.

Evaluates retrieval quality against original questions.csv plus curated domain test cases,
computes Recall@k, citation validity, refusal rate, and runs a 1,000-request reliability benchmark.
"""

from pathlib import Path
import time
from typing import Dict, List
import pandas as pd

from backend.rag_engine import EnergyRAGEngine

DATA_DIR = Path(__file__).resolve().parent / "data"
CSV_PATH = DATA_DIR / "questions.csv"


def run_evaluation() -> Dict[str, object]:
    """Execute complete evaluation suite and return exact measured metrics."""
    engine = EnergyRAGEngine(data_dir=DATA_DIR)

    # 1. Load original benchmark questions from questions.csv
    original_df = pd.read_csv(CSV_PATH)
    original_cases = [
        {"question": row["question"], "expected_source": row["expected_source"], "type": "original"}
        for _, row in original_df.iterrows()
    ]

    # 2. Add curated domain test cases covering all 4 topics and negative queries
    additional_cases = [
        # Grid topic
        {
            "question": "What factors should be reviewed for generation deviation before escalation?",
            "expected_source": "grid_operations_note.md",
            "type": "grid_domain",
        },
        {
            "question": "How are grid frequency events and curtailment instructions checked?",
            "expected_source": "grid_operations_note.md",
            "type": "grid_domain",
        },
        # Hydro topic
        {
            "question": "What safety verifications are required before inspecting a spillway gate?",
            "expected_source": "hydro_safety_brief.md",
            "type": "hydro_domain",
        },
        {
            "question": "Who must communicate with the control room before spillway gate work?",
            "expected_source": "hydro_safety_brief.md",
            "type": "hydro_domain",
        },
        # Paraphrased Solar
        {
            "question": "If inverter temperature exceeds 75C, what cooling checks should be performed?",
            "expected_source": "solar_inverter_sop.md",
            "type": "solar_paraphrase",
        },
        # Paraphrased Wind
        {
            "question": "What does rising nacelle temperature combined with gearbox vibration indicate?",
            "expected_source": "wind_turbine_maintenance.md",
            "type": "wind_paraphrase",
        },
        # Unsupported / Refusal test cases
        {
            "question": "How do you calculate the price of gold in 2026?",
            "expected_source": None,
            "type": "unsupported",
        },
        {
            "question": "What is the recommended recipe for vanilla cupcakes?",
            "expected_source": None,
            "type": "unsupported",
        },
        {
            "question": "What are the core operating procedures for nuclear fuel rods?",
            "expected_source": None,
            "type": "unsupported",
        },
    ]

    all_cases = original_cases + additional_cases

    # Metric accumulators
    total_queries = len(all_cases)
    supported_queries = [c for c in all_cases if c["expected_source"] is not None]
    unsupported_queries = [c for c in all_cases if c["expected_source"] is None]

    top1_correct = 0
    top3_correct = 0
    valid_citations = 0
    total_citations = 0
    successful_answers = 0
    correct_refusals = 0
    latencies: List[float] = []

    print(f"=== Evaluating RAG Assistant on {total_queries} test cases ===")

    for case in all_cases:
        q = case["question"]
        expected = case["expected_source"]

        t0 = time.perf_counter()
        res = engine.query(q, top_k=3)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        if expected is not None:
            # Check retrieval against expected source
            retrieved_sources = [c.source_file for c in res.citations]

            if retrieved_sources and retrieved_sources[0] == expected:
                top1_correct += 1
            if expected in retrieved_sources:
                top3_correct += 1

            if res.status == "success":
                successful_answers += 1

            # Check citation validity against actual document text
            for cit in res.citations:
                total_citations += 1
                doc_text = engine.documents.get(cit.source_file, "")
                if cit.excerpt and cit.excerpt in doc_text:
                    valid_citations += 1
        else:
            # Check safe refusal for unsupported questions
            if res.status == "insufficient_evidence" and len(res.citations) == 0:
                correct_refusals += 1

    top1_acc = (top1_correct / len(supported_queries)) * 100.0
    top3_recall = (top3_correct / len(supported_queries)) * 100.0
    citation_validity = (valid_citations / total_citations * 100.0) if total_citations > 0 else 100.0
    refusal_acc = (correct_refusals / len(unsupported_queries)) * 100.0
    avg_latency = sum(latencies) / len(latencies)

    print("\n--- Retrieval Quality Metrics ---")
    print(f"Indexed Documents: {len(engine.documents)}")
    print(f"Indexed Chunks:    {len(engine.chunks)}")
    print(f"Total Test Cases:  {total_queries} ({len(supported_queries)} supported, {len(unsupported_queries)} unsupported)")
    print(f"Top-1 Accuracy:    {top1_acc:.2f}% ({top1_correct}/{len(supported_queries)})")
    print(f"Recall@3:          {top3_recall:.2f}% ({top3_correct}/{len(supported_queries)})")
    print(f"Citation Validity: {citation_validity:.2f}% ({valid_citations}/{total_citations})")
    print(f"Refusal Accuracy:  {refusal_acc:.2f}% ({correct_refusals}/{len(unsupported_queries)})")
    print(f"Average Latency:   {avg_latency:.2f} ms")

    # 3. Repeated Reliability Test (1,000 deterministic requests)
    print("\n--- Running 1,000 Repeated Deterministic Requests ---")
    bench_start = time.perf_counter()
    bench_completed = 0
    bench_failures = 0
    bench_query = "What should be checked for inverter derating?"

    for i in range(1000):
        try:
            r = engine.query(bench_query)
            if r.status == "success" and r.citations[0].source_file == "solar_inverter_sop.md":
                bench_completed += 1
            else:
                bench_failures += 1
        except Exception:
            bench_failures += 1

    bench_total_duration = time.perf_counter() - bench_start
    avg_req_ms = (bench_total_duration / 1000.0) * 1000.0

    print(f"Completed:      {bench_completed}/1000")
    print(f"Failures:       {bench_failures}/1000")
    print(f"Total Duration: {bench_total_duration:.2f} seconds")
    print(f"Per-query time: {avg_req_ms:.3f} ms")

    return {
        "indexed_documents": len(engine.documents),
        "indexed_chunks": len(engine.chunks),
        "total_test_cases": total_queries,
        "top1_accuracy": top1_acc,
        "recall_at_3": top3_recall,
        "citation_validity_rate": citation_validity,
        "refusal_accuracy": refusal_acc,
        "average_latency_ms": round(avg_latency, 2),
        "benchmark_1000_completed": bench_completed,
        "benchmark_1000_failures": bench_failures,
        "benchmark_1000_duration_sec": round(bench_total_duration, 2),
    }


if __name__ == "__main__":
    run_evaluation()
