
"""
Backend integration for AION RAG Streamlit UI.
Provides synchronous wrappers for pipeline operations and system statistics.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from langchain_core.documents import Document
from aion_poc.config.settings import get_settings
from aion_poc.shared.pipeline import get_pipeline, initialize_pipeline, DemoPipeline
from dataclasses import asdict
import logging
import collections

_pipeline: Optional[DemoPipeline] = None


def get_or_init_pipeline() -> DemoPipeline:
    """
    Initialize and return the singleton pipeline instance for the UI.
    Returns:
        DemoPipeline: The initialized pipeline object.
    """
    global _pipeline
    if _pipeline is None:
        initialize_pipeline()
        _pipeline = get_pipeline()
    return _pipeline

def get_sample_queries() -> list[str]:
    """Return sample queries for UI suggestion."""
    return [
        "What should I do if the charging station is not responding?",
        "How do I use an RFID card to start charging?",
        "What does error code E002 mean?",
        "What is the maintenance schedule for charging stations?",
        "How do I install a new charging station?",
        "What are the electrical requirements for installation?"
    ]

def get_config() -> dict:
    """Return pipeline config as dict for UI."""
    pipeline = get_or_init_pipeline()
    config = getattr(pipeline, "settings", None)
    if config is not None:
        return config.model_dump()
    return {}

def sync_ingest_documents(file_paths: List[str]) -> Dict[str, Any]:
    """
    Synchronously ingest documents from provided file paths using the pipeline.
    Args:
        file_paths (list[str]): List of file paths to ingest.
    Returns:
        dict: Ingestion statistics and results.
    """
    try:
        pipeline = get_or_init_pipeline()
        async def ingest():
            sources = [{"type": "file", "source": path} for path in file_paths]
            stats = await pipeline.ingest_documents(sources)
            if hasattr(stats, "__dataclass_fields__"):
                return asdict(stats)
            elif isinstance(stats, dict):
                return stats
            elif hasattr(stats, "__dict__"):
                return vars(stats)
            else:
                return {"result": stats}
        result = asyncio.run(ingest())
        # Ensure all keys are str for type safety
        if any(isinstance(k, bytes) for k in result.keys()):
            result = {k.decode() if isinstance(k, bytes) else k: v for k, v in result.items()}
        return result
    except Exception as e:
        logging.error("Ingestion failed: %s", e)
        return {"error": str(e)}

async def get_system_stats() -> Dict[str, Any]:
    """
    Fetch system statistics from the pipeline.
    Returns:
        dict: Dictionary of system statistics.
    """
    pipeline = get_or_init_pipeline()
    return await pipeline.get_system_stats()

async def query_knowledge_base(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Query the knowledge base using the pipeline.
    Args:
        query (str): The user query string.
        top_k (int): Number of top results to return.
    Returns:
        Dict[str, Any]: The query result as a dict for UI.
    """
    pipeline = get_or_init_pipeline()
    response = await pipeline.query(query=query, strategy="vectorstore", top_k=top_k)
    # Use asdict if response is a dataclass, else fallback to dict
    if hasattr(response, "__dataclass_fields__"):
        return asdict(response)
    answer = getattr(response, "answer", "No answer")
    sources = getattr(response, "sources", [])
    metadata = getattr(response, "metadata", {})
    return {"answer": answer, "sources": sources, "metadata": metadata}

async def health_check() -> Dict[str, Any]:
    """
    Perform a health check on the pipeline.
    Returns:
        dict: Health status of the pipeline and components.
    """
    pipeline = get_or_init_pipeline()
    return await pipeline.health_check()

def sync_get_system_stats() -> Dict[str, Any]:
    """
    Synchronous wrapper for get_system_stats (for Streamlit compatibility).
    Returns:
        dict: System statistics, vector store, corpus profile, corpus report, query metrics, recent queries, alerts, configuration.
    """
    try:
        stats = asyncio.run(get_system_stats())
        # Unpack all sections for UI
        return {
            "pipeline_stats": stats.get("pipeline_stats", {}),
            "vector_store": stats.get("vector_store", {}),
            "corpus_profile": stats.get("corpus_profile", {}),
            "corpus_report": stats.get("corpus_report", {}),
            "query_metrics": stats.get("query_metrics", {}),
            "recent_queries": stats.get("recent_queries", []),
            "alerts": stats.get("alerts", []),
            "configuration": stats.get("configuration", {}),
        }
    except Exception as e:
        logging.error("System stats failed: %s", e)
        return {"error": str(e)}

def sync_query_knowledge_base(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Synchronous wrapper for query_knowledge_base (for Streamlit compatibility).
    Args:
        query (str): The user query string.
        top_k (int): Number of top results to return.
    Returns:
        Dict[str, Any]: The query result as a dict for UI.
    """
    try:
        return asyncio.run(query_knowledge_base(query, top_k))
    except Exception as e:
        logging.error("Query failed: %s", e)
        return {"answer": "Error", "sources": [], "metadata": {"error": str(e)}}

def sync_query_with_attachment(query: str, file_path: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Synchronous wrapper for querying with a single file attachment.
    Args:
        query (str): The user query string.
        file_path (str): Path to the uploaded file.
        top_k (int): Number of top results to return.
    Returns:
        Dict[str, Any]: The query result as a dict for UI.
    """
    try:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="ignore")
        doc = Document(
            page_content=content,
            metadata={"source_file": path.name, "source_path": str(path)},
        )

        async def query_async():
            pipeline = get_or_init_pipeline()
            response = await pipeline.query_with_documents(query=query, documents=[doc], top_k=top_k)
            return asdict(response)

        return asyncio.run(query_async())
    except Exception as e:
        logging.error("Query with attachment failed: %s", e)
        return {"answer": "Error processing attachment", "sources": [], "metadata": {"error": str(e)}}

def sync_health_check() -> Dict[str, Any]:
    """
    Synchronous wrapper for health_check (for Streamlit compatibility).
    Returns:
        dict: Health status of the pipeline and components, with overall and component breakdown.
    """
    try:
        return asyncio.run(health_check())
    except Exception as e:
        logging.error("Health check failed: %s", e)
        return {"error": str(e)}

def get_log_content(lines: int = 200) -> str:
    """
    Reads the last N lines from the configured log file.

    Args:
        lines (int): The number of recent lines to retrieve.

    Returns:
        str: The content of the last lines of the log file, or an error message.
    """
    try:
        settings = get_settings()
        log_file = settings.project_root / settings.logging.log_dir / settings.logging.log_filename

        if not log_file.exists():
            return f"Log file not found at: {log_file}"

        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            return "".join(collections.deque(f, maxlen=lines))
    except Exception as e:
        logging.error("Failed to read log file: %s", e)
        return f"Error reading log file: {e}"
