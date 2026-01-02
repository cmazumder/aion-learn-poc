"""Convenience helpers for interacting with the Chroma vector store."""

from __future__ import annotations

import logging
import json
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Sequence, Tuple, cast

from langchain_community.vectorstores import Chroma  # type: ignore[import-untyped]
from langchain_core.embeddings import Embeddings  # type: ignore[attr-defined]

from ..config.settings import AppSettings, VectorStoreSettings, get_settings
from ..logging_config import configure_logging

configure_logging()
LOGGER = logging.getLogger(__name__)

MANIFEST_FILENAME = "manifest.json"
MANIFEST_META_KEY = "__meta__"
ALLOWED_METADATA_TYPES: Tuple[type, ...] = (str, int, float, bool)


@dataclass
class VectorStoreManifest:
    entries: Dict[str, Dict[str, int]]
    metadata: Dict[str, Any]


@dataclass
class VectorStoreSyncResult:
    elapsed_seconds: float
    documents_added: int
    documents_updated: int
    documents_removed: int
    chunks_indexed: int
    chunks_deleted: int
    sync_started_at: str
    sync_completed_at: str
    storage_bytes: int
    tracked_files: int
    stored_chunks: int


def get_vectorstore(embedding: Optional[Embeddings] = None) -> Chroma:
    """Return a Chroma vector store bound to the configured collection."""

    settings = cast(AppSettings, get_settings())
    vectorstore_settings = settings.vectorstore
    assert isinstance(vectorstore_settings, VectorStoreSettings)
    collection_name = cast(str, getattr(vectorstore_settings, "collection"))
    embedding_model = embedding or _get_default_embedding()
    settings.vectorstore_path.mkdir(parents=True, exist_ok=True)

    LOGGER.info(
        "Connecting to vector store",
        extra={
            "collection": collection_name,
            "persist_directory": str(settings.vectorstore_path),
            "embedding_model": getattr(embedding_model, "model", embedding_model.__class__.__name__),
        },
    )
    timer_start = perf_counter()

    try:
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embedding_model,
            persist_directory=str(settings.vectorstore_path),
        )
    except Exception as exc:  # pragma: no cover - backend specific
        LOGGER.exception(
            "Vector store initialization failed",
            extra={"error": str(exc), "persist_directory": str(settings.vectorstore_path)},
        )
        raise

    elapsed_ms = (perf_counter() - timer_start) * 1000
    LOGGER.debug(
        "Vector store ready",
        extra={
            "collection": collection_name,
            "persist_directory": str(settings.vectorstore_path),
            "elapsed_ms": round(elapsed_ms, 2),
        },
    )

    return vectorstore


def load_manifest() -> VectorStoreManifest:
    """Load the vector store manifest describing indexed documents."""

    settings = cast(AppSettings, get_settings())
    manifest_path = settings.vectorstore_path / MANIFEST_FILENAME
    if not manifest_path.exists():
        LOGGER.debug(
            "Vector store manifest not found", extra={"manifest_path": str(manifest_path)}
        )
        return VectorStoreManifest(entries={}, metadata={})

    try:
        raw_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, dict):
            raise ValueError("Manifest root must be a dict")

        metadata = raw_data.get(MANIFEST_META_KEY, {})
        if not isinstance(metadata, dict):
            metadata = {}

        entries: Dict[str, Dict[str, int]] = {}
        for path, stats in raw_data.items():
            if path == MANIFEST_META_KEY:
                continue
            if not isinstance(stats, dict):
                LOGGER.debug(
                    "Skipping malformed manifest entry",
                    extra={"entry": path, "value_type": type(stats).__name__},
                )
                continue
            entries[path] = {
                "mtime_ns": int(stats.get("mtime_ns", 0)),
                "size_bytes": int(stats.get("size_bytes", 0)),
                "chunk_count": int(stats.get("chunk_count", 0)),
            }

        return VectorStoreManifest(entries=entries, metadata=metadata)
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        LOGGER.exception(
            "Failed to load vector store manifest",
            extra={"manifest_path": str(manifest_path), "error": str(exc)},
        )
        return VectorStoreManifest(entries={}, metadata={})


def save_manifest(manifest: VectorStoreManifest) -> None:
    """Persist the vector store manifest to disk."""

    settings = cast(AppSettings, get_settings())
    manifest_path = settings.vectorstore_path / MANIFEST_FILENAME
    payload: Dict[str, Any] = {**manifest.entries, MANIFEST_META_KEY: manifest.metadata}
    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        LOGGER.debug(
            "Vector store manifest saved",
            extra={"manifest_path": str(manifest_path), "entries": len(manifest.entries)},
        )
    except OSError as exc:
        LOGGER.exception(
            "Failed to write vector store manifest",
            extra={"manifest_path": str(manifest_path), "error": str(exc)},
        )


def reset_vectorstore() -> None:
    """Remove the persisted vector store so it can be rebuilt from scratch."""

    settings = get_settings()
    persist_path = settings.vectorstore_path

    if persist_path.exists():
        shutil.rmtree(persist_path)
        LOGGER.info(
            "Reset vector store directory",
            extra={"persist_directory": str(persist_path)},
        )
    else:
        LOGGER.debug(
            "Vector store directory not present during reset",
            extra={"persist_directory": str(persist_path)},
        )


def _get_default_embedding() -> Embeddings:
    from ..embedding_service.core import get_embedding_model

    LOGGER.debug("Fetching default embedding model for vector store")
    model = get_embedding_model()
    LOGGER.debug(
        "Default embedding model acquired",
        extra={"model": getattr(model, "model", model.__class__.__name__)},
    )
    return model


def _clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Strip unsupported metadata types before writing to the vector store."""

    cleaned: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, ALLOWED_METADATA_TYPES):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def _calculate_directory_size(path: Path) -> int:
    """Return the total number of bytes consumed by the persistent vector store."""

    if not path.exists():
        return 0

    total = 0
    for entry in path.rglob("*"):
        if not entry.is_file():
            continue
        try:
            total += entry.stat().st_size
        except OSError:
            LOGGER.debug("Skipping file during directory size calculation", extra={"path": str(entry)})
    return total


def synchronize_documents(chunks: Sequence[Any], embedding_model: Optional[Embeddings]) -> VectorStoreSyncResult:
    """Ensure the vector store reflects the supplied chunk collection."""

    settings = cast(AppSettings, get_settings())
    manifest = load_manifest()
    existing_entries = dict(manifest.entries)

    chunk_counts: Dict[str, int] = defaultdict(int)
    file_stats: Dict[str, Dict[str, int]] = {}

    for chunk in chunks:
        metadata = getattr(chunk, "metadata", {}) or {}
        source_path = metadata.get("source_path")
        if not source_path:
            continue
        chunk_counts[source_path] += 1
        path_obj = Path(source_path)
        try:
            stat_result = path_obj.stat()
        except OSError:
            LOGGER.warning(
                "Unable to stat document during vector store sync",
                extra={"source_path": source_path},
            )
            continue
        file_stats[source_path] = {
            "mtime_ns": int(stat_result.st_mtime_ns),
            "size_bytes": stat_result.st_size,
        }

    existing_paths = set(existing_entries.keys())
    current_paths = set(file_stats.keys())
    removed_paths = existing_paths - current_paths

    paths_requiring_sync: List[str] = []
    new_paths: List[str] = []
    updated_paths: List[str] = []

    for path in current_paths:
        desired_entry = {
            "mtime_ns": file_stats[path]["mtime_ns"],
            "size_bytes": file_stats[path]["size_bytes"],
            "chunk_count": chunk_counts.get(path, 0),
        }
        previous_entry = existing_entries.get(path)
        if previous_entry != desired_entry:
            paths_requiring_sync.append(path)
            if previous_entry is None:
                new_paths.append(path)
            else:
                updated_paths.append(path)

    sync_started_at = datetime.now(timezone.utc)

    if not paths_requiring_sync and not removed_paths:
        stored_chunks = sum(entry.get("chunk_count", 0) for entry in manifest.entries.values())
        storage_bytes = _calculate_directory_size(settings.vectorstore_path)
        sync_completed_at = datetime.now(timezone.utc)
        manifest.metadata["last_checked_at"] = sync_completed_at.isoformat()
        manifest.metadata["total_sync_checks"] = manifest.metadata.get("total_sync_checks", 0) + 1
        manifest.metadata.setdefault("document_count", len(manifest.entries))
        manifest.metadata.setdefault("chunk_count", stored_chunks)
        manifest.metadata.setdefault("storage_bytes", storage_bytes)
        save_manifest(manifest)
        LOGGER.debug("Vector store already up to date", extra={"documents_tracked": len(manifest.entries)})
        return VectorStoreSyncResult(
            elapsed_seconds=0.0,
            documents_added=0,
            documents_updated=0,
            documents_removed=0,
            chunks_indexed=0,
            chunks_deleted=0,
            sync_started_at=sync_started_at.isoformat(),
            sync_completed_at=sync_completed_at.isoformat(),
            storage_bytes=storage_bytes,
            tracked_files=len(manifest.entries),
            stored_chunks=stored_chunks,
        )

    try:
        store = get_vectorstore(embedding_model)
    except (RuntimeError, ValueError, OSError) as exc:  # pragma: no cover - backend specific
        LOGGER.exception("Failed to acquire vector store", extra={"error": str(exc)})
        raise

    storage_timer = perf_counter()
    removed_chunk_total = sum(existing_entries.get(path, {}).get("chunk_count", 0) for path in removed_paths)
    replaced_chunk_total = sum(existing_entries.get(path, {}).get("chunk_count", 0) for path in updated_paths)

    try:
        for path in removed_paths:
            store.delete(where={"source_path": path})
            manifest.entries.pop(path, None)

        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []

        if paths_requiring_sync:
            for path in paths_requiring_sync:
                store.delete(where={"source_path": path})

            for idx, chunk in enumerate(chunks):
                metadata = getattr(chunk, "metadata", {}) or {}
                source_path = metadata.get("source_path")
                if not source_path or source_path not in paths_requiring_sync:
                    continue
                texts.append(getattr(chunk, "page_content", ""))
                metadatas.append(_clean_metadata(dict(metadata)))
                chunk_index = metadata.get("chunk_index", idx)
                ids.append(f"{source_path}::chunk_{chunk_index}")

            if texts:
                store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

            for path in paths_requiring_sync:
                manifest.entries[path] = {
                    "mtime_ns": file_stats[path]["mtime_ns"],
                    "size_bytes": file_stats[path]["size_bytes"],
                    "chunk_count": chunk_counts.get(path, 0),
                }

        store.persist()

        elapsed = perf_counter() - storage_timer
        chunk_total = sum(entry.get("chunk_count", 0) for entry in manifest.entries.values())
        storage_bytes = _calculate_directory_size(settings.vectorstore_path)
        sync_completed_at = datetime.now(timezone.utc)

        chunks_indexed = len(texts)
        sync_summary = {
            "documents_added": len(new_paths),
            "documents_updated": len(updated_paths),
            "documents_removed": len(removed_paths),
            "chunks_indexed": chunks_indexed,
            "chunks_deleted": removed_chunk_total + replaced_chunk_total,
            "elapsed_seconds": round(elapsed, 3),
        }

        manifest.metadata.update(
            {
                "last_synced_at": sync_completed_at.isoformat(),
                "last_checked_at": sync_completed_at.isoformat(),
                "document_count": len(manifest.entries),
                "chunk_count": chunk_total,
                "storage_bytes": storage_bytes,
                "last_sync_summary": sync_summary,
                "total_sync_runs": manifest.metadata.get("total_sync_runs", 0) + 1,
                "total_sync_checks": manifest.metadata.get("total_sync_checks", 0) + 1,
            }
        )

        save_manifest(manifest)

        LOGGER.info(
            "Vector store synchronised",
            extra={
                "documents_added": len(new_paths),
                "documents_updated": len(updated_paths),
                "documents_removed": len(removed_paths),
                "chunks_written": sync_summary["chunks_indexed"],
                "elapsed_seconds": round(elapsed, 3),
            },
        )

        return VectorStoreSyncResult(
            elapsed_seconds=elapsed,
            documents_added=len(new_paths),
            documents_updated=len(updated_paths),
            documents_removed=len(removed_paths),
            chunks_indexed=chunks_indexed,
            chunks_deleted=removed_chunk_total + replaced_chunk_total,
            sync_started_at=sync_started_at.isoformat(),
            sync_completed_at=sync_completed_at.isoformat(),
            storage_bytes=storage_bytes,
            tracked_files=len(manifest.entries),
            stored_chunks=chunk_total,
        )
    except (RuntimeError, ValueError, OSError, TypeError) as exc:  # pragma: no cover - backend specific
        LOGGER.exception("Vector store synchronisation failed", extra={"error": str(exc)})
        raise

