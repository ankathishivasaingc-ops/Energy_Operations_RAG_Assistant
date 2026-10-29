"""Energy Operations Document RAG Assistant - Core Engine.

This module provides document ingestion, chunking, TF-IDF vector indexing,
cosine similarity retrieval, evidence-grounded answer generation,
traceable citations, and safety checks.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class DocumentChunk:
    """Represents a chunk of an operational document."""
    chunk_id: str
    source_file: str
    document_title: str
    chunk_index: int
    text: str
    topic: str


@dataclass
class Citation:
    """Traceable citation pointing back to source document evidence."""
    source_file: str
    document_title: str
    chunk_id: str
    excerpt: str
    similarity_score: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "source_file": self.source_file,
            "document_title": self.document_title,
            "chunk_id": self.chunk_id,
            "excerpt": self.excerpt,
            "similarity_score": round(float(self.similarity_score), 4),
        }


@dataclass
class RAGResponse:
    """Structured response returned by the RAG workflow."""
    query: str
    status: str  # "success" | "insufficient_evidence" | "error"
    answer: str
    citations: List[Citation] = field(default_factory=list)
    retrieved_evidence: List[str] = field(default_factory=list)
    similarity_scores: List[float] = field(default_factory=list)
    matched_topic: Optional[str] = None
    latency_ms: float = 0.0
    disclaimer: str = (
        "Standard Safety Note: This assistant provides guidance extracted strictly "
        "from local operational documents. It does not replace site-specific SOPs, "
        "lockout-tagout procedures, or qualified engineering personnel."
    )

    def to_dict(self) -> Dict[str, object]:
        return {
            "query": self.query,
            "status": self.status,
            "answer": self.answer,
            "citations": [c.to_dict() for c in self.citations],
            "retrieved_evidence": self.retrieved_evidence,
            "similarity_scores": [round(float(s), 4) for s in self.similarity_scores],
            "matched_topic": self.matched_topic,
            "latency_ms": round(float(self.latency_ms), 2),
            "disclaimer": self.disclaimer,
        }


def detect_topic(filename: str, title: str) -> str:
    """Map filename or title to energy operational topic."""
    name = (filename + " " + title).lower()
    if "solar" in name or "inverter" in name:
        return "Solar PV Operations"
    elif "wind" in name or "turbine" in name:
        return "Wind Turbine Operations"
    elif "hydro" in name or "spillway" in name:
        return "Hydroelectric Operations"
    elif "grid" in name or "transmission" in name or "frequency" in name:
        return "Grid & Dispatch Operations"
    return "General Renewable Operations"


class EnergyRAGEngine:
    """TF-IDF and Cosine Similarity RAG engine for Energy Operations."""

    def __init__(
        self,
        data_dir: Path,
        similarity_threshold: float = 0.15,
        default_top_k: int = 3,
        chunk_sentence_window: int = 2,
        chunk_sentence_overlap: int = 1,
    ):
        self.data_dir = Path(data_dir)
        self.similarity_threshold = similarity_threshold
        self.default_top_k = default_top_k
        self.chunk_sentence_window = max(1, chunk_sentence_window)
        self.chunk_sentence_overlap = max(0, chunk_sentence_overlap)

        self.documents: Dict[str, str] = {}
        self.chunks: List[DocumentChunk] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.is_indexed: bool = False

        # Load and index on initialization if data_dir exists
        if self.data_dir.exists():
            self.reload()

    def normalize_text(self, text: str) -> str:
        """Normalize whitespace while preserving technical punctuation and units (75C, etc.)."""
        if not text:
            return ""
        # Replace non-breaking spaces and irregular whitespace
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse multiple spaces and tabs
        text = re.sub(r"[ \t]+", " ", text)
        # Collapse consecutive newlines to at most two
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences while respecting decimals and temperatures."""
        # Clean text
        clean = self.normalize_text(text)
        if not clean:
            return []
        # Remove markdown heading prefixes before sentence splitting if on first line
        lines = [line.strip() for line in clean.split("\n") if line.strip()]
        body_lines = []
        for line in lines:
            if line.startswith("#"):
                continue  # skip title line in body sentence list
            body_lines.append(line)

        body_text = " ".join(body_lines)
        if not body_text:
            return []

        # Split on sentence ending punctuation followed by space and capital letter or end of string
        raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", body_text)
        sentences = [s.strip() for s in raw_sentences if s.strip()]
        return sentences

    def create_chunks_from_document(
        self,
        filename: str,
        content: str
    ) -> List[DocumentChunk]:
        """Extract title and split document body into traceable chunks."""
        clean_content = self.normalize_text(content)
        if not clean_content:
            return []

        # Extract title from first markdown header
        title = filename.replace(".md", "").replace("_", " ").title()
        for line in clean_content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                break

        topic = detect_topic(filename, title)
        doc_base_id = re.sub(r"[^a-zA-Z0-9_]", "_", Path(filename).stem)

        sentences = self.split_into_sentences(clean_content)
        if not sentences:
            # If no sentences extracted from body, use normalized content directly
            sentences = [clean_content]

        chunks: List[DocumentChunk] = []
        step = max(1, self.chunk_sentence_window - self.chunk_sentence_overlap)

        for idx in range(0, len(sentences), step):
            window = sentences[idx : idx + self.chunk_sentence_window]
            chunk_text = " ".join(window)
            chunk_id = f"{doc_base_id}_chunk_{len(chunks)}"

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                source_file=filename,
                document_title=title,
                chunk_index=len(chunks),
                text=chunk_text,
                topic=topic,
            )
            chunks.append(chunk)

            # Break if window reached the end
            if idx + self.chunk_sentence_window >= len(sentences):
                break

        return chunks

    def load_documents(self) -> int:
        """Discover and load all supported UTF-8 markdown documents in data_dir."""
        self.documents.clear()
        self.chunks.clear()

        if not self.data_dir.exists() or not self.data_dir.is_dir():
            return 0

        # Discover all .md files in data directory (sorting for determinism)
        md_files = sorted(list(self.data_dir.glob("*.md")))

        for file_path in md_files:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                filename = file_path.name
                self.documents[filename] = content

                doc_chunks = self.create_chunks_from_document(filename, content)
                self.chunks.extend(doc_chunks)
            except Exception:
                # Silently skip unreadable files and continue ingesting valid documents
                continue

        return len(self.documents)

    def build_index(self) -> bool:
        """Build TF-IDF vector matrix from document chunks."""
        if not self.chunks:
            self.vectorizer = None
            self.tfidf_matrix = None
            self.is_indexed = False
            return False

        chunk_texts = [chunk.text for chunk in self.chunks]

        # Use unigram and bigram TF-IDF with english stop words and sublinear term frequency
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            lowercase=True,
            norm="l2",
            sublinear_tf=True,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(chunk_texts)
        self.is_indexed = True
        return True

    def reload(self) -> Dict[str, int]:
        """Reload documents from disk and re-build the retrieval index."""
        doc_count = self.load_documents()
        self.build_index()
        return {
            "documents_loaded": doc_count,
            "chunks_indexed": len(self.chunks),
        }

    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate question input according to domain guidelines."""
        if query is None:
            return False, "Query cannot be null."
        if not isinstance(query, str):
            return False, "Query must be a text string."
        trimmed = query.strip()
        if not trimmed:
            return False, "Question cannot be empty or contain only whitespace."
        if len(trimmed) > 500:
            return False, "Question is too long (maximum 500 characters allowed)."
        return True, trimmed

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Compute cosine similarity and retrieve ranked relevant chunks."""
        if not self.is_indexed or self.vectorizer is None or self.tfidf_matrix is None:
            return []

        k = top_k if top_k is not None else self.default_top_k
        query_vector = self.vectorizer.transform([query])

        # Compute cosine similarity
        similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]

        # Pair each chunk with its score
        scored_chunks: List[Tuple[DocumentChunk, float]] = []
        for idx, score in enumerate(similarities):
            scored_chunks.append((self.chunks[idx], float(score)))

        # Sort deterministically: similarity score descending, chunk_id ascending
        scored_chunks.sort(key=lambda item: (-item[1], item[0].chunk_id))

        # Return top_k results
        return scored_chunks[:k]

    def generate_grounded_answer(
        self,
        query: str,
        retrieved: List[Tuple[DocumentChunk, float]],
    ) -> Tuple[str, List[Citation], List[str], Optional[str]]:
        """Construct deterministic, evidence-grounded answer with traceable citations."""
        citations: List[Citation] = []
        evidence_excerpts: List[str] = []
        top_topic: Optional[str] = None

        if not retrieved:
            refusal = (
                "Insufficient evidence: No relevant operational procedures or technical guidelines "
                "were found for this query in the indexed documentation."
            )
            return refusal, [], [], None

        # Filter chunks that meet the relevance threshold
        relevant = [item for item in retrieved if item[1] >= self.similarity_threshold]

        if not relevant:
            max_score = retrieved[0][1] if retrieved else 0.0
            refusal = (
                f"Insufficient evidence: The query did not match any operational documents with "
                f"sufficient confidence (highest similarity: {max_score:.3f}, required: {self.similarity_threshold:.2f}). "
                "The system will not invent procedures or equipment thresholds."
            )
            return refusal, [], [], None

        # Build citations from relevant chunks
        seen_files = set()
        primary_chunk, primary_score = relevant[0]
        top_topic = primary_chunk.topic

        for chunk, score in relevant:
            citations.append(
                Citation(
                    source_file=chunk.source_file,
                    document_title=chunk.document_title,
                    chunk_id=chunk.chunk_id,
                    excerpt=chunk.text,
                    similarity_score=score,
                )
            )
            evidence_excerpts.append(chunk.text)
            seen_files.add(chunk.document_title)

        # Generate concise, grounded answer based strictly on evidence text
        if len(relevant) == 1:
            doc_title = primary_chunk.document_title
            answer = f"According to the **{doc_title}**:\n\n{primary_chunk.text}"
        else:
            # Multi-chunk synthesis
            answer_parts = [f"Based on the **{primary_chunk.document_title}**:"]
            answer_parts.append(primary_chunk.text)

            # If secondary chunk comes from another document or provides complementary steps
            for secondary_chunk, _ in relevant[1:]:
                if secondary_chunk.text != primary_chunk.text:
                    answer_parts.append(
                        f"\nAdditionally, per **{secondary_chunk.document_title}**: {secondary_chunk.text}"
                    )
            answer = "\n\n".join(answer_parts)

        return answer, citations, evidence_excerpts, top_topic

    def query(self, query_text: str, top_k: Optional[int] = None) -> RAGResponse:
        """Complete RAG execution workflow."""
        start_time = time.perf_counter()

        # Step 1: Query Validation
        is_valid, validation_msg_or_query = self.validate_query(query_text)
        if not is_valid:
            latency = (time.perf_counter() - start_time) * 1000.0
            return RAGResponse(
                query=str(query_text) if query_text is not None else "",
                status="error",
                answer=f"Validation error: {validation_msg_or_query}",
                latency_ms=latency,
            )

        clean_query = validation_msg_or_query

        # Step 2: Retrieval
        retrieved = self.retrieve(clean_query, top_k=top_k)

        # Step 3: Answer Generation and Citations
        answer, citations, evidence, topic = self.generate_grounded_answer(clean_query, retrieved)

        scores = [score for _, score in retrieved]

        # Determine response status
        if not citations:
            status = "insufficient_evidence"
        else:
            status = "success"

        latency = (time.perf_counter() - start_time) * 1000.0

        return RAGResponse(
            query=clean_query,
            status=status,
            answer=answer,
            citations=citations,
            retrieved_evidence=evidence,
            similarity_scores=scores,
            matched_topic=topic,
            latency_ms=latency,
        )
