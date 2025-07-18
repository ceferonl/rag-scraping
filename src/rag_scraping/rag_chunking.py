"""
RAG chunking functions for RAG Scraping.

This module handles creating RAG-ready chunks from knowledge base items.
"""

import logging
from typing import List, Dict, Any
from pathlib import Path

from .models import KnowledgeBaseItem
from .utils import clean_text_for_rag, format_date, create_chunk_id, split_text_into_chunks


logger = logging.getLogger(__name__)


def create_rag_chunks(
    items: List[KnowledgeBaseItem],
    config: Dict[str, Any],
    source_type: str = 'page'
) -> List[Dict[str, Any]]:
    """
    Create RAG-ready chunks from knowledge base items.

    Args:
        items: List of knowledge base items
        config: Configuration dictionary
        source_type: Type of source ('page' or 'pdf')

    Returns:
        List of RAG-ready chunk dictionaries
    """
    logger.info(f"Creating RAG chunks from {len(items)} {source_type} items...")

    all_chunks = []
    rag_config = config['rag']

    for item in items:
        chunks = create_chunks_from_item(item, config, source_type)
        all_chunks.extend(chunks)

    logger.info(f"Created {len(all_chunks)} RAG chunks from {source_type} items")
    return all_chunks


def create_chunks_from_item(
    item: KnowledgeBaseItem,
    config: Dict[str, Any],
    source_type: str = 'page'
) -> List[Dict[str, Any]]:
    """
    Create RAG-ready chunks from a single knowledge base item.

    Args:
        item: Knowledge base item
        config: Configuration dictionary
        source_type: Type of source ('page' or 'pdf')

    Returns:
        List of RAG-ready chunk dictionaries
    """
    chunks = []
    chunk_id = 1

    # Get RAG configuration
    rag_config = config['rag']
    min_chunk_size = rag_config['min_chunk_size']
    max_chunk_size = rag_config['max_chunk_size']
    target_chunk_size = rag_config['target_chunk_size']

    if not item.main_content or not item.main_content.strip():
        # If no main content, create a single chunk with basic info
        fallback_content = f"Page: {item.title}. URL: {item.url}"
        if len(fallback_content.strip()) >= min_chunk_size:
            chunk_item = create_chunk_dict(
                item, chunk_id, fallback_content, source_type, config
            )
            chunks.append(chunk_item)
        return chunks

    # Clean the main content
    cleaned_content = clean_text_for_rag(item.main_content)

    # Split content into chunks
    text_chunks = split_text_into_chunks(
        cleaned_content,
        max_chunk_size=target_chunk_size,
        min_chunk_size=min_chunk_size,
        overlap=200
    )

    # Create chunk dictionaries
    for text_chunk in text_chunks:
        if len(text_chunk.strip()) >= min_chunk_size:
            chunk_item = create_chunk_dict(
                item, chunk_id, text_chunk, source_type, config
            )
            chunks.append(chunk_item)
            chunk_id += 1

    # If no chunks were created (content was too short), create a single chunk
    if not chunks and len(cleaned_content.strip()) >= min_chunk_size:
        chunk_item = create_chunk_dict(
            item, 1, cleaned_content, source_type, config
        )
        chunks.append(chunk_item)

    return chunks


def create_chunk_dict(
    item: KnowledgeBaseItem,
    chunk_number: int,
    content: str,
    source_type: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a chunk dictionary with all necessary metadata.

    Args:
        item: Knowledge base item
        chunk_number: Chunk number
        content: Chunk content
        source_type: Type of source ('page' or 'pdf')
        config: Configuration dictionary

    Returns:
        Chunk dictionary
    """
    chunk_id = create_chunk_id(item.title, chunk_number)

    return {
        'id': chunk_id,
        'title': item.title,
        'content': content,
        'source_type': source_type,
        'sourcepage': item.url if source_type == 'page' else None,
        'sourcefile': None,  # Will be set for PDF chunks
        'page_number': None,  # Will be set for PDF chunks
        'date': format_date(item.date),
        'zones': item.zones or [],
        'type_innovatie': item.type_innovatie or [],
        'pdfs': item.pdfs or [],
        'videos': item.videos or [],
        'pictures': item.pictures or [],
        'chunk_number': chunk_number,
        'content_length': len(content)
    }


def merge_small_chunks(
    chunks: List[Dict[str, Any]],
    min_size: int = 100,
    max_size: int = 2000
) -> List[Dict[str, Any]]:
    """
    Merge small chunks together to create more substantial chunks.

    Args:
        chunks: List of chunks to merge
        min_size: Minimum chunk size to trigger merging
        max_size: Maximum size for merged chunks

    Returns:
        List of merged chunks
    """
    if not chunks:
        return []

    merged_chunks = []
    current_chunk = None

    for chunk in chunks:
        content = chunk.get('content', '')
        content_length = len(content)

        if content_length < min_size:
            # This is a small chunk, try to merge it
            if current_chunk is None:
                # Start a new merged chunk
                current_chunk = chunk.copy()
            else:
                # Add to existing merged chunk
                current_content = current_chunk.get('content', '')
                new_content = current_content + " " + content

                if len(new_content) <= max_size:
                    # Merge is within size limit
                    current_chunk['content'] = new_content
                    current_chunk['content_length'] = len(new_content)
                else:
                    # Merge would be too large, save current and start new
                    merged_chunks.append(current_chunk)
                    current_chunk = chunk.copy()
        else:
            # This is a substantial chunk
            if current_chunk is not None:
                # Save any pending merged chunk
                merged_chunks.append(current_chunk)
                current_chunk = None

            # Add this chunk as-is
            merged_chunks.append(chunk)

    # Don't forget the last merged chunk
    if current_chunk is not None:
        merged_chunks.append(current_chunk)

    return merged_chunks


def validate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and clean chunks.

    Args:
        chunks: List of chunks to validate

    Returns:
        List of validated chunks
    """
    valid_chunks = []

    for chunk in chunks:
        # Check required fields
        if not chunk.get('title') or not chunk.get('content'):
            continue

        # Ensure content is not empty
        content = chunk.get('content', '').strip()
        if not content:
            continue

        # Clean content
        chunk['content'] = clean_text_for_rag(content)

        # Update content length
        chunk['content_length'] = len(chunk['content'])

        valid_chunks.append(chunk)

    return valid_chunks
