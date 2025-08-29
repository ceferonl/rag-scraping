#!/usr/bin/env python3
"""
DEMO: Demo script for new embedding functionality.
Purpose: Demonstrate embedding generation, saving, and RAG-ready file creation.
Created: 2025-01-27
"""

import sys
from pathlib import Path

# Correct path reference from notebooks/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import json
import logging
from rag_scraping.config import load_config
from vector_db.embeddings import (
    embed_text,
    add_embeddings_to_documents,
    save_embeddings_to_file,
    create_rag_ready_with_embeddings
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_documents():
    """Create a small sample of documents for testing."""
    return [
        {
            "id": "test_doc_1",
            "title": "Eerste testdocument",
            "content": "Dit is een test document voor het testen van embeddings. Het bevat Nederlandse tekst om te zien of de embedding functionaliteit correct werkt.",
            "source_type": "test",
            "sourcepage": "test_page_1"
        },
        {
            "id": "test_doc_2",
            "title": "Tweede testdocument",
            "content": "Een ander testdocument met wat verschillende content. Dit document test of meerdere documenten correct verwerkt worden.",
            "source_type": "test",
            "sourcepage": "test_page_2"
        },
        {
            "id": "test_doc_3",
            "title": "Derde testdocument",
            "content": "Het laatste testdocument. Dit document controleert of de batch processing goed functioneert voor embedding generatie.",
            "source_type": "test",
            "sourcepage": "test_page_3"
        }
    ]

def demo_single_embedding():
    """Demo generating a single embedding."""
    logger.info("Demo: single embedding generation...")
    
    config = load_config("config.yaml")
    demo_text = "Dit is een demo voor het genereren van een enkele embedding."
    
    try:
        embedding = embed_text(demo_text, config)
        logger.info(f"✅ Single embedding generated successfully - dimensions: {len(embedding)}")
        return True
    except Exception as e:
        logger.error(f"❌ Single embedding failed: {e}")
        return False

def demo_document_embeddings():
    """Demo generating embeddings for multiple documents."""
    logger.info("Demo: document embeddings generation...")
    
    config = load_config("config.yaml")
    docs = create_sample_documents()
    
    try:
        # Demo without saving
        docs_with_embeddings = add_embeddings_to_documents(docs, config, save_embeddings=False)
        
        # Verify all documents have embeddings
        for doc in docs_with_embeddings:
            if "contentVector" not in doc:
                raise ValueError(f"Document {doc['id']} missing contentVector")
            if not isinstance(doc["contentVector"], list):
                raise ValueError(f"Document {doc['id']} contentVector is not a list")
            if len(doc["contentVector"]) == 0:
                raise ValueError(f"Document {doc['id']} contentVector is empty")
        
        logger.info(f"✅ Document embeddings generated successfully for {len(docs_with_embeddings)} documents")
        return docs_with_embeddings
    except Exception as e:
        logger.error(f"❌ Document embeddings failed: {e}")
        return None

def demo_save_embeddings():
    """Demo saving embeddings to file."""
    logger.info("Demo: saving embeddings to file...")
    
    config = load_config("config.yaml")
    docs = create_sample_documents()
    
    try:
        # Generate embeddings and save them
        docs_with_embeddings = add_embeddings_to_documents(
            docs, config, 
            save_embeddings=True,
            embeddings_file="output/demo/demo_embeddings.json"
        )
        
        # Verify file was created
        embeddings_file = Path("output/demo/demo_embeddings.json")
        if not embeddings_file.exists():
            raise FileNotFoundError("Embeddings file was not created")
        
        # Verify file content
        with open(embeddings_file, 'r') as f:
            saved_data = json.load(f)
        
        if "metadata" not in saved_data:
            raise ValueError("Missing metadata in saved embeddings")
        if "embeddings" not in saved_data:
            raise ValueError("Missing embeddings in saved data")
        if len(saved_data["embeddings"]) != len(docs):
            raise ValueError("Mismatch in number of saved embeddings")
        
        logger.info(f"✅ Embeddings saved successfully to {embeddings_file}")
        logger.info(f"   Provider: {saved_data['metadata']['provider']}")
        logger.info(f"   Model: {saved_data['metadata']['model']}")
        logger.info(f"   Dimensions: {saved_data['metadata']['dimensions']}")
        
        return str(embeddings_file), docs_with_embeddings
        
    except Exception as e:
        logger.error(f"❌ Save embeddings failed: {e}")
        return None, None

def demo_rag_ready_with_embeddings():
    """Demo creating RAG-ready file with embeddings."""
    logger.info("Demo: RAG-ready file with embeddings creation...")
    
    try:
        # First save a simple RAG-ready file
        docs = create_sample_documents()
        rag_ready_file = "output/demo/demo_rag_ready.json"
        Path(rag_ready_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(rag_ready_file, 'w') as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
        
        # Save embeddings separately
        embeddings_file, _ = demo_save_embeddings()
        if not embeddings_file:
            raise ValueError("Could not create embeddings file")
        
        # Combine them
        combined_file = create_rag_ready_with_embeddings(
            rag_ready_file,
            embeddings_file,
            "output/demo/demo_rag_ready_with_embeddings.json"
        )
        
        # Verify combined file
        with open(combined_file, 'r') as f:
            combined_data = json.load(f)
        
        # Check that all documents have embeddings
        for doc in combined_data:
            if "contentVector" not in doc:
                raise ValueError(f"Document {doc['id']} missing contentVector in combined file")
        
        logger.info(f"✅ RAG-ready file with embeddings created successfully: {combined_file}")
        return combined_file
        
    except Exception as e:
        logger.error(f"❌ RAG-ready with embeddings failed: {e}")
        return None

def main():
    """Run all embedding demos."""
    logger.info("🚀 Starting embedding functionality demo...")
    
    # Create demo output directory
    Path("output/demo").mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    total_demos = 4
    
    # Demo 1: Single embedding
    if demo_single_embedding():
        success_count += 1
    
    # Demo 2: Document embeddings
    docs_with_embeddings = demo_document_embeddings()
    if docs_with_embeddings:
        success_count += 1
    
    # Demo 3: Save embeddings
    embeddings_file, _ = demo_save_embeddings()
    if embeddings_file:
        success_count += 1
    
    # Demo 4: RAG-ready with embeddings
    combined_file = demo_rag_ready_with_embeddings()
    if combined_file:
        success_count += 1
    
    # Summary
    logger.info(f"\n🎯 Demo Results: {success_count}/{total_demos} demos completed")
    
    if success_count == total_demos:
        logger.info("✅ All embedding functionality demos completed successfully!")
        return True
    else:
        logger.error(f"❌ {total_demos - success_count} demos failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
