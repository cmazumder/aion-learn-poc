"""Similarity search helpers for the demo index."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import List, Optional, Tuple

from langchain_core.documents import Document

from ..config.settings import get_settings
from ..embedding_service.core import get_embedding_model
from ..logging_config import configure_logging
from ..vectorstore_service.core import get_vectorstore


configure_logging()
LOGGER = logging.getLogger(__name__)


def retrieve_similar_chunks(query: str, top_k: Optional[int] = None) -> List[Tuple[Document, float]]:
    """Return the most relevant chunks for the supplied query."""

    settings = get_settings()
    embedding_model = get_embedding_model()
    store = get_vectorstore(embedding_model)
    k_value = top_k or settings.retrieval.top_k
    LOGGER.debug(
        "Executing similarity search",
        extra={
            "query_preview": query[:120],
            "top_k": k_value,
            "embedding_model": getattr(embedding_model, "model", embedding_model.__class__.__name__),
        },
    )
    LOGGER.info(
        "Retrieving similar chunks",
        extra={"query_length": len(query), "requested_results": k_value},
    )

    start_time = perf_counter()
    try:
        results = store.similarity_search_with_score(query, k=k_value)
    except Exception as exc:  # pragma: no cover - depends on vector store backend
        duration_ms = (perf_counter() - start_time) * 1000
        LOGGER.exception(
            "Vector store similarity search failed",
            extra={"elapsed_ms": round(duration_ms, 2), "top_k": k_value, "error": str(exc)},
        )
        raise
    duration_ms = (perf_counter() - start_time) * 1000

    if not results:
        LOGGER.warning(
            "No chunks matched query",
            extra={"query_preview": query[:80], "elapsed_ms": round(duration_ms, 2)},
        )
        return results

    top_document, top_score = results[0]
    if LOGGER.isEnabledFor(logging.DEBUG):
        LOGGER.debug(
            "Top match preview",
            extra={
                "top_score": round(top_score, 4) if isinstance(top_score, (int, float)) else top_score,
                "top_source": top_document.metadata.get("source"),
                "top_length": len(top_document.page_content),
            },
        )
    LOGGER.info(
        "Retrieved similar chunks",
        extra={
            "elapsed_ms": round(duration_ms, 2),
            "returned_results": len(results),
            "top_score": round(top_score, 4) if isinstance(top_score, (int, float)) else top_score,
            "top_source": top_document.metadata.get("source"),
        },
    )

    return results