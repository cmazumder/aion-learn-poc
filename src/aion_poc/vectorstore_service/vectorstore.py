"""
Vector Store Module - Implements "Vector Indexing" layer.

This module handles the "Vector Indexing" layer from Google Gemini's approach,
providing efficient storage and retrieval of document embeddings.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict
import json


class VectorStore(ABC):
    """Base class for vector storage backends."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collection_name = config.get("collection_name", "aion_docs")
    
    @abstractmethod
    async def add_chunks(self, chunks: List, embeddings: List[List[float]]):
        """Store chunks with their embeddings."""
        pass
    
    @abstractmethod
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple]:
        """Search for similar chunks."""
        pass
    
    @abstractmethod
    async def delete_by_document_id(self, document_id: str):
        """Delete all chunks from a document."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        pass


class ChromaDBVectorStore(VectorStore):
    """
    ChromaDB implementation - Primary choice for local development.
    Provides persistent, embedded vector database.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.persist_directory = config.get("persist_directory", "./data/vectorstore")
        self.distance_metric = config.get("distance_metric", "cosine")
        self.client = None
        self.collection = None
    
    async def _ensure_initialized(self):
        """Lazy initialization of ChromaDB client."""
        if self.client is None:
            # TODO: Import and initialize ChromaDB
            # import chromadb
            # self.client = chromadb.PersistentClient(path=self.persist_directory)
            # self.collection = self.client.get_or_create_collection(
            #     name=self.collection_name,
            #     metadata={"hnsw:space": self.distance_metric}
            # )
            print(f"ChromaDB initialized at {self.persist_directory}")
            self.client = "mock_client"
            self.collection = "mock_collection"
    
    async def add_chunks(self, chunks: List, embeddings: List[List[float]]):
        """Store chunks with embeddings in ChromaDB."""
        await self._ensure_initialized()
        
        # Prepare data for ChromaDB
        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [self._prepare_metadata(chunk) for chunk in chunks]
        
        # TODO: Add to ChromaDB
        # self.collection.add(
        #     ids=ids,
        #     embeddings=embeddings,
        #     documents=documents,
        #     metadatas=metadatas
        # )
        
        print(f"Added {len(chunks)} chunks to ChromaDB")
    
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple]:
        """Search for similar chunks in ChromaDB."""
        await self._ensure_initialized()
        
        # TODO: Implement actual search
        # results = self.collection.query(
        #     query_embeddings=[query_embedding],
        #     n_results=top_k,
        #     where=filter_dict
        # )
        # 
        # return [
        #     (
        #         results["documents"][0][i],
        #         results["metadatas"][0][i], 
        #         results["distances"][0][i]
        #     )
        #     for i in range(len(results["documents"][0]))
        # ]
        
        # Mock results for skeleton
        return [
            ("Mock document content", {"document_id": "doc1", "chunk_index": 0}, 0.1),
            ("Another mock content", {"document_id": "doc2", "chunk_index": 1}, 0.2)
        ][:top_k]
    
    async def delete_by_document_id(self, document_id: str):
        """Delete all chunks from a document."""
        await self._ensure_initialized()
        
        # TODO: Implement deletion
        # self.collection.delete(where={"document_id": document_id})
        print(f"Deleted chunks for document: {document_id}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get ChromaDB statistics."""
        await self._ensure_initialized()
        
        # TODO: Get actual stats
        # count = self.collection.count()
        # return {
        #     "total_chunks": count,
        #     "collection_name": self.collection_name,
        #     "distance_metric": self.distance_metric
        # }
        
        return {
            "total_chunks": 0,
            "collection_name": self.collection_name,
            "distance_metric": self.distance_metric
        }
    
    def _prepare_metadata(self, chunk) -> Dict[str, Any]:
        """Prepare chunk metadata for ChromaDB storage."""
        metadata = chunk.metadata.copy()
        metadata.update({
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "content_length": len(chunk.content)
        })
        
        # ChromaDB metadata must be JSON serializable
        return {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))}


class FAISSVectorStore(VectorStore):
    """
    FAISS implementation - For high-performance similarity search.
    Good for larger datasets and production use.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.index_path = config.get("index_path", "./data/vectorstore/faiss_index")
        self.embedding_dim = config.get("embedding_dim", 384)
        self.index = None
        self.chunk_metadata = {}  # Store metadata separately
    
    async def _ensure_initialized(self):
        """Initialize FAISS index."""
        if self.index is None:
            # TODO: Import and initialize FAISS
            # import faiss
            # self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product (cosine)
            print(f"FAISS index initialized with dimension {self.embedding_dim}")
            self.index = "mock_faiss_index"
    
    async def add_chunks(self, chunks: List, embeddings: List[List[float]]):
        """Store chunks and embeddings in FAISS."""
        await self._ensure_initialized()
        
        # TODO: Add embeddings to FAISS
        # import numpy as np
        # embeddings_array = np.array(embeddings, dtype=np.float32)
        # self.index.add(embeddings_array)
        
        # Store metadata separately
        start_idx = len(self.chunk_metadata)
        for i, chunk in enumerate(chunks):
            self.chunk_metadata[start_idx + i] = {
                "chunk": chunk,
                "content": chunk.content,
                "metadata": chunk.metadata
            }
        
        print(f"Added {len(chunks)} chunks to FAISS index")
    
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple]:
        """Search FAISS index for similar chunks."""
        await self._ensure_initialized()
        
        # TODO: Implement actual search
        # import numpy as np
        # query_vector = np.array([query_embedding], dtype=np.float32)
        # scores, indices = self.index.search(query_vector, top_k)
        # 
        # results = []
        # for i, idx in enumerate(indices[0]):
        #     if idx in self.chunk_metadata:
        #         chunk_data = self.chunk_metadata[idx]
        #         if self._matches_filter(chunk_data["metadata"], filter_dict):
        #             results.append((
        #                 chunk_data["content"],
        #                 chunk_data["metadata"],
        #                 float(scores[0][i])
        #             ))
        # 
        # return results
        
        # Mock results
        return [
            ("Mock FAISS content", {"document_id": "doc1"}, 0.9),
            ("Another FAISS result", {"document_id": "doc2"}, 0.8)
        ][:top_k]
    
    async def delete_by_document_id(self, document_id: str):
        """Delete chunks by document ID (FAISS doesn't support deletion)."""
        # FAISS doesn't support deletion, would need to rebuild index
        # For now, just mark as deleted in metadata
        to_delete = []
        for idx, data in self.chunk_metadata.items():
            if data["metadata"].get("document_id") == document_id:
                to_delete.append(idx)
        
        for idx in to_delete:
            del self.chunk_metadata[idx]
        
        print(f"Marked {len(to_delete)} chunks as deleted for document: {document_id}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get FAISS statistics."""
        return {
            "total_chunks": len(self.chunk_metadata),
            "index_type": "FAISS",
            "embedding_dim": self.embedding_dim
        }
    
    def _matches_filter(self, metadata: Dict[str, Any], filter_dict: Optional[Dict[str, Any]]) -> bool:
        """Check if metadata matches filter criteria."""
        if not filter_dict:
            return True
        
        for key, value in filter_dict.items():
            if metadata.get(key) != value:
                return False
        
        return True


class PineconeVectorStore(VectorStore):
    """
    Pinecone implementation - Cloud-based vector database.
    Good for production deployments with high availability.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("pinecone_api_key")
        self.environment = config.get("pinecone_environment", "us-west1-gcp")
        self.index_name = config.get("index_name", "aion-docs")
        self.index = None
    
    async def _ensure_initialized(self):
        """Initialize Pinecone client."""
        if self.index is None:
            # TODO: Initialize Pinecone
            # import pinecone
            # pinecone.init(api_key=self.api_key, environment=self.environment)
            # self.index = pinecone.Index(self.index_name)
            print(f"Pinecone index '{self.index_name}' initialized")
            self.index = "mock_pinecone_index"
    
    async def add_chunks(self, chunks: List, embeddings: List[List[float]]):
        """Store chunks in Pinecone."""
        await self._ensure_initialized()
        
        # TODO: Upsert to Pinecone
        # vectors = [
        #     {
        #         "id": chunk.id,
        #         "values": embedding,
        #         "metadata": self._prepare_metadata(chunk)
        #     }
        #     for chunk, embedding in zip(chunks, embeddings)
        # ]
        # self.index.upsert(vectors=vectors)
        
        print(f"Added {len(chunks)} chunks to Pinecone")
    
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple]:
        """Search Pinecone index."""
        await self._ensure_initialized()
        
        # TODO: Query Pinecone
        # results = self.index.query(
        #     vector=query_embedding,
        #     top_k=top_k,
        #     include_metadata=True,
        #     filter=filter_dict
        # )
        # 
        # return [
        #     (
        #         match["metadata"]["content"],
        #         match["metadata"],
        #         match["score"]
        #     )
        #     for match in results["matches"]
        # ]
        
        return [("Pinecone result", {"document_id": "doc1"}, 0.95)][:top_k]
    
    async def delete_by_document_id(self, document_id: str):
        """Delete chunks from Pinecone."""
        await self._ensure_initialized()
        
        # TODO: Delete by filter
        # self.index.delete(filter={"document_id": document_id})
        print(f"Deleted chunks for document: {document_id}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Pinecone statistics."""
        await self._ensure_initialized()
        
        # TODO: Get actual stats
        # stats = self.index.describe_index_stats()
        return {
            "total_chunks": 0,
            "index_name": self.index_name,
            "environment": self.environment
        }
    
    def _prepare_metadata(self, chunk) -> Dict[str, Any]:
        """Prepare metadata for Pinecone (includes content)."""
        metadata = chunk.metadata.copy()
        metadata.update({
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content[:1000]  # Pinecone metadata size limits
        })
        return metadata


class VectorStoreManager:
    """
    Manages vector store selection and operations.
    Provides unified interface for all vector storage backends.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get("vectorstore", {}).get("provider", "simple")
        
        # Initialize vector stores
        vectorstore_config = config.get("vectorstore", {})
        
        # Import SimpleVectorStore for compatibility
        from .simple_vectorstore import SimpleVectorStore
        
        self.stores = {
            "simple": SimpleVectorStore(vectorstore_config),
            "chromadb": ChromaDBVectorStore(vectorstore_config),
            "faiss": FAISSVectorStore(vectorstore_config),
            "pinecone": PineconeVectorStore(vectorstore_config)
        }
    
    async def add_chunks(self, chunks: List, embeddings: List[List[float]]):
        """Store chunks in the configured vector store."""
        store = self.stores.get(self.provider)
        if not store:
            raise ValueError(f"Unknown vector store provider: {self.provider}")
        
        await store.add_chunks(chunks, embeddings)
    
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple]:
        """Search for similar chunks."""
        store = self.stores.get(self.provider)
        if not store:
            raise ValueError(f"Unknown vector store provider: {self.provider}")
        
        return await store.similarity_search(query_embedding, top_k, filter_dict)
    
    async def delete_by_document_id(self, document_id: str):
        """Delete all chunks from a document."""
        store = self.stores.get(self.provider)
        if not store:
            raise ValueError(f"Unknown vector store provider: {self.provider}")
        
        await store.delete_by_document_id(document_id)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        store = self.stores.get(self.provider)
        if not store:
            raise ValueError(f"Unknown vector store provider: {self.provider}")
        
        stats = await store.get_stats()
        stats["provider"] = self.provider
        return stats


# Global vector store manager
_vector_store_manager: Optional[VectorStoreManager] = None


def initialize_vector_store(config: Dict[str, Any]):
    """Initialize global vector store."""
    global _vector_store_manager
    _vector_store_manager = VectorStoreManager(config)


def get_vector_store() -> VectorStoreManager:
    """Get global vector store instance."""
    global _vector_store_manager
    if _vector_store_manager is None:
        from .config import get_config
        config = get_config()
        _vector_store_manager = VectorStoreManager(config.__dict__)
    
    return _vector_store_manager