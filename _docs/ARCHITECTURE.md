# AION Architecture - Modular RAG Framework

## Overview

AION (AI-driven Observability and Network Intelligence) is a sophisticated RAG system designed for EV charging station diagnostics with advanced semantic understanding and multi-layered retrieval.

## Core Principles

### 1. Semantic Chunking

- Context-aware text splitting
- Maintains semantic boundaries
- Preserves document structure and relationships

### 2. Document Embedding

- Multi-model embedding support (Sentence Transformers, etc.)
- Specialized embeddings for different document types
- Embedding caching and versioning

### 3. Vector Indexing

- Hierarchical indexing strategies
- Multi-index support (FAISS, Chroma, Pinecone)
- Metadata-rich indexing for filtering

### 4. Layered Retrieval

- Document-level retrieval
- Section-level retrieval
- Chunk-level retrieval
- Hybrid search (semantic + keyword)
- Re-ranking and fusion strategies

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway Layer                        │
│            (FastAPI - REST & WebSocket)                      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                        │
│     (RAG Pipeline, Query Processing, Response Generation)   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌──────▼──────┐
│   Ingestion    │   │    Retrieval    │   │     LLM     │
│    Service     │   │     Service     │   │   Service   │
└───────┬────────┘   └────────┬────────┘   └──────┬──────┘
        │                     │                     │
┌───────▼────────────────────▼─────────────────────▼──────┐
│              Core Services Layer                         │
│  - Document Processing  - Embedding  - Vector Store      │
│  - Chunking Strategies  - Metadata  - Cache              │
└──────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                   Data Sources Layer                     │
│  PDF, Word, Confluence, JIRA, GitHub, Logs, Code, etc.  │
└─────────────────────────────────────────────────────────┘
```

## Module Breakdown

### 1. Data Ingestion (`ingestion/`)

- Multi-format parsers (PDF, DOCX, images, etc.)
- Source connectors (Confluence, JIRA, GitHub)
- Image extraction and OCR
- Metadata extraction

### 2. Document Processing (`processing/`)

- Semantic chunking strategies
- Document structure analysis
- Content normalization
- Language detection

### 3. Embedding (`embedding/`)

- Multiple embedding models
- Embedding caching
- Batch processing
- Model versioning

### 4. Vector Store (`vector_store/`)

- Multi-backend support
- Hierarchical indexing
- Metadata filtering
- Similarity search

### 5. Retrieval (`retrieval/`)

- Layered retrieval strategies
- Hybrid search (semantic + keyword)
- Re-ranking algorithms
- Query expansion
- Retrieval fusion

### 6. LLM Integration (`llm/`)

- Multi-provider support (OpenAI, Anthropic, Ollama)
- Prompt templates
- Response generation
- Streaming support

### 7. Pipeline (`pipeline/`)

- End-to-end RAG orchestration
- Ingestion pipelines
- Query pipelines
- Evaluation pipelines

### 8. API (`api/`)

- REST endpoints
- WebSocket for streaming
- Authentication & authorization
- Rate limiting

## Data Flow

### Ingestion Flow

```text
Source → Parser → Chunker → Embedder → Vector Store
         ↓         ↓          ↓
      Metadata  Structure  Cache
```

### Query Flow

```text
User Query → Query Processor → Multi-Layer Retrieval → Re-ranker
                                     ↓
                              LLM Context Builder
                                     ↓
                              Response Generator → User
```

## Microservice Architecture (Future)

Each major module can be deployed as independent microservices:

1. **Ingestion Service** - Handle document ingestion
1. **Embedding Service** - Generate embeddings
1. **Retrieval Service** - Handle search queries
1. **LLM Service** - Generate responses
1. **API Gateway** - Route requests

## Technology Stack

- **Framework**: FastAPI, LangChain
- **Embeddings**: Sentence Transformers, TBD
- **Vector Stores**: ChromaDB, FAISS, Pinecone
- **LLM**: Ollama, TBD
- **Processing**: Unstructured, PyPDF, python-docx
- **Async**: asyncio, celery
- **Monitoring**: Prometheus, Grafana
