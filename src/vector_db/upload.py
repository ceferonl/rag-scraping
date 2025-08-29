"""
Upload functionality for vector databases.

This module provides functionality to upload RAG documents to vector databases.
Use validation.py for document validation and embeddings.py for embedding generation.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from rag_scraping.config import load_config
from .azure import AzureVectorDB
from .embeddings import add_embeddings_to_documents

logger = logging.getLogger(__name__)


def upload_documents_to_azure(
    docs: List[Dict[str, Any]],
    config: Dict[str, Any],
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    index_name: Optional[str] = None,
    create_index: bool = True,
    add_embeddings: bool = True,
    save_embeddings: bool = True
) -> None:
    """
    Upload documents to Azure Cognitive Search.

    Note: Documents should be pre-validated using validation.py before upload.

    Args:
        docs: Documents to upload (should be pre-validated)
        config: Configuration dictionary
        endpoint: Azure Search endpoint (if not provided, reads from env)
        api_key: Azure Search API key (if not provided, reads from env)
        index_name: Index name (if not provided, reads from config)
        create_index: Whether to create/recreate the index
        add_embeddings: Whether to add embeddings to documents
        save_embeddings: Whether to save embeddings to file
    """
    import os

    # Get Azure configuration
    endpoint = endpoint or os.environ.get('AZURE_SEARCH_ENDPOINT')
    api_key = api_key or os.environ.get('AZURE_SEARCH_API_KEY')

    vector_db_cfg = config.get('vector_db', {})
    index_name = index_name or vector_db_cfg.get('index_name')

    if not (endpoint and api_key and index_name):
        raise ValueError(f"Missing Azure configuration: endpoint={bool(endpoint)}, api_key={bool(api_key)}, index_name={index_name}")

    logger.info(f"Uploading {len(docs)} documents to Azure Search: {index_name}")

    # Add embeddings if requested
    if add_embeddings:
        docs_with_embeddings = add_embeddings_to_documents(docs, config, save_embeddings)
    else:
        docs_with_embeddings = docs

    # Initialize Azure Vector DB
    db = AzureVectorDB(endpoint=endpoint, api_key=api_key, index_name=index_name)

    # Create index if requested
    if create_index:
        logger.info(f"Creating/recreating index '{index_name}'...")
        db.create_index()
        logger.info("Index ready.")

    # Upload documents
    logger.info(f"Uploading {len(docs_with_embeddings)} documents...")
    db.upload_documents(docs_with_embeddings)
    logger.info("Upload complete.")


def upload_from_file(
    json_path: str,
    config_path: Optional[str] = None,
    **kwargs
) -> None:
    """
    Upload documents from a JSON file to Azure.

    Args:
        json_path: Path to JSON file containing documents
        config_path: Path to config file (if not provided, looks for config.yaml)
        **kwargs: Additional arguments for upload_documents_to_azure
    """
    # Load configuration
    if config_path:
        config = load_config(config_path)
    else:
        # Look for config.yaml in common locations
        possible_configs = [
            Path("config.yaml"),
            Path("../config.yaml"),
            Path("../../config.yaml"),
            Path(__file__).parent.parent.parent / "config.yaml"
        ]
        config_path = None
        for path in possible_configs:
            if path.exists():
                config_path = str(path)
                break

        if not config_path:
            raise FileNotFoundError("Could not find config.yaml - please specify config_path")

        config = load_config(config_path)

    # Load documents
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Document file not found: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        docs = json.load(f)

    logger.info(f"Loaded {len(docs)} documents from {json_path}")

    # Upload documents
    upload_documents_to_azure(docs, config, **kwargs)


# Backward compatibility function
def add_embeddings(docs: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Backward compatibility wrapper."""
    return add_embeddings_to_documents(docs, config, save_embeddings=False)


if __name__ == "__main__":
    # Simple CLI interface
    import argparse

    parser = argparse.ArgumentParser(description="Upload RAG documents to Azure Search (use validation.py first)")
    parser.add_argument("json_file", help="Path to JSON file containing pre-validated documents")
    parser.add_argument("--config", help="Path to config file (default: auto-detect config.yaml)")
    parser.add_argument("--no-create-index", action="store_true", help="Don't create/recreate index")
    parser.add_argument("--no-embeddings", action="store_true", help="Don't add embeddings")
    parser.add_argument("--no-save-embeddings", action="store_true", help="Don't save embeddings to file")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        upload_from_file(
            args.json_file,
            config_path=args.config,
            create_index=not args.no_create_index,
            add_embeddings=not args.no_embeddings,
            save_embeddings=not args.no_save_embeddings
        )
        print("Upload completed successfully!")
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        exit(1)
