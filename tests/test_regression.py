"""
Regression tests for the Versnellingsplan scraper.
Tests to detect if functionality breaks when making changes.
"""

import pytest
import json
from pathlib import Path
from rag_scraping.pages import VersnellingsplanScraper
from rag_scraping.pdfs import PDFProcessor


def test_scraper_config_unchanged():
    """Regression test: scraper config should not change unexpectedly."""
    scraper = VersnellingsplanScraper()

    # These values should remain stable
    assert scraper.base_url == "https://www.versnellingsplan.nl/Kennisbank/"
    assert scraper.config.REQUEST_DELAY == 1.0  # Increased for better reliability
    assert scraper.config.MAX_RETRIES == 3
    assert scraper.config.TIMEOUT == 30


def test_pdf_processor_config_unchanged():
    """Regression test: PDF processor config should not change unexpectedly."""
    processor = PDFProcessor()

    # These values should remain stable
    assert processor.config.DOWNLOAD_TIMEOUT == 30
    assert processor.config.MAX_RETRIES == 3
    assert processor.config.USER_AGENT == "RAG-Scraper/1.0"


def test_knowledge_base_item_structure():
    """Regression test: KnowledgeBaseItem structure should remain stable."""
    from rag_scraping.pages import KnowledgeBaseItem

    # Create a minimal item
    item = KnowledgeBaseItem(
        title="Test Item",
        url="https://example.com/test"
    )

    # Check that all expected fields exist
    expected_fields = [
        'title', 'url', 'date', 'item_type', 'main_content',
        'associated_files', 'zones', 'type_innovatie',
        'pdfs', 'videos', 'pictures'
    ]

    for field in expected_fields:
        assert hasattr(item, field), f"KnowledgeBaseItem should have {field} field"

    # Check default values
    assert item.associated_files == []
    assert item.zones == []
    assert item.type_innovatie == []
    assert item.pdfs == []
    assert item.videos == []
    assert item.pictures == []


def test_main_page_item_structure():
    """Regression test: MainPageItem structure should remain stable."""
    from rag_scraping.pages import MainPageItem

    # Create a minimal item
    item = MainPageItem(
        title="Test Item",
        url="https://example.com/test",
        item_type="Publicatie"
    )

    # Check that all expected fields exist
    expected_fields = ['title', 'url', 'item_type']

    for field in expected_fields:
        assert hasattr(item, field), f"MainPageItem should have {field} field"

    # Check values
    assert item.title == "Test Item"
    assert item.url == "https://example.com/test"
    assert item.item_type == "Publicatie"


def test_output_file_structure_consistency():
    """Regression test: output file structure should be consistent."""
    output_dir = Path("output/demo")

    # Find the most recent detailed items file
    detailed_files = list(output_dir.glob("rescraped_items_*.json"))
    if not detailed_files:
        pytest.skip("No detailed items files found")

    latest_file = max(detailed_files, key=lambda f: f.stat().st_mtime)

    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check that we have a reasonable number of items
    assert 10 <= len(data) <= 1000, f"Should have reasonable number of items, got {len(data)}"

    # Check that all items have the same structure
    first_item = data[0]
    expected_keys = set(first_item.keys())

    for item in data[1:5]:  # Check first 5 items
        assert set(item.keys()) == expected_keys, "All items should have same structure"


def test_rag_ready_chunk_sizes():
    """Regression test: RAG-ready chunks should have reasonable sizes."""
    output_dir = Path("output/demo")

    # Find the most recent RAG-ready file
    rag_files = list(output_dir.glob("rag_ready_*.json"))
    if not rag_files:
        pytest.skip("No RAG-ready files found")

    latest_file = max(rag_files, key=lambda f: f.stat().st_mtime)

    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check chunk sizes
    for chunk in data[:10]:  # Check first 10 chunks
        content_length = len(chunk['content'])
        assert 50 <= content_length <= 5000, f"Chunk size should be reasonable, got {content_length}"


def test_date_parsing_consistency():
    """Regression test: date parsing should be consistent."""
    output_dir = Path("output/demo")

    # Find the most recent detailed items file
    detailed_files = list(output_dir.glob("rescraped_items_*.json"))
    if not detailed_files:
        pytest.skip("No detailed items files found")

    latest_file = max(detailed_files, key=lambda f: f.stat().st_mtime)

    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check that dates are in ISO format
    for item in data:
        if item['date']:
            # Should be ISO format (YYYY-MM-DDTHH:MM:SS)
            assert 'T' in item['date'], f"Date should be ISO format: {item['date']}"
            assert len(item['date']) >= 10, f"Date should be at least YYYY-MM-DD: {item['date']}"


def test_url_consistency():
    """Regression test: URLs should be consistent and valid."""
    output_dir = Path("output/demo")

    # Find the most recent detailed items file
    detailed_files = list(output_dir.glob("rescraped_items_*.json"))
    if not detailed_files:
        pytest.skip("No detailed items files found")

    latest_file = max(detailed_files, key=lambda f: f.stat().st_mtime)

    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check that URLs are consistent
    for item in data:
        url = item['url']
        assert url.startswith('https://www.versnellingsplan.nl/'), \
            f"URL should be from versnellingsplan.nl: {url}"
        assert '/Kennisbank/' in url, f"URL should be from knowledge base: {url}"
