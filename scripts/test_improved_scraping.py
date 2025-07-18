#!/usr/bin/env python3
"""
Test script for improved scraping logic.

This script tests the improved scraping logic with a few sample URLs to ensure
the retry mechanism and fallback content extraction work correctly.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

from rag_scraping.pages import VersnellingsplanScraper, KnowledgeBaseItem

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Test URLs - these should be accessible and have content
TEST_URLS = [
    {
        "url": "https://www.versnellingsplan.nl/Kennisbank/vier-jaar-versnellen/",
        "title": "Vier jaar versnellen"
    },
    {
        "url": "https://www.versnellingsplan.nl/Kennisbank/kwaliteitenradar-onderwijskundig-ict-professional/",
        "title": "Kwaliteitenradar Onderwijskundig ICT professional"
    },
    {
        "url": "https://www.versnellingsplan.nl/Kennisbank/goede-voorbeelden-onderwijsinnovaties-met-ict/",
        "title": "Goede voorbeelden onderwijsinnovaties met ict"
    }
]

async def test_single_item(url: str, title: str) -> KnowledgeBaseItem:
    """Test scraping a single item."""
    logger.info(f"\n--- Testing item: {title} ---")
    logger.info(f"URL: {url}")

    item = KnowledgeBaseItem(title=title, url=url)
    scraper = VersnellingsplanScraper()

    try:
        await scraper._scrape_item_details(item)

        # Analyze results
        content_length = len(item.main_content.strip()) if item.main_content else 0
        has_content = content_length > 0
        has_metadata = bool(item.item_type or item.zones or item.type_innovatie)

        logger.info(f"Results:")
        logger.info(f"  Content length: {content_length} characters")
        logger.info(f"  Has content: {'✅' if has_content else '❌'}")
        logger.info(f"  Has metadata: {'✅' if has_metadata else '❌'}")
        logger.info(f"  Item type: {item.item_type}")
        logger.info(f"  Zones: {item.zones}")
        logger.info(f"  Type innovatie: {item.type_innovatie}")
        logger.info(f"  Associated files: {len(item.associated_files)}")

        if has_content:
            logger.info(f"  Content preview: {item.main_content[:200]}...")

        return item

    except Exception as e:
        logger.error(f"❌ Error testing {title}: {e}")
        return item

async def main():
    """Main test function."""
    logger.info("Testing improved scraping logic...")

    output_dir = Path("output/test")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Test each URL
    results = []
    for i, test_data in enumerate(TEST_URLS):
        logger.info(f"\n--- Test {i+1}/{len(TEST_URLS)} ---")

        # Add delay between tests
        if i > 0:
            await asyncio.sleep(2.0)  # 2 second delay between tests

        result = await test_single_item(test_data["url"], test_data["title"])
        results.append(result)

    # Save results
    output_file = output_dir / f"test_results_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([item.to_dict() for item in results], f, indent=2, ensure_ascii=False)

    logger.info(f"\nTest results saved to: {output_file}")

    # Summary
    successful_tests = sum(1 for item in results if item.main_content and len(item.main_content.strip()) > 100)

    logger.info(f"\nTest Summary:")
    logger.info(f"  Total tests: {len(TEST_URLS)}")
    logger.info(f"  Successful: {successful_tests}")
    logger.info(f"  Failed: {len(TEST_URLS) - successful_tests}")

    if successful_tests == len(TEST_URLS):
        logger.info("✅ All tests passed! Improved scraping logic is working correctly.")
    else:
        logger.warning(f"⚠️  {len(TEST_URLS) - successful_tests} tests failed. Check the logs for details.")

if __name__ == "__main__":
    asyncio.run(main())
