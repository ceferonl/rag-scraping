"""
Shared pytest fixtures for the Versnellingsplan scraper tests.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_scraping.versnellingsplan import KnowledgeBaseItem, VersnellingsplanScraper


@pytest.fixture
def mock_crawl_result():
    """Create a mock CrawlResult object."""
    result = MagicMock()
    result.html = "<html><body>Test HTML</body></html>"
    result.url = "https://example.com"
    result.status_code = 200
    return result


@pytest.fixture
def mock_crawler():
    """Create a mock AsyncWebCrawler object."""
    crawler = AsyncMock()
    crawler.crawl = AsyncMock()
    return crawler


@pytest.fixture
def sample_knowledge_base_items():
    """Create a list of sample KnowledgeBaseItem objects."""
    return [
        KnowledgeBaseItem(
            title="Test Item 1",
            url="https://example.com/1",
            date=None,
            item_type="Publication",
            main_content="Test content 1",
            associated_files=["file1.pdf"],
            zones=["Zone 1"],
            type_innovatie=["Type 1"]
        ),
        KnowledgeBaseItem(
            title="Test Item 2",
            url="https://example.com/2",
            date=None,
            item_type="Product",
            main_content="Test content 2",
            associated_files=["file2.pdf"],
            zones=["Zone 2"],
            type_innovatie=["Type 2"]
        )
    ]


@pytest.fixture
def scraper_with_mock_crawler(mock_crawler):
    """Create a VersnellingsplanScraper with a mock crawler."""
    scraper = VersnellingsplanScraper()
    scraper.crawler = mock_crawler
    return scraper
