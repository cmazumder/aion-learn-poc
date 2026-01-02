"""Utilities for loading the synthetic AION corpus into LangChain documents."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..config.settings import get_settings
from ..logging_config import configure_logging

CSVLoader: Optional[Any] = None
Docx2txtLoader: Optional[Any] = None
PyPDFLoader: Optional[Any] = None
UnstructuredExcelLoader: Optional[Any] = None

try:  # Optional heavy dependencies
    from langchain_community.document_loaders import CSVLoader, Docx2txtLoader, PyPDFLoader  # type: ignore[import-not-found, import-untyped]
    from langchain_community.document_loaders.excel import UnstructuredExcelLoader  # type: ignore[import-not-found, import-untyped]
except ImportError:  # pragma: no cover - optional dependency path
    CSVLoader = Docx2txtLoader = PyPDFLoader = UnstructuredExcelLoader = None  # type: ignore[assignment]

Document = import_module("langchain_core.documents").Document  # type: ignore[attr-defined]

configure_logging()
logger = logging.getLogger(__name__)


@dataclass
class DirectoryIngestionSummary:
    directory: str
    documents_added: int
    files_processed: int
    files_skipped: int
    duration_seconds: float


@dataclass
class CorpusLoadReport:
    documents_loaded: int
    files_processed: int
    files_skipped: int
    missing_directories: List[str]
    directory_summaries: List[DirectoryIngestionSummary]
    extra_documents: int = 0

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".log",
    ".json",
}

LoaderEntry = Tuple[Any, Dict[str, Any]]
LOADER_FACTORIES: Dict[str, LoaderEntry] = {}

if PyPDFLoader is not None:
    LOADER_FACTORIES[".pdf"] = (PyPDFLoader, {})
    SUPPORTED_EXTENSIONS.add(".pdf")
if Docx2txtLoader is not None:
    LOADER_FACTORIES[".docx"] = (Docx2txtLoader, {})
    SUPPORTED_EXTENSIONS.add(".docx")
if CSVLoader is not None:
    LOADER_FACTORIES[".csv"] = (CSVLoader, {})
    SUPPORTED_EXTENSIONS.add(".csv")
if UnstructuredExcelLoader is not None:
    for ext in (".xls", ".xlsx"):
        LOADER_FACTORIES[ext] = (UnstructuredExcelLoader, {})
        SUPPORTED_EXTENSIONS.add(ext)

SOURCE_TYPE_MAP = {
    "ocpp_spec": "spec",
    "sample_logs": "log",
    "sample_jira": "jira",
    "sample_confluence": "kb",
    "sample_release_notes": "release_notes",
    "sample_git": "git",
}


def _infer_incident_id(file_path: Path) -> str | None:
    """Attempt to infer an incident identifier from the file name."""

    stem = file_path.stem.lower()
    if "incident" in stem:
        parts = stem.split("_")
        for part in parts:
            if part.startswith("incident"):
                return part
    if stem.startswith("demo"):
        return stem
    return None


def _load_text(path: Path) -> str:
    """Read a UTF-8 text file, falling back to latin-1 if required."""

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("Fallback to latin-1 decoding", extra={"path": str(path)})
        return path.read_text(encoding="latin-1")


def _load_json_as_text(path: Path) -> str:
    """Flatten JSON into a readable text representation."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning(
            "Failed to parse JSON document",
            extra={"path": str(path), "error": str(exc)},
        )
        return path.read_text(encoding="utf-8", errors="ignore")

    def _flatten(obj: object, prefix: str = "") -> Iterable[str]:
        if isinstance(obj, dict):
            for key, value in obj.items():
                yield from _flatten(value, f"{prefix}{key}.")
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                yield from _flatten(value, f"{prefix}{idx}.")
        else:
            yield f"{prefix.rstrip('.')}: {obj}"

    return "\n".join(_flatten(data))


def _build_metadata(path: Path) -> dict:
    """Generate consistent metadata for the AION corpus."""

    parent = path.parent.name
    source_type = SOURCE_TYPE_MAP.get(parent, "reference")
    incident_id = _infer_incident_id(path)
    return {
        "source_path": str(path),
        "source_dir": parent,
        "source_file": path.name,
        "source_type": source_type,
        "incident_id": incident_id,
    }


def _augment_documents(docs: List[Any], path: Path) -> List[Any]:
    """Attach standard metadata to loader-provided documents."""

    if not docs:
        return []

    base_metadata = _build_metadata(path)
    enriched: List[Any] = []
    for index, doc in enumerate(docs):
        merged_metadata = dict(base_metadata)
        existing_metadata = getattr(doc, "metadata", {}) or {}
        merged_metadata.update(existing_metadata)
        merged_metadata.setdefault("loader_index", index)
        enriched.append(
            Document(
                page_content=getattr(doc, "page_content", ""),
                metadata=merged_metadata,
            )
        )
    return enriched


def _documents_from_file(path: Path) -> List[Any]:
    """Create LangChain documents from a file on disk."""

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        logger.debug("Skipping unsupported file type", extra={"path": str(path)})
        return []

    if suffix == ".json":
        content = _load_json_as_text(path)
        if not content.strip():
            logger.debug("Skipping empty JSON document", extra={"path": str(path)})
            return []
        metadata = _build_metadata(path)
        return [Document(page_content=content, metadata=metadata)]

    if suffix in {".txt", ".md", ".log"}:
        content = _load_text(path)
        if not content.strip():
            logger.debug("Skipping empty text file", extra={"path": str(path)})
            return []
        metadata = _build_metadata(path)
        return [Document(page_content=content, metadata=metadata)]

    loader_entry = LOADER_FACTORIES.get(suffix)
    if loader_entry is None:
        logger.warning(
            "No loader registered for supported extension",
            extra={"path": str(path), "extension": suffix},
        )
        return []

    loader_cls, loader_kwargs = loader_entry
    try:
        loader = loader_cls(str(path), **loader_kwargs)
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        logger.exception(
            "Failed to initialise document loader",
            extra={"path": str(path), "extension": suffix, "error": str(exc)},
        )
        return []

    try:
        loaded_docs = loader.load()
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as exc:
        logger.exception(
            "Document loader failed to read file",
            extra={"path": str(path), "extension": suffix, "error": str(exc)},
        )
        return []

    if not loaded_docs:
        logger.debug("Loader returned no documents", extra={"path": str(path)})
        return []

    return _augment_documents(loaded_docs, path)


def load_corpus() -> Tuple[List[Any], CorpusLoadReport]:
    """Load every supported document in the configured corpus directories."""

    settings = get_settings()
    documents: List[Any] = []
    directory_summaries: List[DirectoryIngestionSummary] = []
    missing_directories: List[str] = []
    total_files_processed = 0
    total_files_skipped = 0

    directories = [str(path) for path in settings.absolute_data_dirs]
    logger.info("Scanning corpus directories", extra={"directories": directories})

    for data_dir in settings.absolute_data_dirs:
        dir_start = time.perf_counter()
        if not data_dir.exists():
            missing_directories.append(str(data_dir))
            logger.warning("Data directory missing", extra={"path": str(data_dir)})
            continue

        docs_added = 0
        files_processed = 0
        files_skipped = 0

        logger.debug(
            "Processing data directory",
            extra={"path": str(data_dir)},
        )
        for path in sorted(data_dir.rglob("*")):
            if not path.is_file():
                continue
            files_processed += 1
            docs = _documents_from_file(path)
            if docs:
                documents.extend(docs)
                docs_added += len(docs)
            else:
                files_skipped += 1

        dir_duration = time.perf_counter() - dir_start
        directory_summaries.append(
            DirectoryIngestionSummary(
                directory=data_dir.name,
                documents_added=docs_added,
                files_processed=files_processed,
                files_skipped=files_skipped,
                duration_seconds=round(dir_duration, 3),
            )
        )

        total_files_processed += files_processed
        total_files_skipped += files_skipped

        logger.info(
            "Processed directory",
            extra={
                "directory": data_dir.name,
                "documents_added": docs_added,
                "files_processed": files_processed,
                "files_skipped": files_skipped,
                "duration_seconds": round(dir_duration, 3),
            },
        )

    logger.info(
        "Loaded documents from corpus",
        extra={"total_documents": len(documents), "files_processed": total_files_processed},
    )

    report = CorpusLoadReport(
        documents_loaded=len(documents),
        files_processed=total_files_processed,
        files_skipped=total_files_skipped,
        missing_directories=missing_directories,
        directory_summaries=directory_summaries,
    )

    return documents, report


def load_documents_from_sources(sources: Sequence[Dict[str, Any]]) -> List[Any]:
    """Generate LangChain documents from CLI ingestion descriptors."""

    documents: List[Any] = []
    for source in sources:
        if source.get("type") != "file":
            logger.warning("Unsupported source type", extra={"source": source})
            continue

        raw_path = source.get("source")
        if raw_path is None:
            logger.warning("Source entry missing path", extra={"source": source})
            continue

        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            logger.warning("Source path not found", extra={"path": raw_path})
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1", errors="ignore")

        metadata = {
            "source_path": str(path.resolve()),
            "source_dir": path.parent.name,
            "source_file": path.name,
            "source_type": source.get("source_type", "cli_sample"),
        }

        documents.append(Document(page_content=content, metadata=metadata))

    if documents:
        logger.debug(
            "Prepared documents from sources",
            extra={"count": len(documents)},
        )
    else:
        logger.debug("No documents prepared from sources", extra={"source_count": len(sources)})

    return documents
