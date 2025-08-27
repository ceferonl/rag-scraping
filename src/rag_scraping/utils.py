"""
Shared utilities for RAG Scraping.

This module contains shared utility functions used throughout the pipeline
to avoid code duplication.
"""

import re
import unicodedata
from typing import Any, List
from datetime import datetime, timezone


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

    # Remove all quotes
    text = text.replace('"', '')
    text = text.replace("'", '')
    text = text.replace('\\', '/')
    text = text.replace('\t', ' ')
    text = text.replace('\\"', '')
    text = text.replace("\\'", '')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\n', ' ')
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single
    text = text.strip()
    return text


def format_date(date_value: Any) -> str:
    """
    Format date value to ISO8601 with timezone for vector DB compatibility.

    All dates must be ISO8601 with timezone (e.g. 2023-07-17T00:00:00Z).

    Args:
        date_value: Date value to format

    Returns:
        ISO8601 formatted date string with timezone or None
    """
    if not date_value:
        return None

    if isinstance(date_value, datetime):
        # If datetime has no timezone, assume UTC
        if date_value.tzinfo is None:
            date_value = date_value.replace(tzinfo=timezone.utc)
        return date_value.isoformat()
    elif isinstance(date_value, str):
        date_value = date_value.strip()
        if not date_value:
            return None
        # If string already has timezone info, return as-is
        if date_value.endswith('Z') or '+' in date_value or (date_value.count('-') > 2 and 'T' in date_value):
            return date_value
        # Otherwise add UTC timezone
        if 'T' in date_value:
            return date_value + 'Z'
        else:
            # Date only format, add time and timezone
            return date_value + 'T00:00:00Z'
    else:
        return str(date_value)


def normalize_document_id(text: str) -> str:
    """
    Normalize text to create vector DB compatible document IDs.

    Document IDs must only contain [a-zA-Z0-9_\\-=]. This function:
    - Normalizes unicode (é→e, ñ→n, etc.)
    - Removes/replaces forbidden characters
    - Handles multiple underscores and edge cases

    Args:
        text: Text to normalize for use as document ID

    Returns:
        Normalized text safe for use as document ID
    """
    if not text:
        return "unknown"

    # Unicode normalize (NFKD) and remove accents/diacritics
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))

    # Replace spaces and common punctuation with underscores
    text = text.replace(' ', '_')
    text = text.replace('(', '_').replace(')', '_')
    text = text.replace('[', '_').replace(']', '_')
    text = text.replace('{', '_').replace('}', '_')

    # Replace forbidden chars with underscores (only allow a-zA-Z0-9_\-=)
    text = re.sub(r'[^a-zA-Z0-9_\-=]', '_', text)

    # Collapse multiple underscores
    text = re.sub(r'_+', '_', text)

    # Strip leading/trailing underscores
    text = text.strip('_')

    # Ensure we have something valid
    if not text:
        return "unknown"

    # Ensure it starts with alphanumeric (some systems require this)
    if not text[0].isalnum():
        text = 'doc_' + text

    return text


def create_chunk_id(title: str, chunk_number: int) -> str:
    """
    Create a consistent chunk ID from title and number.

    Uses normalize_document_id to ensure vector DB compatibility.

    Args:
        title: Item title
        chunk_number: Chunk number

    Returns:
        Normalized chunk ID safe for vector databases
    """
    # Use the new normalization function
    clean_title = normalize_document_id(title)
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
