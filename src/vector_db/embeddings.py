"""
Embedding functionality for vector databases.

Pure functions for generating, saving and loading embeddings.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def embed_text_azure_openai(text: str, config: Dict[str, Any]) -> List[float]:
    """Generate embeddings using Azure OpenAI."""
    from openai import AzureOpenAI

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")

    if not endpoint or not api_key:
        raise ValueError("Missing Azure OpenAI environment variables: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY")

    embeddings_config = config.get('embeddings', {})
    api_version = embeddings_config.get('api_version', '2024-08-01-preview')
    model = embeddings_config.get('model', 'text-embedding-3-small')

    client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=endpoint,
    )

    text = text or ""
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


def embed_text_openai(text: str, config: Dict[str, Any]) -> List[float]:
    """Generate embeddings using regular OpenAI."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OpenAI environment variable: OPENAI_API_KEY")

    embeddings_config = config.get('embeddings', {})
    model = embeddings_config.get('model', 'text-embedding-3-small')

    client = OpenAI(api_key=api_key)

    text = text or ""
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


def embed_text(text: str, config: Dict[str, Any]) -> List[float]:
    """Generate embeddings using configured provider."""
    embeddings_config = config.get('embeddings', {})
    provider = embeddings_config.get('provider', 'azure_openai')

    if provider == 'azure_openai':
        return embed_text_azure_openai(text, config)
    elif provider == 'openai':
        return embed_text_openai(text, config)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


def get_embedding_dimensions(config: Dict[str, Any]) -> int:
    """Get embedding dimensions from config."""
    return config.get('embeddings', {}).get('dimensions', 1536)


def add_embeddings_to_documents(
    docs: List[Dict[str, Any]],
    config: Dict[str, Any],
    save_embeddings: bool = True,
    embeddings_file: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Add embeddings to documents with optional saving.

    Args:
        docs: Documents to add embeddings to
        config: Configuration dictionary
        save_embeddings: Whether to save embeddings to file
        embeddings_file: Path to save embeddings (auto-generated if None)

    Returns:
        Documents with embeddings added
    """
    logger.info(f"Adding embeddings to {len(docs)} documents...")

    docs_with_embeddings = []
    embeddings_data = []

    for i, doc in enumerate(docs):
        content = doc.get('content', '') or doc.get('title', '')
        embedding = embed_text(content, config)

        doc_with_embedding = {
            **doc,
            "contentVector": embedding
        }
        docs_with_embeddings.append(doc_with_embedding)

        # Store embedding data for saving
        if save_embeddings:
            embeddings_data.append({
                "id": doc.get('id'),
                "content_preview": content[:100] + "..." if len(content) > 100 else content,
                "embedding": embedding,
                "dimensions": len(embedding)
            })

        if (i + 1) % 100 == 0:
            logger.info(f"Generated embeddings for {i + 1}/{len(docs)} documents")

    # Save embeddings if requested
    if save_embeddings and embeddings_data:
        if not embeddings_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            embeddings_file = f"output/production/embeddings_{timestamp}.json"

        save_embeddings_to_file(embeddings_data, embeddings_file, config)

    logger.info("Embedding generation complete.")
    return docs_with_embeddings


def save_embeddings_to_file(
    embeddings_data: List[Dict[str, Any]],
    filepath: str,
    config: Dict[str, Any]
) -> None:
    """Save embeddings to file with metadata."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)

    embeddings_config = config.get('embeddings', {})
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "provider": embeddings_config.get('provider'),
        "model": embeddings_config.get('model'),
        "dimensions": embeddings_config.get('dimensions'),
        "total_documents": len(embeddings_data)
    }

    output_data = {
        "metadata": metadata,
        "embeddings": embeddings_data
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(embeddings_data)} embeddings to {filepath}")


def load_embeddings_from_file(filepath: str) -> Dict[str, Any]:
    """Load embeddings from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_rag_ready_with_embeddings(
    rag_ready_file: str,
    embeddings_file: str,
    output_file: Optional[str] = None
) -> str:
    """
    Combine RAG-ready documents with saved embeddings.

    Args:
        rag_ready_file: Path to RAG-ready JSON file
        embeddings_file: Path to embeddings JSON file
        output_file: Output file path (auto-generated if None)

    Returns:
        Path to combined file
    """
    # Load data
    with open(rag_ready_file, 'r', encoding='utf-8') as f:
        rag_docs = json.load(f)

    embeddings_data = load_embeddings_from_file(embeddings_file)

    # Create lookup for embeddings by document ID
    embeddings_lookup = {
        item['id']: item['embedding']
        for item in embeddings_data['embeddings']
    }

    # Add embeddings to documents
    docs_with_embeddings = []
    matched_count = 0

    for doc in rag_docs:
        doc_id = doc.get('id')
        if doc_id in embeddings_lookup:
            doc_with_embedding = {
                **doc,
                "contentVector": embeddings_lookup[doc_id]
            }
            matched_count += 1
        else:
            logger.warning(f"No embedding found for document ID: {doc_id}")
            doc_with_embedding = doc

        docs_with_embeddings.append(doc_with_embedding)

    logger.info(f"Matched {matched_count}/{len(rag_docs)} documents with embeddings")

    # Save combined file
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"output/production/rag_ready_with_embeddings_{timestamp}.json"

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(docs_with_embeddings, f, ensure_ascii=False, indent=2)

    logger.info(f"Created RAG-ready file with embeddings: {output_file}")
    return output_file


# Backward compatibility - alias for the original function name
add_embeddings = add_embeddings_to_documents
