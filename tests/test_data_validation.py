"""
Data validation tests for the Versnellingsplan scraper output.
Tests to verify the output has the correct structure and quality.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime


def load_latest_output_file(pattern: str) -> list:
    """Load the most recent output file matching the pattern."""
    output_dir = Path("output/demo")
    files = list(output_dir.glob(pattern))

    if not files:
        pytest.skip(f"No files found matching {pattern}")

    # Get the most recent file
    latest_file = max(files, key=lambda f: f.stat().st_mtime)

    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_detailed_items_structure():
    """Test: do detailed items have the correct structure?"""
    data = load_latest_output_file("rescraped_items_*.json")

    assert isinstance(data, list), "Should be a list of items"
    assert len(data) > 0, "Should have at least one item"

    # Check each item structure
    for item in data:
        # Required fields
        assert 'title' in item, "Item should have title"
        assert 'url' in item, "Item should have url"
        assert 'main_content' in item, "Item should have main_content"

        # Optional fields should exist (even if empty)
        assert 'date' in item, "Item should have date field"
        assert 'item_type' in item, "Item should have item_type field"
        assert 'zones' in item, "Item should have zones field"
        assert 'type_innovatie' in item, "Item should have type_innovatie field"
        assert 'pdfs' in item, "Item should have pdfs field"
        assert 'videos' in item, "Item should have videos field"
        assert 'pictures' in item, "Item should have pictures field"
        # Note: other_files field is not used in our data structure

        # Data types
        assert isinstance(item['title'], str), "Title should be string"
        assert isinstance(item['url'], str), "URL should be string"
        assert isinstance(item['main_content'], str), "Main content should be string"
        assert isinstance(item['zones'], list), "Zones should be list"
        assert isinstance(item['type_innovatie'], list), "Type innovatie should be list"
        assert isinstance(item['pdfs'], list), "PDFs should be list"
        assert isinstance(item['videos'], list), "Videos should be list"
        assert isinstance(item['pictures'], list), "Pictures should be list"
        # Note: other_files field is not used in our data structure


def test_detailed_items_content_quality():
    """Test: is the content quality good?"""
    data = load_latest_output_file("rescraped_items_*.json")

    for item in data:
        # Content should not be empty
        assert item['title'].strip(), "Title should not be empty"
        assert item['url'].strip(), "URL should not be empty"
        # Content should not be empty - this indicates a scraping problem
        content = item['main_content']
        assert content and content.strip(), f"Main content should not be empty for item '{item['title']}': {repr(content)}"

        # URLs should be valid
        assert item['url'].startswith('http'), "URL should be valid"

        # Content should be substantial
        assert len(item['title']) > 5, "Title should be meaningful"
        assert len(item['main_content']) > 50, "Content should be substantial"

        # Date format if present
        if item['date']:
            try:
                datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Invalid date format: {item['date']}")


def test_rag_ready_structure():
    """Test: do RAG-ready files have the correct structure?"""
    data = load_latest_output_file("rag_ready_*.json")

    assert isinstance(data, list), "Should be a list of chunks"
    assert len(data) > 0, "Should have at least one chunk"

    # Check each chunk structure
    for chunk in data:
        # Required fields for RAG
        assert 'content' in chunk, "Chunk should have content"
        assert 'title' in chunk, "Chunk should have title"
        assert 'sourcepage' in chunk, "Chunk should have sourcepage"

        # Data types
        assert isinstance(chunk['content'], str), "Content should be string"
        assert isinstance(chunk['title'], str), "Title should be string"
        assert isinstance(chunk['sourcepage'], str), "Sourcepage should be string"


def test_rag_ready_content_quality():
    """Test: is the RAG-ready content quality good?"""
    data = load_latest_output_file("rag_ready_*.json")

    for chunk in data:
        # Content should not be empty
        assert chunk['content'].strip(), "Chunk content should not be empty"

        # Content should be reasonable length for RAG - very small chunks indicate problems
        content_length = len(chunk['content'])
        assert content_length >= 50, f"Chunk should be substantial, got {content_length} chars"
        assert content_length < 5000, "Chunk should not be too long"

        # Title should be meaningful
        assert chunk['title'].strip(), "Title should not be empty"
        assert chunk['sourcepage'].startswith('http'), "Sourcepage should be valid"

        # Source should indicate origin
        assert 'versnellingsplan.nl' in chunk['sourcepage'], \
            "Sourcepage should be from versnellingsplan.nl"


def test_file_categorization():
    """Test: are files properly categorized?"""
    data = load_latest_output_file("rescraped_items_*.json")

    for item in data:
        # Check that files are properly categorized
        all_files = set(item['pdfs'] + item['videos'] + item['pictures'])

        # PDFs should end with .pdf
        for pdf in item['pdfs']:
            assert pdf.lower().endswith('.pdf'), f"PDF should end with .pdf: {pdf}"

        # Videos should be video URLs
        for video in item['videos']:
            assert any(ext in video.lower() for ext in ['.mp4', '.avi', '.mov', 'youtu.be', 'youtube.com']), \
                f"Video should be video format: {video}"

        # No overlap between categories
        pdfs = set(item['pdfs'])
        videos = set(item['videos'])
        pictures = set(item['pictures'])
        assert not (pdfs & videos), "PDFs and videos should not overlap"
        assert not (pdfs & pictures), "PDFs and pictures should not overlap"
        assert not (videos & pictures), "Videos and pictures should not overlap"
