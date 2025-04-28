"""
Unit tests for the VersnellingsplanScraper class.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from crawl4ai import AsyncWebCrawler

from rag_scraping.versnellingsplan import KnowledgeBaseItem, VersnellingsplanScraper


@pytest.fixture
def mock_page():
    """Create a mock Page object."""
    page = MagicMock()
    page.select = MagicMock()
    return page


@pytest.fixture
def mock_crawler():
    """Create a mock Crawler object."""
    crawler = AsyncMock()
    crawler.arun = AsyncMock()
    return crawler


@pytest.mark.asyncio
async def test_scraper_initialization():
    """Test that the scraper initializes correctly."""
    scraper = VersnellingsplanScraper()
    assert scraper.base_url == "https://www.versnellingsplan.nl/kennisbank/"
    assert isinstance(scraper.crawler, AsyncWebCrawler)
    assert scraper.items == []


@pytest.mark.asyncio
async def test_scrape_knowledge_base(scraper_with_mock_crawler, mock_crawl_result):
    """Test the main scraping method."""
    # Set up the mock crawler to return our mock crawl result
    scraper_with_mock_crawler.crawler.arun.return_value = mock_crawl_result

    # Mock the _scrape_item_details method
    scraper_with_mock_crawler._scrape_item_details = AsyncMock()

    # Run the scraping process
    items = await scraper_with_mock_crawler.scrape()

    # Verify that the crawler was called with the correct URL
    scraper_with_mock_crawler.crawler.arun.assert_called_once_with(scraper_with_mock_crawler.base_url)

    # Verify that _scrape_item_details was called for each item
    assert scraper_with_mock_crawler._scrape_item_details.call_count == len(items)


@pytest.mark.asyncio
async def test_scrape_item_details(scraper_with_mock_crawler, mock_crawl_result):
    """Test the method that scrapes details from an individual item page."""
    # Set up the mock crawler to return our mock crawl result
    scraper_with_mock_crawler.crawler.arun.return_value = mock_crawl_result

    # Set up the mock crawl result with some test HTML
    # ruff: noqa
    mock_crawl_result.html = """
    <html>
        <body>
            <div class="content">Test content</div>
            <ul class="elementor-icon-list-items elementor-post-info">
                <li itemprop="datePublished">
                    <span class="elementor-post-info__item--type-date">20 september 2022</span>
                </li>
                <li itemprop="about">
                    <a class="elementor-post-info__terms-list-item">Zone 1</a>
                </li>
                <li itemprop="about">
                    <span class="elementor-post-info__terms-list-item">Publicatie</span>
                </li>
                <li itemprop="about">
                    <span class="elementor-post-info__terms-list-item">Onderzoek</span>
                </li>
            </ul>
            <div data-elementor-type="wp-post">
                <section class="elementor-section elementor-top-section">
                    <div class="elementor-widget-text-editor">
                        <div class="elementor-widget-container">
                            <p>This is the main content of the page.</p>
                        </div>
                    </div>
                </section>
            </div>
            <a href="test.pdf">Test PDF</a>
        </body>
    </html>
    """

    # Create a test item
    item = KnowledgeBaseItem(title="Test Item", url="https://example.com/test")

    # Call the method
    await scraper_with_mock_crawler._scrape_item_details(item)

    # Verify that the crawler was called with the correct URL
    scraper_with_mock_crawler.crawler.arun.assert_called_once_with(item.url)

    # Verify that the item's attributes were updated
    assert item.main_content is not None, "Main content should be set"
    assert "This is the main content of the page" in item.main_content, (
        "Main content should contain expected text"
    )
    assert item.date == datetime(2022, 9, 20), "Date should be correctly parsed"
    assert item.zones == ["Zone 1"], "Zones should be correctly extracted"
    assert item.item_type == "Publicatie", "Item type should be correctly extracted"
    assert item.type_innovatie == ["Onderzoek"], (
        "Type innovatie should be correctly extracted"
    )
    assert item.associated_files == ["test.pdf"], (
        "Associated files should be correctly extracted"
    )


def test_save_results(tmp_path, sample_knowledge_base_items):
    """Test the method that saves results to a file."""
    # Create a scraper
    scraper = VersnellingsplanScraper()

    # Add some test items to the scraper
    scraper.items = sample_knowledge_base_items

    # Create a temporary output file
    output_file = tmp_path / "test_output.json"

    # Call the method
    scraper.save_results(str(output_file))

    # Verify that the file was created
    assert output_file.exists()

    # Verify that the file contains the correct data
    import json
    with open(output_file, "r") as f:
        data = json.load(f)

    assert len(data) == 2
    assert data[0]["title"] == "Test Item 1"
    assert data[0]["url"] == "https://example.com/1"
    assert data[0]["item_type"] == "Publication"
    assert data[0]["main_content"] == "Test content 1"
    assert data[0]["associated_files"] == ["file1.pdf"]
    assert data[0]["zones"] == ["Zone 1"]
    assert data[0]["type_innovatie"] == ["Type 1"]

    assert data[1]["title"] == "Test Item 2"
    assert data[1]["url"] == "https://example.com/2"
    assert data[1]["item_type"] == "Product"
    assert data[1]["main_content"] == "Test content 2"
    assert data[1]["associated_files"] == ["file2.pdf"]
    assert data[1]["zones"] == ["Zone 2"]
    assert data[1]["type_innovatie"] == ["Type 2"]
