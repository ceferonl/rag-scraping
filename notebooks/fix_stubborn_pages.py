#!/usr/bin/env python3
"""
Specialized script for pages that need extended retry logic and loading time.
Use this for pages that consistently fail with standard retry logic.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag_scraping.config import load_config_with_paths
from rag_scraping.scraping import scrape_with_retry, extract_main_content, extract_associated_files
from rag_scraping.models import MainPageItem, KnowledgeBaseItem
from bs4 import BeautifulSoup
import logging

# Hardcoded list of problematic items that need special handling
STUBBORN_PAGES = [
    {
        "title": "Vakcommunity's over een landelijk platform digitale open leermaterialen",
        "url": "https://www.versnellingsplan.nl/Kennisbank/vakcommunitys-over-een-landelijk-platform-digitale-open-leermaterialen/",
        "item_type": "Publicatie"
    }
]


async def scrape_with_extreme_patience(
    url: str,
    config: dict,
    max_retries: int = 10,
    initial_delay: float = 2.0,
    post_fetch_delay: float = 3.0
) -> any:
    """
    Scrape a URL with extreme patience - many retries, long delays, post-fetch waiting.

    Args:
        url: URL to scrape
        config: Configuration dictionary
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (scales up)
        post_fetch_delay: Delay after successful fetch to wait for content loading

    Returns:
        Crawl result or None if failed
    """
    logger = logging.getLogger(__name__)

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"🔄 Attempt {attempt + 1}/{max_retries + 1}: Fetching {url}")

            # Use the standard retry mechanism first
            result = await scrape_with_retry(url, config, max_retries=1)

            if result and result.success and result.html:
                logger.info(f"✅ Fetch successful, waiting {post_fetch_delay}s for content to load...")
                await asyncio.sleep(post_fetch_delay)

                # Quick content validation
                if len(result.html) > 10000:  # Reasonable content size
                    soup = BeautifulSoup(result.html, 'html.parser')
                    main_content = extract_main_content(soup, config)

                    if len(main_content.strip()) > 100:  # Has meaningful content
                        logger.info(f"🎉 Successfully extracted content ({len(main_content)} chars)")
                        return result
                    else:
                        logger.warning(f"⚠️  Content too short ({len(main_content)} chars), retrying...")
                else:
                    logger.warning(f"⚠️  HTML too short ({len(result.html)} chars), retrying...")
            else:
                logger.warning(f"❌ Fetch failed, retrying...")

        except Exception as e:
            logger.error(f"💥 Exception on attempt {attempt + 1}: {e}")

        # If this wasn't the last attempt, wait with exponential backoff
        if attempt < max_retries:
            delay = initial_delay * (2 ** attempt)  # Exponential backoff: 2, 4, 8, 16, 32...
            logger.info(f"⏳ Waiting {delay}s before next attempt...")
            await asyncio.sleep(delay)

    logger.error(f"💀 Failed to scrape {url} after {max_retries + 1} attempts")
    return None


async def scrape_stubborn_item(item_data: dict, config: dict) -> KnowledgeBaseItem:
    """
    Scrape a single stubborn item with extreme patience.

    Args:
        item_data: Dictionary with title, url, item_type
        config: Configuration dictionary

    Returns:
        KnowledgeBaseItem with scraped content
    """
    logger = logging.getLogger(__name__)
    main_item = MainPageItem(**item_data)

    logger.info(f"🎯 Targeting stubborn page: {main_item.title}")
    logger.info(f"🔗 URL: {main_item.url}")

    # Use extreme patience scraping
    result = await scrape_with_extreme_patience(main_item.url, config)

    if not result or not result.success:
        logger.error(f"❌ Failed to fetch: {main_item.title}")
        return KnowledgeBaseItem(
            title=main_item.title,
            url=main_item.url,
            item_type=main_item.item_type,
            main_content="Failed to scrape after extreme retry attempts"
        )

    # Parse the content
    soup = BeautifulSoup(result.html, 'html.parser')

    # Create knowledge base item
    item = KnowledgeBaseItem(
        title=main_item.title,
        url=main_item.url,
        item_type=main_item.item_type
    )

    # Extract date
    date_elem = soup.select_one('time.elementor-post-date')
    if date_elem:
        date_text = date_elem.get_text(strip=True)
        try:
            item.date = datetime.strptime(date_text, "%d %B %Y")
        except ValueError:
            logger.warning(f"Could not parse date: {date_text}")

    # Extract zones
    zones_elem = soup.select_one('div.elementor-post__terms')
    if zones_elem:
        zones_links = zones_elem.select('a')
        item.zones = [link.get_text(strip=True) for link in zones_links]

    # Extract type innovatie
    type_elem = soup.select_one('div.elementor-post__badge')
    if type_elem:
        item.type_innovatie = [type_elem.get_text(strip=True)]

    # Extract main content
    main_content = extract_main_content(soup, config)
    item.main_content = main_content

    # Extract associated files
    files = extract_associated_files(soup)
    item.pdfs = files.get('pdfs', [])
    item.videos = files.get('videos', [])
    item.pictures = files.get('pictures', [])

    logger.info(f"✅ Successfully scraped: {item.title}")
    logger.info(f"📄 Content length: {len(item.main_content)} characters")

    return item


async def main():
    """Main function to scrape stubborn pages."""
    print("🔧 Stubborn Pages Fix Script")
    print("=" * 50)

    try:
        # Load configuration
        config_path = Path(__file__).parent.parent / "config.yaml"
        config = load_config_with_paths(config_path=config_path, run_type="production")

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
        )

        print(f"🎯 Targeting {len(STUBBORN_PAGES)} stubborn pages...")

        results = []
        for i, item_data in enumerate(STUBBORN_PAGES, 1):
            print(f"\n[{i}/{len(STUBBORN_PAGES)}] Processing: {item_data['title']}")

            item = await scrape_stubborn_item(item_data, config)
            results.append(item)

            if i < len(STUBBORN_PAGES):
                print("⏳ Waiting 5 seconds before next item...")
                await asyncio.sleep(5)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(__file__).parent.parent / "output" / "production" / f"stubborn_pages_fixed_{timestamp}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([item.to_dict() for item in results], f, indent=2, ensure_ascii=False)

        print(f"\n🎉 Success! Fixed {len(results)} stubborn pages")
        print(f"💾 Results saved to: {output_file}")

        # Show summary
        for item in results:
            status = "✅ Success" if len(item.main_content) > 100 else "❌ Failed"
            print(f"   {status}: {item.title} ({len(item.main_content)} chars)")

        return results

    except Exception as e:
        print(f"❌ Script failed: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    asyncio.run(main())
