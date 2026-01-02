"""Centralised configuration for the AION POC."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingSettings(BaseModel):
    """Configuration for the embedding model."""

    model: str = Field(default="nomic-embed-text", description="Ollama embedding model name")


class LLMSettings(BaseModel):
    """Configuration for the LLM used during augmentation."""

    provider: str = Field(default="ollama", description="LLM provider identifier")
    model: str = Field(default="llama3:8b", description="Default LLM model name")
    available_models: List[str] = Field(default_factory=list, description="Optional list of allowed model names")
    base_url: str = Field(default="http://localhost:11434", description="LLM inference endpoint base URL")
    temperature: float = Field(default=0.2, ge=0.0, le=1.5)
    max_output_tokens: int = Field(default=768, ge=1)
    timeout_seconds: float = Field(default=120.0, ge=1.0, description="LLM request timeout in seconds")


class VectorStoreSettings(BaseModel):
    """Configuration for the persisted Chroma vector store."""

    persist_dir: Path = Field(default=Path("data/db/chroma_store/"))
    collection: str = Field(default="aion_chromadb")


class ChunkingSettings(BaseModel):
    """Configuration for document chunking."""

    method: str = Field(default="recursive")
    chunk_size: int = Field(default=1000, ge=128)
    chunk_overlap: int = Field(default=200, ge=0)


class RetrievalSettings(BaseModel):
    """Configuration for retrieval behaviour."""

    top_k: int = Field(default=4, ge=1, le=10)


class LoggingSettings(BaseModel):
    """Configuration for application logging."""

    level: str = Field(default="DEBUG", description="Root logger level")
    format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        description="Logging formatter string",
    )
    datefmt: str = Field(default="%Y-%m-%dT%H:%M:%S", description="Datetime format for logs")
    log_file: Path | None = Field(default=None, description="Optional log file path")
    log_dir: Path = Field(default=Path("logs"), description="Directory to write log files into")
    log_filename: str = Field(default="aion.log", description="Default filename for log output")
    enable_console: bool = Field(default=False, description="Emit logs to the console")
    enable_file: bool = Field(default=True, description="Emit logs to a rotating file handler")
    max_bytes: int = Field(default=5_000_000, ge=1, description="Max size for rotating file logs")
    backup_count: int = Field(default=5, ge=0, description="Number of rotated log files to keep")
    propagate: bool = Field(default=False, description="Whether to propagate logs to parent loggers")


class AppSettings(BaseSettings):
    """Application level configuration surfaced to the rest of the code base."""

    model_config = SettingsConfigDict(env_prefix="AION_", env_file=".env", env_nested_delimiter="__")

    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3])
    data_root: Path = Field(default=Path("data"))
    corpus_subdirs: List[str] = Field(
        default_factory=lambda: [
            "ocpp_spec",
            "sample_logs",
            "sample_jira",
            "sample_confluence",
            "sample_release_notes",
            "sample_git",
        ]
    )

    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    vectorstore: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @property
    def absolute_data_dirs(self) -> List[Path]:
        """Return all data directories that should be ingested."""

        base = self.project_root / self.data_root
        return [base / subdir for subdir in self.corpus_subdirs]

    @property
    def vectorstore_path(self) -> Path:
        """Return the absolute path to the vector store directory."""

        persist = self.vectorstore.persist_dir
        if persist.is_absolute():
            return persist
        return (self.project_root / persist).resolve()


@lru_cache()
def get_settings() -> AppSettings:
    """Return a cached settings object."""

    return AppSettings()