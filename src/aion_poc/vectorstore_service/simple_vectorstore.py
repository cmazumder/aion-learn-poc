"""
Simple Vector Store - In-memory implementation for testing.
Alternative to ChromaDB for compatibility with all Python versions.
"""

from typing import List, Dict, Any, Optional, Tuple
import json
import pickle
from pathlib import Path


class SimpleVectorStore:
    """
    Simple in-memory vector store for testing and development.
    No external dependencies - just uses built-in Python libraries.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collection_name = config.get("collection_name", "aion_docs")
        self.persist_directory = config.get("persist_directory", "./data/vectorstore")
        
        # In-memory storage
        self.chunks = []  # List of chunk objects
        self.embeddings = []  # List of embeddings (parallel to chunks)
        self.chunk_metadata = []  # List of metadata (parallel to chunks)
        
        # Load existing data if available
        self._load_from_disk()
    
    async def add_chunks(self, chunks: List, embeddings: List[List[float]]):
        """Store chunks with their embeddings."""
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings must have the same length")
        
        # Add to in-memory storage
        for chunk, embedding in zip(chunks, embeddings):
            self.chunks.append(chunk)
            self.embeddings.append(embedding)
            self.chunk_metadata.append(self._prepare_metadata(chunk))
        
        # Persist to disk
        await self._save_to_disk()
        
        print(f"✅ Added {len(chunks)} chunks to SimpleVectorStore")
    
    async def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple]:
        """Search for similar chunks using cosine similarity."""
        if not self.embeddings:
            return []
        
        # Calculate similarities
        similarities = []
        for i, stored_embedding in enumerate(self.embeddings):
            # Apply filters if provided
            if filter_dict and not self._matches_filter(self.chunk_metadata[i], filter_dict):
                continue
            
            similarity = self._cosine_similarity(query_embedding, stored_embedding)
            similarities.append((similarity, i))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        # Return top_k results
        results = []
        for similarity, idx in similarities[:top_k]:
            results.append((
                self.chunks[idx].content,
                self.chunk_metadata[idx],
                1.0 - similarity  # Convert to distance (lower is better)
            ))
        
        return results
    
    async def delete_by_document_id(self, document_id: str):
        """Delete all chunks from a document."""
        indices_to_remove = []
        
        for i, metadata in enumerate(self.chunk_metadata):
            if metadata.get("document_id") == document_id:
                indices_to_remove.append(i)
        
        # Remove in reverse order to maintain indices
        for i in sorted(indices_to_remove, reverse=True):
            del self.chunks[i]
            del self.embeddings[i]
            del self.chunk_metadata[i]
        
        # Persist changes
        await self._save_to_disk()
        
        print(f"✅ Deleted {len(indices_to_remove)} chunks for document: {document_id}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            "total_chunks": len(self.chunks),
            "collection_name": self.collection_name,
            "store_type": "SimpleVectorStore",
            "embedding_dimension": len(self.embeddings[0]) if self.embeddings else 0
        }
    
    def _prepare_metadata(self, chunk) -> Dict[str, Any]:
        """Prepare chunk metadata for storage."""
        metadata = chunk.metadata.copy()
        metadata.update({
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "content_length": len(chunk.content),
            "chunk_id": chunk.id
        })
        
        # Ensure all values are JSON serializable
        return {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))}
    
    def _matches_filter(self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if metadata.get(key) != value:
                return False
        return True
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Magnitudes
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(a * a for a in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def _save_to_disk(self):
        """Save current state to disk."""
        persist_dir = Path(self.persist_directory)
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Save data using pickle for Python objects
        data_file = persist_dir / "simple_vectorstore.pkl"
        with open(data_file, 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'embeddings': self.embeddings,
                'chunk_metadata': self.chunk_metadata
            }, f)
        
        # Save metadata as JSON for inspection
        metadata_file = persist_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                'collection_name': self.collection_name,
                'total_chunks': len(self.chunks),
                'embedding_dimension': len(self.embeddings[0]) if self.embeddings else 0
            }, f, indent=2)
    
    def _load_from_disk(self):
        """Load existing data from disk."""
        persist_dir = Path(self.persist_directory)
        data_file = persist_dir / "simple_vectorstore.pkl"
        
        if data_file.exists():
            try:
                with open(data_file, 'rb') as f:
                    data = pickle.load(f)
                
                self.chunks = data.get('chunks', [])
                self.embeddings = data.get('embeddings', [])
                self.chunk_metadata = data.get('chunk_metadata', [])
                
                print(f"✅ Loaded {len(self.chunks)} chunks from disk")
            except Exception as e:
                print(f"⚠️  Could not load existing data: {e}")
                # Initialize empty storage
                self.chunks = []
                self.embeddings = []
                self.chunk_metadata = []


# Update the vectorstore module to use SimpleVectorStore by default
def get_simple_vector_store(config: Dict[str, Any]) -> SimpleVectorStore:
    """Get a simple vector store instance for testing."""
    return SimpleVectorStore(config)