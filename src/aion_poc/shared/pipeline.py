"""Lightweight helpers to build and query a demo RAG index."""

from __future__ import annotations

import hashlib
import logging
import json
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence, cast


from ..augmentation_service.core import AugmentationManager
from ..chunking_service.core import chunk_documents
from ..config.settings import AppSettings, get_settings
from ..embedding_service.core import generate_document_embeddings, get_embedding_model
from ..ingestion_service.core import CorpusLoadReport, DirectoryIngestionSummary, load_corpus, load_documents_from_sources
from ..logging_config import configure_logging
from ..retrieval_service.core import retrieve_similar_chunks
from ..vectorstore_service.core import VectorStoreSyncResult, load_manifest, synchronize_documents

configure_logging()
logger = logging.getLogger(__name__)


@dataclass
class DemoIndex:
    """Container holding everything needed to answer demo queries."""

    settings: AppSettings
    documents: List[Any]
    chunks: List[Any]
    embeddings: List[List[float]]


@dataclass
class DemoContext:
    """A single supporting chunk returned with a query."""

    score: float
    snippet: str
    metadata: dict


@dataclass
class DemoQueryResult:
    """Result returned by :func:`run_demo_query`."""

    question: str
    answer: str
    contexts: List[DemoContext]


@dataclass
class IngestionStats:
    """Timing and count metrics for an ingestion run."""

    total_documents: int
    total_chunks: int
    ingestion_time: float
    embedding_time: float
    storage_time: float
    total_time: float
    run_started_at: str
    run_completed_at: str
    documents_added: int
    documents_updated: int
    documents_removed: int
    chunks_indexed: int
    chunks_deleted: int
    documents_skipped: int
    ad_hoc_documents_ingested: int
    corpus_profile: Dict[str, Any]
    corpus_report: CorpusLoadReport
    vectorstore_sync: VectorStoreSyncResult


@dataclass
class PipelineQueryResponse:
    """Envelope returned from :meth:`DemoPipeline.query`."""

    answer: str
    sources: List[str]
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class QueryTelemetry:
    """Runtime metrics captured for each pipeline query."""

    question: str
    timestamp: str
    strategy: str
    retrieval_time: float
    augmentation_time: float
    total_time: float
    context_count: int
    confidence: float
    hit: bool


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = sum(a * a for a in vec_a) ** 0.5
    mag_b = sum(b * b for b in vec_b) ** 0.5

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def _format_snippet(text: str, max_chars: int = 320) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[: max_chars - 3]}..."


def _load_query_history(settings: AppSettings) -> List[QueryTelemetry]:
    """Load query history from a JSON file in the vectorstore directory."""
    history_file = settings.vectorstore_path / "query_telemetry.json"
    if not history_file.exists():
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Re-hydrate dataclasses from dicts
        return [QueryTelemetry(**entry) for entry in data]
    except (json.JSONDecodeError, TypeError, OSError) as e:
        logger.warning(
            "Could not load or parse query history file",
            extra={"path": str(history_file), "error": str(e)},
        )
        return []


def _save_query_history(history: List[QueryTelemetry], settings: AppSettings) -> None:
    """Save the query history to a JSON file."""
    history_file = settings.vectorstore_path / "query_telemetry.json"
    try:
        # Convert list of dataclasses to list of dicts for JSON serialization
        data_to_save = [entry.__dict__ for entry in history]
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2)
    except (TypeError, OSError) as e:
        logger.error(
            "Failed to save query history",
            extra={"path": str(history_file), "error": str(e)},
        )

def _summarize_corpus(documents: Sequence[Any], chunks: Sequence[Any]) -> Dict[str, Any]:
    """Compute aggregate statistics for the loaded corpus and chunk set."""

    source_dirs: Counter[str] = Counter()
    source_types: Counter[str] = Counter()

    for document in documents:
        metadata = getattr(document, "metadata", {}) or {}
        directory = metadata.get("source_dir")
        if directory:
            source_dirs[str(directory)] += 1
        source_type = metadata.get("source_type")
        if source_type:
            source_types[str(source_type)] += 1

    chunk_lengths = [len(getattr(chunk, "page_content", "")) for chunk in chunks]
    empty_chunks = sum(1 for length in chunk_lengths if length == 0)

    token_estimate = 0
    duplicate_chunks = 0
    seen_hashes: set[str] = set()
    for chunk in chunks:
        content = getattr(chunk, "page_content", "")
        if content:
            token_estimate += len(content.split())
            digest = hashlib.md5(content.encode("utf-8")).hexdigest()
            if digest in seen_hashes:
                duplicate_chunks += 1
            else:
                seen_hashes.add(digest)

    average_chunk_length = (sum(chunk_lengths) / len(chunk_lengths)) if chunk_lengths else 0.0
    average_tokens_per_chunk = (token_estimate / len(chunk_lengths)) if chunk_lengths else 0.0
    chunks_per_document = (len(chunks) / len(documents)) if documents else 0.0

    return {
        "total_documents": len(documents),
        "total_chunks": len(chunks),
        "source_directories": dict(source_dirs.most_common()),
        "source_types": dict(source_types.most_common()),
        "average_chunk_length": round(average_chunk_length, 2),
        "average_tokens_per_chunk": round(average_tokens_per_chunk, 2),
        "chunks_per_document": round(chunks_per_document, 2),
        "duplicate_chunks": duplicate_chunks,
        "empty_chunks": empty_chunks,
        "estimated_token_count": token_estimate,
    }


def build_demo_index() -> DemoIndex:
    """Ingest, chunk, and embed the local corpus for quick demos."""

    start_time = time.perf_counter()
    settings = cast(AppSettings, get_settings())
    settings_data = settings.model_dump()
    chunk_config: Dict[str, Any] = settings_data.get("chunking", {})
    embedding_config: Dict[str, Any] = settings_data.get("embedding", {})

    logger.info(
        "Starting demo index build",
        extra={"data_dirs": [str(path) for path in settings.absolute_data_dirs]},
    )
    logger.debug(
        "Demo build configuration",
        extra={
            "chunk_size": chunk_config.get("chunk_size"),
            "chunk_overlap": chunk_config.get("chunk_overlap"),
            "embedding_model": embedding_config.get("model"),
        },
    )

    corpus_start = time.perf_counter()
    documents, corpus_report = load_corpus()
    corpus_duration = time.perf_counter() - corpus_start
    logger.info(
        "Loaded %d documents in %.2fs",
        len(documents),
        corpus_duration,
        extra={
            "files_processed": corpus_report.files_processed,
            "files_skipped": corpus_report.files_skipped,
        },
    )
    if logger.isEnabledFor(logging.DEBUG) and documents:
        first_metadata = getattr(documents[0], "metadata", {})
        logger.debug(
            "Sample document metadata",
            extra={"metadata": dict(list(first_metadata.items())[:5]) if isinstance(first_metadata, dict) else first_metadata},
        )

    if not documents:
        logger.warning("No documents found in corpus directories: %s", settings.absolute_data_dirs)

    chunk_start = time.perf_counter()
    chunks = chunk_documents(documents)
    chunk_duration = time.perf_counter() - chunk_start
    logger.info(
        "Created %d chunks in %.2fs",
        len(chunks),
        chunk_duration,
        extra={
            "chunk_size": chunk_config.get("chunk_size"),
            "chunk_overlap": chunk_config.get("chunk_overlap"),
        },
    )
    embeddings, _, embedding_duration = generate_document_embeddings(chunks)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Embedding batch summary",
            extra={"chunk_count": len(chunks), "embedding_time": round(embedding_duration, 3)},
        )
    corpus_profile = _summarize_corpus(documents, chunks)
    logger.debug(
        "Corpus profile snapshot",
        extra={
            "source_directories": corpus_profile.get("source_directories", {}),
            "source_types": corpus_profile.get("source_types", {}),
            "average_chunk_length": corpus_profile.get("average_chunk_length"),
        },
    )

    total_duration = time.perf_counter() - start_time
    logger.info("Demo index ready in %.2fs", total_duration)

    return DemoIndex(
        settings=settings,
        documents=documents,
        chunks=chunks,
        embeddings=embeddings,
    )


def run_demo_query(question: str, index: DemoIndex, top_k: int = 4) -> DemoQueryResult:
    """Return a deterministic answer assembled from the most similar chunks."""

    query_start = time.perf_counter()
    normalized_question = " ".join(question.split())
    logger.info(
        "Running demo query",
        extra={"question": normalized_question[:160], "top_k": top_k},
    )
    logger.debug(
        "Query context",
        extra={
            "has_embeddings": bool(index.embeddings),
            "document_count": len(index.documents),
            "chunk_count": len(index.chunks),
        },
    )

    if not index.embeddings:
        raise ValueError("The demo index contains no embeddings. Did you run build_demo_index()?")

    embedder = get_embedding_model()
    try:
        query_vec = embedder.embed_query(question)
    except Exception as exc:  # pragma: no cover - depends on embedding backend
        logger.exception("Failed to embed query", extra={"error": str(exc)})
        raise

    scored = []
    for chunk, vector in zip(index.chunks, index.embeddings):
        score = _cosine_similarity(query_vec, vector)
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    top_matches = scored[:top_k]
    logger.debug(
        "Scores computed",
        extra={"total_scored": len(scored), "positive_scores": sum(1 for score, _ in scored if score > 0)},
    )

    match_snapshot = [
        {
            "score": round(score, 4),
            "chunk_index": chunk.metadata.get("chunk_index"),
            "source": chunk.metadata.get("source_file"),
        }
        for score, chunk in top_matches
        if score > 0
    ]
    if match_snapshot:
        logger.debug("Top matches", extra={"matches": match_snapshot})

    contexts = [
        DemoContext(
            score=score,
            snippet=_format_snippet(chunk.page_content),
            metadata=dict(chunk.metadata),
        )
        for score, chunk in top_matches
        if score > 0
    ]

    if contexts:
        summary_lines = [
            f"- {ctx.snippet}"
            for ctx in contexts
        ]
        answer = "Here is what I found based on the knowledge base:\n" + "\n".join(summary_lines)
    else:
        answer = "I could not find a relevant answer in the indexed corpus."
        logger.warning("No supporting chunks found for query", extra={"question": normalized_question[:160]})

    duration = time.perf_counter() - query_start
    logger.info(
        "Query processed",
        extra={"contexts": len(contexts), "duration_seconds": round(duration, 3)},
    )
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Query response prepared",
            extra={
                "context_sources": [ctx.metadata.get("source_file") for ctx in contexts[:3]],
                "answer_preview": answer[:120],
            },
        )

    return DemoQueryResult(question=question, answer=answer, contexts=contexts)


class DemoPipeline:
    """High-level coordinator that wraps the demo index helpers."""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.index: Optional[DemoIndex] = None
        self.last_stats: Optional[IngestionStats] = None
        self.last_sync_result: Optional[VectorStoreSyncResult] = None
        self.last_corpus_report: Optional[CorpusLoadReport] = None
        self.corpus_profile: Dict[str, Any] = {}
        self.query_history: List[QueryTelemetry] = _load_query_history(self.settings)
        self.augmentation = AugmentationManager(settings.model_dump())

    def initialize(self) -> None:
        """Build the initial index so queries can run immediately."""

        logger.info("Initialising demo pipeline")
        init_start = time.perf_counter()
        index, stats = self._build_index()
        self.index = index
        self.last_stats = stats
        logger.info(
            "Demo pipeline ready",
            extra={
                "documents": stats.total_documents,
                "chunks": stats.total_chunks,
                "duration_seconds": stats.total_time,
            },
        )
        logger.debug(
            "Pipeline initialized",
            extra={"initialization_time": round(time.perf_counter() - init_start, 3)},
        )

    async def ingest_documents(self, sources: List[Dict[str, Any]]) -> IngestionStats:
        """Process additional documents and rebuild the in-memory index."""

        logger.info("Starting ingestion run", extra={"source_count": len(sources)})
        extra_documents = load_documents_from_sources(sources)
        index, stats = self._build_index(extra_documents=extra_documents)
        self.index = index
        self.last_stats = stats
        logger.info(
            "Ingestion run complete",
            extra={
                "documents": stats.total_documents,
                "chunks": stats.total_chunks,
                "total_time": stats.total_time,
            },
        )
        logger.debug(
            "Ingestion run stats",
            extra={
                "extra_documents": len(extra_documents),
                "documents_total": stats.total_documents,
                "chunks_total": stats.total_chunks,
            },
        )
        return stats

    async def query(self, query: str, *, strategy: str = "demo", top_k: int = 3) -> PipelineQueryResponse:
        """Answer a question using configured retrieval and augmentation."""

        if self.index is None:
            raise RuntimeError("Pipeline is not initialized")

        logger.debug("Pipeline query starting", extra={"strategy": strategy, "top_k": top_k})
        retrieval_start = time.perf_counter()

        contexts: List[DemoContext] = []
        sources: List[str] = []
        confidences: List[float] = []

        if strategy == "vectorstore":
            retrieved = retrieve_similar_chunks(query, top_k)
            for document, score in retrieved:
                contexts.append(
                    DemoContext(
                        score=score,
                        snippet=_format_snippet(document.page_content),
                        metadata=dict(document.metadata),
                    )
                )
                sources.append(str(document.metadata.get("source") or document.metadata.get("source_file")))
                confidences.append(score if isinstance(score, (int, float)) else 0.0)
        else:
            result = run_demo_query(query, self.index, top_k=top_k)
            contexts = result.contexts
            for context in contexts:
                source = context.metadata.get("source_file") or context.metadata.get("source_path")
                if source:
                    sources.append(str(source))
                confidences.append(context.score)

        retrieval_time = time.perf_counter() - retrieval_start

        augmentation_start = time.perf_counter()
        augmentation_response = await self.augmentation.generate_answer(
            query,
            contexts,
            answer_type=self.augmentation.detect_query_type(query),
        )
        augmentation_time = time.perf_counter() - augmentation_start

        confidence = max(confidences) if confidences else augmentation_response.confidence
        metadata = {
            "query_type": strategy,
            "retrieval_time": round(retrieval_time, 3),
            "augmentation_time": round(augmentation_time, 3),
            "total_time": round(retrieval_time + augmentation_time, 3),
            "context_count": len(contexts),
        }
        metadata["contexts_returned"] = len(contexts)
        metadata["hit"] = bool(contexts)

        telemetry = QueryTelemetry(
            question=query,
            timestamp=datetime.now(timezone.utc).isoformat(),
            strategy=strategy,
            retrieval_time=retrieval_time,
            augmentation_time=augmentation_time,
            total_time=retrieval_time + augmentation_time,
            context_count=len(contexts),
            confidence=confidence,
            hit=bool(contexts),
        )
        self.query_history.append(telemetry)
        if len(self.query_history) > 100:
            self.query_history = self.query_history[-100:]
        _save_query_history(self.query_history, self.settings)

        logger.info(
            "Query completed",
            extra={
                "query": query[:160],
                "contexts": len(contexts),
                "confidence": round(confidence, 4),
            },
        )
        logger.debug(
            "Pipeline query metadata",
            extra={
                "sources": sources[:3],
                "retrieval_time": round(retrieval_time, 3),
                "augmentation_time": round(augmentation_time, 3),
            },
        )

        return PipelineQueryResponse(
            answer=augmentation_response.answer,
            sources=augmentation_response.sources or sources,
            confidence=confidence,
            metadata={**metadata, **augmentation_response.metadata},
        )

    async def query_with_documents(
        self, query: str, documents: List[Any], top_k: int = 3
    ) -> PipelineQueryResponse:
        """
        Answer a question using a temporary, in-memory index of provided documents.
        This is ideal for "chat with your document" scenarios.
        """
        if not documents:
            return await self.query(query, strategy="vectorstore", top_k=top_k)

        logger.info(
            "Starting query with temporary documents",
            extra={"query": query[:120], "document_count": len(documents)},
        )
        query_start_time = time.perf_counter()

        # 1. Chunk the temporary documents
        temp_chunks = chunk_documents(documents)

        # 2. Embed the temporary chunks
        temp_embeddings, _, _ = generate_document_embeddings(temp_chunks)

        # 3. Perform in-memory similarity search
        retrieval_start = time.perf_counter()
        embedder = get_embedding_model()
        query_vec = embedder.embed_query(query)

        scored = []
        for chunk, vector in zip(temp_chunks, temp_embeddings):
            score = _cosine_similarity(query_vec, vector)
            scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        top_matches = scored[:top_k]

        contexts = [
            DemoContext(
                score=score,
                snippet=_format_snippet(chunk.page_content),
                metadata=dict(chunk.metadata),
            )
            for score, chunk in top_matches
            if score > 0
        ]
        retrieval_time = time.perf_counter() - retrieval_start

        # 4. Augment the answer
        augmentation_start = time.perf_counter()
        augmentation_response = await self.augmentation.generate_answer(
            query, contexts, answer_type=self.augmentation.detect_query_type(query)
        )
        augmentation_time = time.perf_counter() - augmentation_start

        # 5. Assemble response and metadata
        confidence = max([ctx.score for ctx in contexts]) if contexts else 0.0
        metadata = {
            "query_type": "attachment_query",
            "retrieval_time": round(retrieval_time, 3),
            "augmentation_time": round(augmentation_time, 3),
            "total_time": round(time.perf_counter() - query_start_time, 3),
            "context_count": len(contexts),
            "hit": bool(contexts),
        }

        return PipelineQueryResponse(
            answer=augmentation_response.answer,
            sources=augmentation_response.sources or [doc.metadata.get("source_file", "Uploaded File") for doc in documents],
            confidence=confidence,
            metadata={**metadata, **augmentation_response.metadata},
        )

    async def get_system_stats(self) -> Dict[str, Any]:
        """Return snapshot metrics used by the CLI dashboard."""

        if self.index is None:
            raise RuntimeError("Pipeline is not initialized")

        manifest = load_manifest()
        manifest_entries = manifest.entries
        stored_chunks = sum(entry.get("chunk_count", 0) for entry in manifest_entries.values())
        tracked_files = len(manifest_entries)
        manifest_metadata = manifest.metadata or {}

        last_synced_at = manifest_metadata.get("last_synced_at")
        last_checked_at = manifest_metadata.get("last_checked_at")
        storage_bytes = int(manifest_metadata.get("storage_bytes", 0))
        try:
            manifest_age_seconds = (
                (datetime.now(timezone.utc) - datetime.fromisoformat(last_synced_at)).total_seconds()
                if last_synced_at
                else None
            )
        except (ValueError, TypeError):
            manifest_age_seconds = None

        last_sync_summary = manifest_metadata.get("last_sync_summary")
        if not isinstance(last_sync_summary, dict):
            last_sync_summary = {}

        pipeline_stats: Dict[str, Any] = {
            "total_documents": len(self.index.documents),
            "total_chunks": len(self.index.chunks),
        }
        if self.last_stats is not None:
            pipeline_stats.update(
                {
                    "last_ingestion_duration_seconds": self.last_stats.total_time,
                    "last_ingestion_started_at": self.last_stats.run_started_at,
                    "last_ingestion_completed_at": self.last_stats.run_completed_at,
                    "documents_added_last_run": self.last_stats.documents_added,
                    "documents_updated_last_run": self.last_stats.documents_updated,
                    "documents_removed_last_run": self.last_stats.documents_removed,
                    "chunks_indexed_last_run": self.last_stats.chunks_indexed,
                    "chunks_deleted_last_run": self.last_stats.chunks_deleted,
                    "documents_skipped_last_run": self.last_stats.documents_skipped,
                    "ad_hoc_documents_ingested": self.last_stats.ad_hoc_documents_ingested,
                }
            )

        vector_store: Dict[str, Any] = {
            "provider": "chroma" if manifest_entries else "in-memory",
            "collection_name": self.settings.vectorstore.collection,
            "tracked_files": tracked_files,
            "stored_chunks": stored_chunks,
            "last_synced_at": last_synced_at,
            "last_checked_at": last_checked_at,
            "storage_bytes": storage_bytes,
            "manifest_age_seconds": round(manifest_age_seconds, 3) if manifest_age_seconds is not None else None,
            "documents_added_last_sync": last_sync_summary.get("documents_added", 0),
            "documents_updated_last_sync": last_sync_summary.get("documents_updated", 0),
            "documents_removed_last_sync": last_sync_summary.get("documents_removed", 0),
            "chunks_indexed_last_sync": last_sync_summary.get("chunks_indexed", 0),
            "chunks_deleted_last_sync": last_sync_summary.get("chunks_deleted", 0),
            "total_sync_runs": manifest_metadata.get("total_sync_runs", 0),
            "total_sync_checks": manifest_metadata.get("total_sync_checks", 0),
        }

        corpus_profile = (
            self.last_stats.corpus_profile
            if self.last_stats is not None
            else _summarize_corpus(self.index.documents, self.index.chunks)
        )

        corpus_report_section: Dict[str, Any] = {}
        if self.last_stats is not None:
            corpus_report = self.last_stats.corpus_report
            corpus_report_section = {
                "documents_loaded": corpus_report.documents_loaded,
                "files_processed": corpus_report.files_processed,
                "files_skipped": corpus_report.files_skipped,
                "missing_directories": corpus_report.missing_directories,
                "extra_documents_ingested": corpus_report.extra_documents,
                "directory_summaries": [
                    {
                        "directory": summary.directory,
                        "documents_added": summary.documents_added,
                        "files_processed": summary.files_processed,
                        "files_skipped": summary.files_skipped,
                        "duration_seconds": summary.duration_seconds,
                    }
                    for summary in corpus_report.directory_summaries
                ],
            }

        history = self.query_history
        query_metrics: Dict[str, Any] = {"total_queries": len(history)}
        recent_queries: List[Dict[str, Any]] = []
        if history:
            hit_ratio = sum(1 for entry in history if entry.hit) / len(history)
            avg_retrieval = mean(entry.retrieval_time for entry in history)
            avg_augmentation = mean(entry.augmentation_time for entry in history)
            avg_total = mean(entry.total_time for entry in history)
            last_entry = history[-1]
            query_metrics.update(
                {
                    "hit_ratio": round(hit_ratio, 3),
                    "avg_retrieval_ms": round(avg_retrieval * 1000, 2),
                    "avg_augmentation_ms": round(avg_augmentation * 1000, 2),
                    "avg_total_ms": round(avg_total * 1000, 2),
                    "last_query_at": last_entry.timestamp,
                    "last_query_latency_ms": round(last_entry.total_time * 1000, 2),
                    "last_query_confidence": round(last_entry.confidence, 4),
                }
            )
            recent_queries = [
                {
                    "question": entry.question[:120],
                    "timestamp": entry.timestamp,
                    "strategy": entry.strategy,
                    "latency_ms": round(entry.total_time * 1000, 2),
                    "contexts": entry.context_count,
                    "confidence": round(entry.confidence, 4),
                }
                for entry in history[-5:]
            ]

        alerts: List[str] = []
        if self.last_stats is not None and self.last_stats.documents_skipped:
            alerts.append(f"{self.last_stats.documents_skipped} files were skipped during the last ingestion run.")
        if (
            self.last_stats is not None
            and self.last_stats.corpus_report.missing_directories
        ):
            alerts.append(
                "Missing data directories: "
                + ", ".join(self.last_stats.corpus_report.missing_directories)
            )
        if corpus_profile.get("duplicate_chunks", 0):
            alerts.append(f"{corpus_profile['duplicate_chunks']} duplicate chunks detected in the current index.")
        if vector_store["documents_removed_last_sync"]:
            alerts.append(
                f"{vector_store['documents_removed_last_sync']} documents were removed during the last vector store sync."
            )

        configuration = {
            "chunking_strategy": self.settings.chunking.method,
            "embedding_model": self.settings.embedding.model,
            "vector_store_provider": vector_store["provider"],
            "llm_provider": "demo",
            "llm_model": self.settings.llm.model,
        }

        logger.debug(
            "System stats gathered",
            extra={
                "documents": pipeline_stats["total_documents"],
                "chunks": pipeline_stats["total_chunks"],
                "vector_store": vector_store,
            },
        )

        return {
            "pipeline_stats": pipeline_stats,
            "vector_store": vector_store,
            "corpus_profile": corpus_profile,
            "corpus_report": corpus_report_section,
            "query_metrics": query_metrics,
            "recent_queries": recent_queries,
            "alerts": alerts,
            "configuration": configuration,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform simple health diagnostics for the CLI."""

        if self.index is None:
            return {
                "overall": "degraded",
                "components": {
                    "corpus": "not_initialized",
                    "embeddings": "not_initialized",
                },
            }

        components = {
            "corpus": "healthy" if self.index.documents else "empty",
            "chunks": "healthy" if self.index.chunks else "empty",
            "embeddings": "healthy" if self.index.embeddings else "empty",
        }

        overall = "healthy" if all(value == "healthy" for value in components.values()) else "degraded"
        logger.info("Health check evaluated", extra={"overall": overall, "components": components})
        return {
            "overall": overall,
            "components": components,
        }

    def _build_index(self, *, extra_documents: Optional[List[Any]] = None) -> tuple[DemoIndex, IngestionStats]:
        """Rebuild the demo index, optionally appending additional documents."""

        run_started_at = datetime.now(timezone.utc)
        start_time = time.perf_counter()

        ingest_start = time.perf_counter()
        documents, corpus_report = load_corpus()
        ingest_duration = time.perf_counter() - ingest_start

        additional_documents = len(extra_documents or [])
        if extra_documents:
            documents.extend(extra_documents)
            corpus_report.extra_documents = additional_documents
            logger.debug(
                "Appended extra documents",
                extra={"additional_documents": additional_documents},
            )

        chunk_start = time.perf_counter()
        chunks = chunk_documents(documents)
        chunk_duration = time.perf_counter() - chunk_start
        logger.debug(
            "Chunking completed",
            extra={
                "documents": len(documents),
                "chunks": len(chunks),
                "duration_seconds": round(chunk_duration, 3),
            },
        )

        embeddings, embedder, embedding_duration = generate_document_embeddings(chunks)
        corpus_profile = _summarize_corpus(documents, chunks)

        sync_result = synchronize_documents(chunks, embedder)

        total_duration = time.perf_counter() - start_time
        run_completed_at = datetime.now(timezone.utc)

        stats = IngestionStats(
            total_documents=len(documents),
            total_chunks=len(chunks),
            ingestion_time=round(ingest_duration, 3),
            embedding_time=round(embedding_duration, 3),
            storage_time=round(sync_result.elapsed_seconds, 3),
            total_time=round(total_duration, 3),
            run_started_at=run_started_at.isoformat(),
            run_completed_at=run_completed_at.isoformat(),
            documents_added=sync_result.documents_added,
            documents_updated=sync_result.documents_updated,
            documents_removed=sync_result.documents_removed,
            chunks_indexed=sync_result.chunks_indexed,
            chunks_deleted=sync_result.chunks_deleted,
            documents_skipped=corpus_report.files_skipped,
            ad_hoc_documents_ingested=additional_documents,
            corpus_profile=corpus_profile,
            corpus_report=corpus_report,
            vectorstore_sync=sync_result,
        )
        logger.debug(
            "Index rebuild metrics",
            extra={
                "documents": stats.total_documents,
                "chunks": stats.total_chunks,
                "documents_added": stats.documents_added,
                "documents_updated": stats.documents_updated,
                "documents_removed": stats.documents_removed,
                "ingestion_time": stats.ingestion_time,
                "embedding_time": stats.embedding_time,
                "storage_time": stats.storage_time,
                "total_time": stats.total_time,
            },
        )

        self.last_stats = stats
        self.last_corpus_report = corpus_report
        self.corpus_profile = corpus_profile
        self.last_sync_result = sync_result

        index = DemoIndex(
            settings=self.settings,
            documents=documents,
            chunks=chunks,
            embeddings=embeddings,
        )

        return index, stats


_PIPELINE_STATE: Dict[str, Optional[DemoPipeline]] = {"instance": None}


def initialize_pipeline(force: bool = False) -> DemoPipeline:
    """Initialize the global demo pipeline and return it."""

    pipeline = _PIPELINE_STATE.get("instance")

    if pipeline is None or force:
        settings = cast(AppSettings, get_settings())
        pipeline = DemoPipeline(settings)
        pipeline.initialize()
        _PIPELINE_STATE["instance"] = pipeline
    return pipeline


def get_pipeline() -> DemoPipeline:
    """Return the cached demo pipeline, initializing it on first use."""

    pipeline = initialize_pipeline()
    if pipeline is None:  # pragma: no cover - defensive guard
        raise RuntimeError("Pipeline failed to initialize")
    return pipeline
