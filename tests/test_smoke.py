"""
Smoke tests for the Versnellingsplan scraper.
Simple tests to verify the scraper still works.
"""

import pytest
import asyncio
from pathlib import Path

from rag_scraping.pages import VersnellingsplanScraper, MainPageItem


@pytest.mark.asyncio
async def test_main_page_scraping():
    """Smoke test: can we scrape the main page?"""
    scraper = VersnellingsplanScraper()
    items = await scraper.scrape_main_page_only(max_details=0)

    # Basic checks
    assert len(items) > 0, "Should find at least some items"
    assert all(isinstance(item, MainPageItem) for item in items), "All items should be MainPageItem"

    # Check structure
    for item in items:
        assert hasattr(item, 'title'), "Item should have title"
        assert hasattr(item, 'url'), "Item should have url"
        assert hasattr(item, 'item_type'), "Item should have item_type"
        assert item.title, "Title should not be empty"
        assert item.url, "URL should not be empty"
        assert item.url.startswith('http'), "URL should be valid"


@pytest.mark.asyncio
async def test_single_item_scraping():
    """Smoke test: can we scrape a single detailed item?"""
    scraper = VersnellingsplanScraper()

    # Test with a known item URL
    test_url = "https://www.versnellingsplan.nl/Kennisbank/vier-jaar-versnellen/"
    test_title = "Vier jaar versnellen"

    item = await scraper.scrape_item(test_url, test_title)

    # Basic checks
    assert item.title == test_title, "Title should match"
    assert item.url == test_url, "URL should match"
    assert item.main_content, "Should have main content"
    assert len(item.main_content) > 100, "Content should be substantial"


@pytest.mark.asyncio
async def test_pdf_processor_initialization():
    """Smoke test: can we initialize the PDF processor?"""
    from rag_scraping.pdfs import PDFProcessor

    processor = PDFProcessor()
    assert processor.output_dir.exists(), "Output directory should be created"
    assert processor.config, "Should have config"


def test_output_files_exist():
    """Smoke test: do our output files exist and have content?"""
    output_dir = Path("output/demo")

    # Check for recent detailed items file
    detailed_files = list(output_dir.glob("detailed_items_*.json"))
    assert len(detailed_files) > 0, "Should have detailed items files"

    # Check for recent RAG-ready files
    rag_files = list(output_dir.glob("rag_ready_*.json"))
    assert len(rag_files) > 0, "Should have RAG-ready files"

    # Check file sizes (adjust threshold for small files)
    for file in detailed_files + rag_files:
        assert file.stat().st_size > 100, f"File {file.name} should have content"
