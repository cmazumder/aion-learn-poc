# AION Project Structure - Complete Skeleton

This document outlines the complete modular directory structure for AION.

## Complete Directory Tree

```
aion-poc/
├── ARCHITECTURE.md                    # System architecture documentation
├── README.md                          # Project overview
├── pyproject.toml                     # Python project configuration
├── .env                               # Environment variables
├── .gitignore                         # Git ignore patterns
│
├── data/                              # Data storage
│   ├── ocpp_spec/                     # OCPP specifications
│   ├── sample_logs/                   # Sample log files
│   ├── sample_jira/                   # Sample JIRA data
│   └── vector_db/                     # Vector database storage
│
├── notebooks/                         # Jupyter notebooks for exploration
│   ├── 01-initial-rag-poc.ipynb
│   ├── 02-semantic-chunking.ipynb
│   └── 03-layered-retrieval.ipynb
│
├── src/aion_poc/                      # Main source code
│   ├── __init__.py
│   ├── main.py                        # FastAPI application entry
│   ├── config.py                      # Configuration management
│   │
│   ├── ingestion/                     # Data Ingestion Layer
│   │   ├── __init__.py
│   │   ├── base.py                    # Base ingester interface
│   │   ├── parsers/                   # Document parsers
│   │   │   ├── __init__.py
│   │   │   ├── pdf_parser.py          # PDF with image extraction
│   │   │   ├── docx_parser.py         # Word documents
│   │   │   ├── image_parser.py        # Images with OCR
│   │   │   ├── html_parser.py         # HTML/Web pages
│   │   │   └── markdown_parser.py     # Markdown files
│   │   └── connectors/                # External API connectors
│   │       ├── __init__.py
│   │       ├── confluence_connector.py # Confluence integration
│   │       ├── jira_connector.py       # JIRA integration
│   │       ├── github_connector.py     # GitHub PR/Issues
│   │       └── log_stream_connector.py # Real-time logs
│   │
│   ├── processing/                    # Document Processing Layer
│   │   ├── __init__.py
│   │   ├── chunking/                  # Chunking strategies
│   │   │   ├── __init__.py            # Base chunker + Chunk model
│   │   │   ├── semantic_chunker.py    # Semantic similarity-based
│   │   │   ├── hierarchical_chunker.py # Document hierarchy aware
│   │   │   └── sliding_window.py      # Sliding window approach
│   │   ├── structure.py               # Document structure analysis
│   │   └── normalizer.py              # Content normalization
│   │
│   ├── embedding/                     # Embedding Layer
│   │   ├── __init__.py
│   │   ├── base.py                    # Base embedder interface
│   │   ├── sentence_transformer.py    # Sentence Transformers
│   │   ├── openai_embedder.py         # OpenAI embeddings
│   │   ├── ollama_embedder.py         # Local Ollama embeddings
│   │   ├── cache.py                   # Embedding cache
│   │   └── batch_processor.py         # Batch embedding processing
│   │
│   ├── vector_store/                  # Vector Store Layer
│   │   ├── __init__.py
│   │   ├── base.py                    # Base vector store interface
│   │   ├── chroma_store.py            # ChromaDB implementation
│   │   ├── faiss_store.py             # FAISS implementation
│   │   ├── pinecone_store.py          # Pinecone cloud store
│   │   ├── indexing/                  # Indexing strategies
│   │   │   ├── __init__.py
│   │   │   ├── hierarchical_index.py  # Multi-level indexing
│   │   │   └── metadata_index.py      # Metadata filtering
│   │   └── search.py                  # Search utilities
│   │
│   ├── retrieval/                     # Retrieval Layer
│   │   ├── __init__.py
│   │   ├── base.py                    # Base retriever interface
│   │   ├── layered/                   # Layered retrieval strategies
│   │   │   ├── __init__.py
│   │   │   ├── document_retriever.py  # Document-level retrieval
│   │   │   ├── section_retriever.py   # Section-level retrieval
│   │   │   └── chunk_retriever.py     # Chunk-level retrieval
│   │   ├── hybrid_search.py           # Hybrid (semantic + keyword)
│   │   ├── reranker.py                # Re-ranking algorithms
│   │   ├── query_expansion.py         # Query expansion techniques
│   │   └── fusion.py                  # Retrieval fusion strategies
│   │
│   ├── llm/                           # LLM Integration Layer
│   │   ├── __init__.py
│   │   ├── base.py                    # Base LLM interface
│   │   ├── ollama_llm.py              # Ollama integration
│   │   ├── openai_llm.py              # OpenAI integration
│   │   ├── anthropic_llm.py           # Anthropic Claude
│   │   ├── prompts/                   # Prompt templates
│   │   │   ├── __init__.py
│   │   │   ├── rag_prompts.py         # RAG-specific prompts
│   │   │   ├── diagnostic_prompts.py  # Diagnostic prompts
│   │   │   └── rca_prompts.py         # Root cause analysis prompts
│   │   └── streaming.py               # Streaming response handler
│   │
│   ├── pipeline/                      # Pipeline Orchestration Layer
│   │   ├── __init__.py
│   │   ├── base.py                    # Base pipeline interface
│   │   ├── ingestion_pipeline.py      # End-to-end ingestion
│   │   ├── query_pipeline.py          # Query processing pipeline
│   │   ├── rag_pipeline.py            # Complete RAG pipeline
│   │   └── evaluation_pipeline.py     # Evaluation and metrics
│   │
│   ├── core/                          # Core Utilities
│   │   ├── __init__.py
│   │   ├── logging.py                 # Logging configuration
│   │   ├── metrics.py                 # Metrics and monitoring
│   │   ├── cache.py                   # Caching utilities
│   │   └── exceptions.py              # Custom exceptions
│   │
│   └── api/                           # API Layer
│       ├── __init__.py
│       ├── routes/                    # API routes
│       │   ├── __init__.py
│       │   ├── health.py              # Health check endpoints
│       │   ├── ingest.py              # Ingestion endpoints
│       │   ├── query.py               # Query endpoints
│       │   └── admin.py               # Admin endpoints
│       ├── models/                    # Pydantic models
│       │   ├── __init__.py
│       │   ├── request.py             # Request models
│       │   └── response.py            # Response models
│       ├── middleware/                # API middleware
│       │   ├── __init__.py
│       │   ├── auth.py                # Authentication
│       │   ├── rate_limit.py          # Rate limiting
│       │   └── logging.py             # Request logging
│       └── websocket.py               # WebSocket handlers
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── conftest.py                    # Pytest configuration
│   ├── unit/                          # Unit tests
│   │   ├── test_parsers.py
│   │   ├── test_chunking.py
│   │   ├── test_embedding.py
│   │   └── test_retrieval.py
│   ├── integration/                   # Integration tests
│   │   ├── test_ingestion_pipeline.py
│   │   └── test_rag_pipeline.py
│   └── e2e/                           # End-to-end tests
│       └── test_api.py
│
└── scripts/                           # Utility scripts
    ├── setup_db.py                    # Database initialization
    ├── ingest_data.py                 # Data ingestion script
    └── evaluate_rag.py                # RAG evaluation script
```

## Key Module Responsibilities

### 1. Ingestion (`ingestion/`)

- **Parsers**: Extract content from various file formats
- **Connectors**: Connect to external APIs (Confluence, JIRA, GitHub)
- **Features**: Multi-format support, image extraction, OCR, metadata preservation

### 2. Processing (`processing/`)

- **Semantic Chunking**: Context-aware text splitting
- **Hierarchical Chunking**: Structure-preserving chunking
- **Normalization**: Content cleanup and standardization

### 3. Embedding (`embedding/`)

- **Multi-Model Support**: Sentence Transformers, OpenAI, Ollama
- **Caching**: Prevent redundant embedding generation
- **Batch Processing**: Efficient bulk embedding

### 4. Vector Store (`vector_store/`)

- **Multi-Backend**: ChromaDB, FAISS, Pinecone
- **Hierarchical Indexing**: Multi-level document representation
- **Metadata Filtering**: Efficient filtered search

### 5. Retrieval (`retrieval/`)

- **Layered Retrieval**: Document → Section → Chunk levels
- **Hybrid Search**: Combine semantic and keyword search
- **Re-ranking**: Improve result relevance
- **Query Expansion**: Enhance query understanding
- **Fusion**: Combine multiple retrieval strategies

### 6. LLM (`llm/`)

- **Multi-Provider**: Ollama, OpenAI, Anthropic
- **Prompt Engineering**: Specialized prompts for different tasks
- **Streaming**: Real-time response streaming

### 7. Pipeline (`pipeline/`)

- **Ingestion Pipeline**: Source → Parse → Chunk → Embed → Index
- **Query Pipeline**: Query → Retrieve → Re-rank → Generate
- **RAG Pipeline**: Complete end-to-end RAG flow

### 8. API (`api/`)

- **REST Endpoints**: Standard HTTP API
- **WebSocket**: Real-time streaming responses
- **Authentication**: Secure access control
- **Rate Limiting**: Resource protection

## Data Flow

### Ingestion Flow

```
External Source → Connector/Parser → Document
    ↓
Chunking Strategy → Chunks
    ↓
Embedding Model → Embedded Chunks
    ↓
Vector Store → Indexed Documents
```

### Query Flow

```
User Query → Query Processor
    ↓
Layered Retrieval (Document/Section/Chunk)
    ↓
Re-ranking & Fusion
    ↓
Context Builder → LLM
    ↓
Response Generator → User
```

## Technology Stack

- **Web Framework**: FastAPI
- **Async**: asyncio, aiohttp
- **Document Processing**: unstructured, PyPDF2, python-docx, pytesseract
- **Embeddings**: sentence-transformers, openai, ollama
- **Vector Stores**: chromadb, faiss-cpu, pinecone-client
- **LLM**: langchain, ollama, openai, anthropic
- **Testing**: pytest, pytest-asyncio
- **Monitoring**: prometheus-client
- **Task Queue**: celery (for async ingestion)

## Configuration

Example `config.py`:

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Vector Store
    vector_store_type: str = "chroma"  # chroma, faiss, pinecone
    chroma_persist_directory: str = "./data/vector_db"
    
    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    
    # LLM
    llm_provider: str = "ollama"  # ollama, openai, anthropic
    llm_model: str = "llama3:8b"
    
    # Chunking
    chunk_strategy: str = "semantic"  # semantic, hierarchical, sliding
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # Retrieval
    retrieval_strategy: str = "layered"  # layered, hybrid, fusion
    top_k: int = 5
    
    # External APIs
    confluence_url: str = ""
    jira_url: str = ""
    github_token: str = ""
    
    class Config:
        env_file = ".env"
```

## Next Steps for Implementation

1. **Phase 1**: Core infrastructure

   - Base classes and interfaces
   - Configuration management
   - Logging and metrics

1. **Phase 2**: Ingestion

   - Implement parsers (PDF, DOCX, images)
   - Implement connectors (Confluence, JIRA, GitHub)

1. **Phase 3**: Processing & Embedding

   - Semantic chunking implementation
   - Embedding model integration
   - Caching layer

1. **Phase 4**: Storage & Retrieval

   - Vector store implementations
   - Layered retrieval strategies
   - Re-ranking algorithms

1. **Phase 5**: LLM & API

   - LLM provider integrations
   - API endpoints
   - WebSocket streaming

1. **Phase 6**: Pipelines & Evaluation

   - End-to-end pipelines
   - Evaluation metrics
   - Performance optimization

1. **Phase 7**: Microservices

   - Service separation
   - Inter-service communication
   - Container deployment (Docker/Kubernetes)
