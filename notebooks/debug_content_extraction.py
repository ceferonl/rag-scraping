#!/usr/bin/env python3
"""
Debug script to examine HTML structure and understand content extraction issues.
"""

import asyncio
import json
import logging
from pathlib import Path

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_single_url(url: str, title: str):
    """Debug a single URL to understand the HTML structure."""
    logger.info(f"\n--- Debugging: {title} ---")
    logger.info(f"URL: {url}")

    # Fetch the page
    crawler = AsyncWebCrawler()
    result = await crawler.arun(url)

    if not result or not result.success:
        logger.error("Failed to fetch page")
        return

    soup = BeautifulSoup(result.html, 'html.parser')

    # Check for main post container
    main_post = soup.select_one('div[data-elementor-type="wp-post"]')
    logger.info(f"Main post container found: {main_post is not None}")

    if main_post:
        # Check for text editors
        text_editors = main_post.select('div.elementor-widget-text-editor div.elementor-widget-container')
        logger.info(f"Text editors found: {len(text_editors)}")

        for i, editor in enumerate(text_editors[:3]):  # Show first 3
            text = editor.get_text(strip=True)
            logger.info(f"  Editor {i+1}: {len(text)} chars - {text[:100]}...")

    # Check for alternative content areas
    logger.info("\n--- Alternative content areas ---")

    # Article tag
    article = soup.find('article')
    if article:
        text = article.get_text(strip=True)
        logger.info(f"Article content: {len(text)} chars - {text[:200]}...")

    # Entry content
    entry_content = soup.find('div', class_='entry-content')
    if entry_content:
        text = entry_content.get_text(strip=True)
        logger.info(f"Entry content: {len(text)} chars - {text[:200]}...")

    # Main content
    main_content = soup.find('main') or soup.find('div', class_='main-content')
    if main_content:
        text = main_content.get_text(strip=True)
        logger.info(f"Main content: {len(text)} chars - {text[:200]}...")

    # All paragraphs
    paragraphs = soup.find_all('p')
    logger.info(f"Total paragraphs: {len(paragraphs)}")

    meaningful_paragraphs = [p for p in paragraphs if len(p.get_text(strip=True)) > 50]
    logger.info(f"Meaningful paragraphs (>50 chars): {len(meaningful_paragraphs)}")

    for i, p in enumerate(meaningful_paragraphs[:3]):
        text = p.get_text(strip=True)
        logger.info(f"  Paragraph {i+1}: {len(text)} chars - {text[:150]}...")

    # Check for toggle content
    toggle_sections = soup.select('div.elementor-toggle')
    logger.info(f"Toggle sections found: {len(toggle_sections)}")

    for i, toggle in enumerate(toggle_sections[:2]):
        toggle_items = toggle.select('div.elementor-toggle-item')
        logger.info(f"  Toggle {i+1}: {len(toggle_items)} items")

        for j, item in enumerate(toggle_items[:2]):
            title_elem = item.select_one('a.elementor-toggle-title')
            content_elem = item.select_one('div.elementor-tab-content')

            if title_elem and content_elem:
                title = title_elem.get_text(strip=True)
                content = content_elem.get_text(strip=True)
                logger.info(f"    Item {j+1}: '{title}' - {len(content)} chars")

    # Check for accordion content
    accordion_items = soup.select('div.elementor-accordion-item')
    logger.info(f"Accordion items found: {len(accordion_items)}")

    # Save HTML for manual inspection
    output_dir = Path("output/debug")
    output_dir.mkdir(parents=True, exist_ok=True)

    html_file = output_dir / f"debug_{title.replace(' ', '_')[:30]}.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(result.html)

    logger.info(f"HTML saved to: {html_file}")

async def main():
    """Main debug function."""
    test_urls = [
        {
            "url": "https://www.versnellingsplan.nl/kennisbank/product/cerego-de-app-voor-studenten-om-parate-kennis-te-oefenen/",
            "title": "Cerego"
        }
    ]

    for test_data in test_urls:
        await debug_single_url(test_data["url"], test_data["title"])
        await asyncio.sleep(2)  # Delay between requests

if __name__ == "__main__":
    asyncio.run(main())
