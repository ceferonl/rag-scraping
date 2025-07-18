#!/usr/bin/env python3
"""
Re-scrape problematic items from the Versnellingsplan knowledge base.

This script identifies items with empty content or other issues and re-scrapes them
using the improved scraping logic with better retry mechanisms and fallback content extraction.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from rag_scraping.pages import VersnellingsplanScraper, KnowledgeBaseItem

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def load_detailed_items(file_path: str) -> List[Dict[str, Any]]:
    """Load detailed items from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def identify_problematic_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify items with empty content or other issues."""
    problematic = []

    for item in items:
        issues = []

        # Check for empty main content
        if not item.get('main_content') or not item['main_content'].strip():
            issues.append("empty_main_content")

        # Check for very short content (less than 100 characters)
        if item.get('main_content') and len(item['main_content'].strip()) < 100:
            issues.append("very_short_content")

        # Check for missing metadata
        if not item.get('item_type'):
            issues.append("missing_item_type")

        if not item.get('zones'):
            issues.append("missing_zones")

        if issues:
            item['issues'] = issues
            problematic.append(item)

    return problematic

async def rescrape_item(item_data: Dict[str, Any]) -> KnowledgeBaseItem:
    """Re-scrape a single item with improved logic."""
    url = item_data['url']
    title = item_data['title']

    logger.info(f"Re-scraping item: {title}")
    logger.info(f"URL: {url}")
    logger.info(f"Issues: {item_data.get('issues', [])}")

    # Create a new item and scrape with improved logic
    item = KnowledgeBaseItem(title=title, url=url)
    scraper = VersnellingsplanScraper()

    try:
        await scraper._scrape_item_details(item)

        # Log the results
        if item.main_content and item.main_content.strip():
            logger.info(f"✅ Successfully extracted {len(item.main_content)} characters of content")
        else:
            logger.warning(f"❌ Still no content extracted after re-scraping")

        return item

    except Exception as e:
        logger.error(f"❌ Error re-scraping {title}: {e}")
        return item

async def main():
    """Main function to re-scrape problematic items."""
    # Configuration
    input_file = "output/demo/detailed_items_20250716_160459.json"  # Update this path
    output_dir = Path("output/demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load existing items
    logger.info(f"Loading items from: {input_file}")
    items = load_detailed_items(input_file)
    logger.info(f"Loaded {len(items)} items")

    # Identify problematic items
    logger.info("Identifying problematic items...")
    problematic_items = identify_problematic_items(items)
    logger.info(f"Found {len(problematic_items)} problematic items")

    if not problematic_items:
        logger.info("No problematic items found!")
        return

    # Show summary of issues
    issue_counts = {}
    for item in problematic_items:
        for issue in item.get('issues', []):
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    logger.info("Issue summary:")
    for issue, count in issue_counts.items():
        logger.info(f"  {issue}: {count} items")

    # Re-scrape problematic items
    logger.info("Starting re-scraping of problematic items...")
    rescraped_items = []

    for i, item_data in enumerate(problematic_items):
        logger.info(f"\n--- Re-scraping item {i+1}/{len(problematic_items)} ---")

        # Add delay between items
        if i > 0:
            await asyncio.sleep(1.0)  # 1 second delay

        rescraped_item = await rescrape_item(item_data)
        rescraped_items.append(rescraped_item)

    # Save re-scraped items
    output_file = output_dir / f"rescraped_items_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([item.to_dict() for item in rescraped_items], f, indent=2, ensure_ascii=False)

    logger.info(f"\nRe-scraped items saved to: {output_file}")

    # Analyze results
    successful_rescrapes = 0
    for item in rescraped_items:
        if item.main_content and item.main_content.strip() and len(item.main_content.strip()) >= 100:
            successful_rescrapes += 1

    logger.info(f"\nRe-scraping results:")
    logger.info(f"  Total problematic items: {len(problematic_items)}")
    logger.info(f"  Successfully re-scraped: {successful_rescrapes}")
    logger.info(f"  Still problematic: {len(problematic_items) - successful_rescrapes}")

    # Create a combined file with all items (original + re-scraped)
    logger.info("Creating combined file with all items...")

    # Create a map of re-scraped items by URL
    rescraped_map = {item.url: item for item in rescraped_items}

    # Update original items with re-scraped data
    updated_items = []
    for item_data in items:
        url = item_data['url']
        if url in rescraped_map:
            # Use re-scraped data
            updated_items.append(rescraped_map[url].to_dict())
        else:
            # Keep original data
            updated_items.append(item_data)

    combined_file = output_dir / f"detailed_items_combined_{timestamp}.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(updated_items, f, indent=2, ensure_ascii=False)

    logger.info(f"Combined file saved to: {combined_file}")

if __name__ == "__main__":
    asyncio.run(main())
