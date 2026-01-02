#!/usr/bin/env python3
"""
Test script to validate all imports work correctly after microservice restructuring.
Run with: poetry run python tests/test_imports.py
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all critical imports work correctly."""
    print("🧪 Testing AION POC imports after microservice restructuring...")
    
    try:
        # Test config
        from src.aion_poc.config.settings import get_config
        config = get_config()
        print("✅ Config service imports working")
        
        # Test ingestion
        from src.aion_poc.ingestion_service.core import IngestionManager, Document
        print("✅ Ingestion service imports working")
        
        # Test embedding
        from src.aion_poc.embedding_service.core import initialize_embedding_service, get_embedding_service
        print("✅ Embedding service imports working")
        
        # Test vectorstore
        from src.aion_poc.vectorstore_service.vectorstore import initialize_vector_store, get_vector_store
        print("✅ Vector store service imports working")
        
        # Test chunking
        from src.aion_poc.chunking_service.core import ChunkingManager, Chunk
        print("✅ Chunking service imports working")
        
        # Test retrieval
        from src.aion_poc.retrieval_service.core import RetrievalManager, RetrievalResult
        print("✅ Retrieval service imports working")
        
        # Test augmentation
        from src.aion_poc.augmentation_service.core import AugmentationManager, AugmentationResponse
        print("✅ Augmentation service imports working")
        
        # Test pipeline
        from src.aion_poc.shared.pipeline import get_pipeline, initialize_pipeline
        print("✅ Pipeline imports working")
        
        # Test demo
        from src.aion_poc.shared.demo import AionDemo
        print("✅ Demo imports working")
        
        # Test backward compatibility
        from src.aion_poc import get_config as legacy_config
        print("✅ Backward compatibility imports working")
        
        print("\n🎉 All imports successful! Microservice restructuring complete.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)