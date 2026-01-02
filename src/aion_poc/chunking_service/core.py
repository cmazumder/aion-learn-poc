"""Chunk the loaded documents using LangChain's RecursiveCharacterTextSplitter."""

from __future__ import annotations

import logging
import time
from importlib import import_module
from typing import Any, List

Document = import_module("langchain_core.documents").Document  # type: ignore[attr-defined]
RecursiveCharacterTextSplitter = import_module("langchain_text_splitters").RecursiveCharacterTextSplitter  # type: ignore[attr-defined]

from ..config.settings import get_settings
from ..logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


def chunk_documents(documents: List[Any]) -> List[Any]:
    """Split documents into smaller chunks suitable for embedding."""

    settings = get_settings()

    if not documents:
        logger.warning("No documents supplied for chunking; returning empty list")
        return []

    if logger.isEnabledFor(logging.DEBUG):
        sample_metadata = getattr(documents[0], "metadata", {})
        logger.debug(
            "Preparing to chunk documents",
            extra={
                "document_count": len(documents),
                "sample_metadata": dict(list(sample_metadata.items())[:5]) if isinstance(sample_metadata, dict) else sample_metadata,
            },
        )

    logger.debug(
        "Chunking documents",
        extra={
            "document_count": len(documents),
            "chunk_size": settings.chunking.chunk_size,
            "chunk_overlap": settings.chunking.chunk_overlap,
        },
    )
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunking.chunk_size,
        chunk_overlap=settings.chunking.chunk_overlap,
    )

    start_time = time.perf_counter()
    try:
        chunks = splitter.split_documents(documents)
    except Exception as exc:  # pragma: no cover - relies on splitter implementation
        logger.exception(
            "Chunking failed",
            extra={"document_count": len(documents), "error": str(exc)},
        )
        raise
    duration = time.perf_counter() - start_time

    # Annotate chunk metadata with the chunk index for traceability
    for idx, chunk in enumerate(chunks):
        chunk.metadata.setdefault("chunk_index", idx)

    if logger.isEnabledFor(logging.DEBUG):
        preview = [
            {
                "chunk_index": chunk.metadata.get("chunk_index"),
                "source_file": chunk.metadata.get("source_file"),
                "length": len(getattr(chunk, "page_content", "")),
            }
            for chunk in chunks[:3]
        ]
        logger.debug("Chunking preview", extra={"sample_chunks": preview})

    logger.info(
        "Created %d document chunks",
        len(chunks),
        extra={"duration_seconds": round(duration, 3)},
    )
    return chunks