"""Embedding helpers wired to project settings."""

from __future__ import annotations

import hashlib
import logging
import random
import importlib
from functools import lru_cache
from time import perf_counter
from typing import Any, List, Optional, Sequence, Tuple, Type, cast

from langchain_core.embeddings import Embeddings  # type: ignore[import-not-found]

from ..config.settings import AppSettings, get_settings
from ..logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

EmbeddingFactory = Optional[Type[Embeddings]]


def _load_embedding_class(module_name: str, class_name: str) -> EmbeddingFactory:
    """Helper to import an embedding class dynamically without hard dependency."""

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        logger.debug(
            "Embedding provider module unavailable",
            extra={"provider_module": module_name, "error": str(exc)},
        )
        return None

    embedding_class = getattr(module, class_name, None)
    if embedding_class is None:
        logger.debug(
            "Embedding class missing from module",
            extra={"provider_module": module_name, "missing_class": class_name},
        )
    return embedding_class


LatestOllamaEmbeddings = _load_embedding_class("langchain_ollama", "OllamaEmbeddings")
CommunityOllamaEmbeddings = _load_embedding_class("langchain_community.embeddings", "OllamaEmbeddings")


class HashEmbeddings(Embeddings):
    """Deterministic hash-based embeddings for fallback scenarios."""

    def __init__(self, size: int = 512):
        self.size = size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        seed_source = hashlib.sha256(text.encode("utf-8")).hexdigest()
        seed = int(seed_source[:16], 16)
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(self.size)]


@lru_cache()
def get_embedding_model() -> Embeddings:
    """Return a cached embedding model, falling back to a hash variant."""

    settings = cast(AppSettings, get_settings())
    embedding_config = getattr(settings, "embedding", None)
    model_name = str(getattr(embedding_config, "model", "unknown"))
    logger.debug(
        "Selecting embedding provider",
        extra={"requested_model": model_name},
    )

    if LatestOllamaEmbeddings is not None:
        provider_cls = cast(Any, LatestOllamaEmbeddings)
        logger.info(
            "Using langchain-ollama embeddings",
            extra={"model": model_name, "provider": "langchain-ollama"},
        )
        logger.debug(
            "Instantiating langchain-ollama embeddings",
            extra={"provider_module": LatestOllamaEmbeddings.__module__},
        )
        return provider_cls(model=model_name)

    if CommunityOllamaEmbeddings is not None:
        provider_cls = cast(Any, CommunityOllamaEmbeddings)
        logger.warning(
            "Using deprecated langchain_community OllamaEmbeddings; upgrade to langchain-ollama",
            extra={"model": model_name},
        )
        logger.debug(
            "Instantiating deprecated Ollama embeddings",
            extra={"provider_module": CommunityOllamaEmbeddings.__module__},
        )
        return provider_cls(model=model_name)

    logger.info(
        "No Ollama embedding provider available; falling back to hash embeddings",
        extra={"attempted_modules": ["langchain_ollama", "langchain_community.embeddings"]},
    )
    logger.debug("Creating deterministic hash embeddings", extra={"vector_size": HashEmbeddings().size})

    logger.warning("Using deterministic hash embeddings; install and run Ollama for real vectors.")
    return HashEmbeddings()


def generate_document_embeddings(chunks: Sequence[Any]) -> Tuple[List[List[float]], Embeddings, float]:
    """Return embeddings for the supplied chunks and the underlying embedding model."""

    embedder = get_embedding_model()
    if not chunks:
        logger.warning("No chunks supplied for embedding; returning empty vectors")
        return [], embedder, 0.0

    texts = [getattr(chunk, "page_content", "") for chunk in chunks]
    logger.debug(
        "Generating embeddings",
        extra={
            "chunk_count": len(texts),
            "embedding_model": getattr(embedder, "model", embedder.__class__.__name__),
        },
    )

    start_time = perf_counter()
    try:
        embeddings = embedder.embed_documents(texts)
    except Exception as exc:  # pragma: no cover - backend specific
        logger.exception(
            "Embedding generation failed",
            extra={"chunk_count": len(texts), "error": str(exc)},
        )
        raise
    duration = perf_counter() - start_time

    vector_size = len(embeddings[0]) if embeddings else 0
    logger.info(
        "Generated embeddings",
        extra={
            "chunk_count": len(embeddings),
            "duration_seconds": round(duration, 3),
            "vector_size": vector_size,
        },
    )

    return embeddings, embedder, duration