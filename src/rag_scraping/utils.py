"""
Shared utilities for RAG Scraping.

This module contains shared utility functions used throughout the pipeline
to avoid code duplication.
"""

import re
from typing import Any, List
from datetime import datetime


def clean_text_for_rag(text: str) -> str:
    """
    Clean text specifically for RAG applications.

    This is a shared utility to avoid code duplication between modules.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text optimized for RAG
    """
    if not text:
        return ""

    # Normalize quotes and problematic characters
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('\\', '/')
    text = text.replace('\t', ' ')

    # Remove escaped quotes (both single and double)
    text = text.replace('\\"', '"')
    text = text.replace("\\'", "'")

    # Normalize newlines
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Replace all newlines with spaces (for RAG, we want continuous text)
    text = text.replace('\n', ' ')

    # Remove excessive whitespace
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single

    # Clean up and strip
    text = text.strip()

    return text


def format_date(date_value: Any) -> str:
    """
    Format date value for consistent output.

    Args:
        date_value: Date value to format

    Returns:
        Formatted date string or None
    """
    if not date_value:
        return None

    if hasattr(date_value, 'isoformat'):
        return date_value.isoformat()
    elif isinstance(date_value, str):
        return date_value
    else:
        return str(date_value)


def create_chunk_id(title: str, chunk_number: int) -> str:
    """
    Create a consistent chunk ID from title and number.

    Args:
        title: Item title
        chunk_number: Chunk number

    Returns:
        Formatted chunk ID
    """
    # Clean title for use in ID
    clean_title = title.replace(' ', '_').replace('(', '').replace(')', '')
    clean_title = re.sub(r'[^\w\-_]', '', clean_title)  # Remove special chars

    return f"{clean_title}_chunk_{chunk_number:02d}"


def split_text_into_chunks(
    text: str,
    max_chunk_size: int = 1500,
    min_chunk_size: int = 50,
    overlap: int = 200
) -> List[str]:
    """
    Split text into chunks for RAG processing.

    Args:
        text: Text to split
        max_chunk_size: Maximum chunk size in characters
        min_chunk_size: Minimum chunk size in characters
        overlap: Overlap between chunks in characters

    Returns:
        List of text chunks
    """
    if not text or len(text.strip()) < min_chunk_size:
        return []

    chunks = []
    current_pos = 0

    while current_pos < len(text):
        # Find the end position for this chunk
        end_pos = current_pos + max_chunk_size

        if end_pos >= len(text):
            # Last chunk
            chunk = text[current_pos:].strip()
            if len(chunk) >= min_chunk_size:
                chunks.append(chunk)
            break

        # Try to find a good break point (sentence end)
        chunk_text = text[current_pos:end_pos]

        # Look for sentence endings
        sentence_endings = ['.', '!', '?']
        break_pos = end_pos

        for ending in sentence_endings:
            pos = chunk_text.rfind(ending)
            if pos > max_chunk_size * 0.7:  # Only break if it's in the last 30%
                break_pos = current_pos + pos + 1
                break

        # If no good sentence break, try paragraph break
        if break_pos == end_pos:
            pos = chunk_text.rfind('\n\n')
            if pos > max_chunk_size * 0.5:
                break_pos = current_pos + pos + 2

        # Extract chunk
        chunk = text[current_pos:break_pos].strip()
        if len(chunk) >= min_chunk_size:
            chunks.append(chunk)

        # Move to next position with overlap
        current_pos = max(break_pos - overlap, current_pos + 1)

    return chunks
