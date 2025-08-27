"""
Web scraping functions for RAG Scraping.

This module provides functional approaches to web scraping,
replacing the class-based approach with pure functions.
"""

import asyncio
import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

from .models import MainPageItem, KnowledgeBaseItem
from .utils import clean_text_for_rag, format_date


logger = logging.getLogger(__name__)


async def scrape_with_retry(
    url: str,
    config: Dict[str, Any],
    max_retries: Optional[int] = None
) -> Any:
    """
    Scrape a URL with retry logic and exponential backoff.

    Args:
        url: URL to scrape
        config: Configuration dictionary
        max_retries: Maximum number of retries (uses config default if None)

    Returns:
        Crawl result or None if failed
    """
    if max_retries is None:
        max_retries = config['scraping']['max_retries']

    retry_delays = config['scraping']['retry_delays']

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Fetching URL (attempt {attempt + 1}/{max_retries + 1}): {url}")

            # Create a fresh crawler instance for each request
            crawler = AsyncWebCrawler()
            result = await crawler.arun(url)

            # Check if the request was successful
            if result and result.success and result.html:
                logger.info(f"Successfully fetched URL: {url}")
                return result
            else:
                logger.warning(f"Request returned no content for {url} (attempt {attempt + 1})")

        except Exception as e:
            logger.error(f"Exception fetching {url} (attempt {attempt + 1}): {e}")

        # If this wasn't the last attempt, wait before retrying
        if attempt < max_retries:
            delay = retry_delays[min(attempt, len(retry_delays) - 1)]
            logger.info(f"Waiting {delay} seconds before retry...")
            await asyncio.sleep(delay)

    logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts")
    return None


async def delay_between_requests(config: Dict[str, Any]) -> None:
    """Add a random delay between requests to be respectful to the server."""
    min_delay = config['scraping']['min_delay']
    max_delay = config['scraping']['max_delay']
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)


async def scrape_main_page(config: Dict[str, Any]) -> List[MainPageItem]:
    """
    Scrape the main page and return list of main page items.

    Args:
        config: Configuration dictionary

    Returns:
        List of main page items
    """
    base_url = config['scraping']['base_url']
    logger.info(f"Scraping main page: {base_url}")

    result = await scrape_with_retry(base_url, config)
    if not result or not result.success:
        logger.error(f"Failed to fetch main page: {base_url}")
        return []

    soup = BeautifulSoup(result.html, 'html.parser')
    item_divs = soup.find_all('div', class_='elementor-post__card')
    logger.info(f"Found {len(item_divs)} items on main page")

    items = []
    for item_div in item_divs:
        title_link = item_div.select_one('a.elementor-post__thumbnail__link')
        if not title_link:
            continue

        url = title_link.get('href')
        if not url:
            continue

        title_elem = item_div.select_one('div.elementor-post__text a')
        title = title_elem.get_text(strip=True) if title_elem else None
        badge = item_div.select_one('div.elementor-post__badge')
        item_type = badge.get_text(strip=True) if badge else None

        if title and url:
            item = MainPageItem(
                title=title,
                url=url,
                item_type=item_type or "Unknown"
            )
            items.append(item)

    logger.info(f"Successfully extracted {len(items)} main page items")
    return items


def is_valid_content(content: str) -> bool:
    """
    Check if scraped content is valid (not a server error or empty).

    Args:
        content: The scraped content to validate

    Returns:
        True if content is valid, False if it indicates an error
    """
    if not content or len(content.strip()) < 50:
        return False

    # Check for server error indicators
    error_indicators = [
        "server encountered an internal error",
        "misconfiguration and was unable to complete",
        "contact the server administrator",
        "error occurred",
        "500 internal server error",
        "503 service unavailable"
    ]

    content_lower = content.lower()
    return not any(indicator in content_lower for indicator in error_indicators)


async def scrape_item_details(
    main_item: MainPageItem,
    config: Dict[str, Any]
) -> KnowledgeBaseItem:
    """
    Scrape detailed information for a single item with content-level retry.

    Args:
        main_item: Main page item to get details for
        config: Configuration dictionary

    Returns:
        Detailed knowledge base item
    """
    logger.info(f"Scraping details for: {main_item.title}")

    max_retries = config['scraping']['max_retries']
    retry_delays = config['scraping']['retry_delays']

    for attempt in range(max_retries + 1):
        try:
            # Attempt to scrape
            result = await scrape_with_retry(main_item.url, config)
            if not result or not result.success:
                logger.warning(f"HTTP request failed for {main_item.title} (attempt {attempt + 1})")
                raise Exception("HTTP request failed")

            soup = BeautifulSoup(result.html, 'html.parser')

            # Extract main content first to validate
            main_content = extract_main_content(soup, config)

            # Validate content quality
            if not is_valid_content(main_content):
                logger.warning(f"Invalid content detected for {main_item.title} (attempt {attempt + 1})")
                raise Exception("Invalid or error content detected")

            # Content is valid - create the full item
            item = KnowledgeBaseItem(
                title=main_item.title,
                url=main_item.url,
                item_type=main_item.item_type,
                main_content=main_content
            )

            # Extract additional details
            date_elem = soup.select_one('time.elementor-post-date')
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                try:
                    item.date = datetime.strptime(date_text, "%d %B %Y")
                except ValueError:
                    logger.warning(f"Could not parse date: {date_text}")

            zones_elem = soup.select_one('div.elementor-post__terms')
            if zones_elem:
                zones_links = zones_elem.select('a')
                item.zones = [link.get_text(strip=True) for link in zones_links]

            type_elem = soup.select_one('div.elementor-post__badge')
            if type_elem:
                item.type_innovatie = [type_elem.get_text(strip=True)]

            files = extract_associated_files(soup)
            item.pdfs = files.get('pdfs', [])
            item.videos = files.get('videos', [])
            item.pictures = files.get('pictures', [])

            logger.info(f"Successfully scraped details for {item.title}")
            return item

        except Exception as e:
            if attempt < max_retries:
                delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                logger.info(f"Retrying {main_item.title} in {delay} seconds (attempt {attempt + 2}/{max_retries + 1})")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Failed to scrape {main_item.title} after {max_retries + 1} attempts: {e}")

    # Return failed item after all retries exhausted
    return KnowledgeBaseItem(
        title=main_item.title,
        url=main_item.url,
        item_type=main_item.item_type,
        main_content=f"Failed to scrape after {max_retries + 1} attempts"
    )


def extract_main_content(soup: BeautifulSoup, config: Dict[str, Any]) -> str:
    """
    Extract main content from a page using multiple strategies.

    Args:
        soup: BeautifulSoup object
        config: Configuration dictionary

    Returns:
        Extracted main content
    """
    # Primary content selectors
    content_selectors = [
        'div.elementor-widget-theme-post-content',
        'div.elementor-post__content',
        'article.elementor-post',
        'div.entry-content',
        'main',
        'div.content'
    ]

    main_content_parts = []

    # Try primary selectors
    for selector in content_selectors:
        content_elem = soup.select_one(selector)
        if content_elem:
            text = content_elem.get_text(separator=' ', strip=True)
            if text and len(text.strip()) > 100:
                main_content_parts.append(text)
                break

    # If no content found, try fallback method
    if not main_content_parts:
        fallback_content = extract_content_fallback(soup)
        if fallback_content:
            main_content_parts.append(fallback_content)

    # Combine content and clean
    if main_content_parts:
        main_content = " \n\n ".join(main_content_parts)

        # Remove unwanted phrases
        remove_phrases = config['rag']['remove_phrases']
        for phrase in remove_phrases:
            main_content = main_content.replace(phrase, "")

        return clean_text_for_rag(main_content)

    return ""


def extract_content_fallback(soup: BeautifulSoup) -> str:
    """
    Fallback content extraction method.

    Args:
        soup: BeautifulSoup object

    Returns:
        Extracted content or empty string
    """
    # Try to find any substantial text content
    text_elements = soup.find_all(['p', 'div', 'section'], string=True)

    content_parts = []
    for elem in text_elements:
        text = elem.get_text(strip=True)
        if text and len(text) > 50:  # Only substantial text
            content_parts.append(text)

    if content_parts:
        return " ".join(content_parts)

    return ""


def extract_associated_files(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """
    Extract associated files from a page.

    Args:
        soup: BeautifulSoup object

    Returns:
        Dictionary with file lists by type
    """
    files = {
        'pdfs': [],
        'videos': [],
        'pictures': []
    }

    # Find all links
    links = soup.find_all('a', href=True)

    for link in links:
        href = link['href']

        if href.endswith('.pdf'):
            files['pdfs'].append(href)
        elif any(ext in href.lower() for ext in ['.mp4', '.avi', '.mov', '.wmv']):
            files['videos'].append(href)
        elif any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
            files['pictures'].append(href)

    return files
