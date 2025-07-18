"""
Versnellingsplan Knowledge Base Scraper

This module provides functionality to scrape the Versnellingsplan knowledge base,
including metadata, content, and associated files.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List, Optional, Any, Dict

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

import logging
import asyncio
import time
import random

from pydantic import BaseModel, ValidationError, field_validator, model_validator


@dataclass
class KnowledgeBaseItem:
    """Represents a single item in the knowledge base."""
    title: str
    url: str
    date: Optional[datetime] = None
    item_type: Optional[str] = None
    main_content: Optional[str] = None
    associated_files: List[str] = None
    zones: List[str] = None
    type_innovatie: List[str] = None
    pdfs: List[str] = None
    videos: List[str] = None
    pictures: List[str] = None
    other_files: List[str] = None

    def __post_init__(self):
        if self.associated_files is None:
            self.associated_files = []
        if self.zones is None:
            self.zones = []
        if self.type_innovatie is None:
            self.type_innovatie = []
        if self.pdfs is None:
            self.pdfs = []
        if self.videos is None:
            self.videos = []
        if self.pictures is None:
            self.pictures = []
        if self.other_files is None:
            self.other_files = []

    def to_dict(self):
        """Convert the item to a dictionary for JSON serialization."""
        data = asdict(self)
        if self.date:
            data['date'] = self.date.isoformat()
        # Remove associated_files from output since it's split into specific categories
        data.pop('associated_files', None)
        return data


class ScraperConfig:
    BASE_URL = "https://www.versnellingsplan.nl/Kennisbank/"
    REQUEST_DELAY = 1.0  # seconds between requests (increased for better reliability)
    MIN_DELAY = 0.5  # minimum delay between requests
    MAX_DELAY = 2.0  # maximum delay between requests
    MAX_RETRIES = 3
    TIMEOUT = 30
    USER_AGENT = "RAG-Scraper/1.0"
    RETRY_DELAYS = [1, 2, 5]  # delays in seconds for retries

# Set up logging
logger = logging.getLogger("rag_scraping.pages")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class KnowledgeBaseItemValidation(BaseModel):
    title: str
    url: str
    main_content: str
    pdfs: list
    videos: list
    pictures: list
    other_files: list

    @field_validator('main_content')
    @classmethod
    def main_content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('main_content must not be empty')
        return v

    @model_validator(mode="after")
    def no_overlap_in_files(self):
        pdfs = set(self.pdfs)
        videos = set(self.videos)
        pictures = set(self.pictures)
        other_files = set(self.other_files)
        overlap = (pdfs | videos | pictures) & other_files
        if overlap:
            raise ValueError(f'other_files overlaps with pdfs/videos/pictures: {overlap}')
        return self


class MainPageItem(BaseModel):
    title: str
    url: str
    item_type: str


class VersnellingsplanScraper:
    """Scraper for the Versnellingsplan knowledge base."""

    def __init__(self, base_url: str = ScraperConfig.BASE_URL):
        self.base_url = base_url
        self.crawler = AsyncWebCrawler()
        self.items: List[KnowledgeBaseItem] = []
        self.config = ScraperConfig

    async def _scrape_with_retry(self, url: str, max_retries: int = None) -> Any:
        """Scrape with proper retry logic and exponential backoff."""
        if max_retries is None:
            max_retries = self.config.MAX_RETRIES

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
                delay = self.config.RETRY_DELAYS[min(attempt, len(self.config.RETRY_DELAYS) - 1)]
                logger.info(f"Waiting {delay} seconds before retry...")
                await asyncio.sleep(delay)

        logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts")
        return None

    async def _delay_between_requests(self):
        """Add a random delay between requests to be respectful to the server."""
        delay = random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY)
        await asyncio.sleep(delay)

    async def scrape(self) -> List[KnowledgeBaseItem]:
        logger.info(f"Scraping main page: {self.base_url}")
        result = await self._scrape_with_retry(self.base_url)
        if not result or not result.success:
            logger.error(f"Failed to fetch main page: {self.base_url}")
            return self.items

        soup = BeautifulSoup(result.html, 'html.parser')
        item_divs = soup.find_all('div', class_='elementor-post__card')
        logger.info(f"Found {len(item_divs)} items on main page")

        for i, item_div in enumerate(item_divs):
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
                item = KnowledgeBaseItem(
                    title=title,
                    url=url,
                    item_type=item_type
                )
                logger.info(f"Scraping item {i+1}/{len(item_divs)}: {title}")
                try:
                    await self._scrape_item_details(item)
                    # Add delay between items
                    if i < len(item_divs) - 1:
                        await self._delay_between_requests()
                except Exception as e:
                    logger.error(f"Error scraping details for {title} ({url}): {e}")
                    continue
                self.items.append(item)
        return self.items

    async def scrape_main_page_only(self, max_details: int = 0) -> List[MainPageItem]:
        """
        Scrape only the main knowledge base page and optionally get details for a limited number of items.

        Args:
            max_details: Maximum number of items to fetch full details for (0 means no detail scraping)

        Returns:
            List of knowledge base items with basic metadata
        """
        logger.info(f"Scraping main page: {self.base_url}")
        result = await self._scrape_with_retry(self.base_url)
        items = []
        if not result or not result.success:
            logger.error(f"Failed to fetch main page: {self.base_url}")
            return items
        soup = BeautifulSoup(result.html, 'html.parser')
        item_divs = soup.find_all('div', class_='elementor-post__card')
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
                # Use KnowledgeBaseItem if we need details, MainPageItem otherwise
                if max_details > 0:
                    item = KnowledgeBaseItem(title=title, url=url, item_type=item_type)
                else:
                    item = MainPageItem(title=title, url=url, item_type=item_type)
                items.append(item)
        if max_details > 0:
            for i, item in enumerate(items[:max_details]):
                logger.info(f"Scraping details for item {i+1}/{max_details}: {item.title}")
                try:
                    await self._scrape_item_details(item)
                    # Add delay between items
                    if i < min(max_details, len(items)) - 1:
                        await self._delay_between_requests()
                except Exception as e:
                    logger.error(f"Error scraping details for {item.title} ({item.url}): {e}")
                    continue
        return items

    async def _scrape_item_details(self, item: KnowledgeBaseItem) -> None:
        """
        Scrape additional details for a knowledge base item, including toggle/dropdown content and interactive elements.
        """
        print(f"Scraping item details in scrape for {item.title} ({item.url})")
        result = await self._scrape_with_retry(item.url)
        if not result or not result.success:
            logger.error(f"Failed to fetch item page: {item.url}")
            return
        soup = BeautifulSoup(result.html, 'html.parser')

        # Extract metadata (same as original function)
        info_list = soup.select_one(
            'ul.elementor-icon-list-items.elementor-post-info'
        )
        if info_list:
            # Extract date
            date_item = info_list.select_one(
                'li[itemprop="datePublished"] '
                'span.elementor-post-info__item--type-date'
            )
            if date_item:
                date_text = date_item.get_text(strip=True)
                try:
                    # Parse Dutch month names
                    dutch_months = {
                        'januari': '01',
                        'februari': '02',
                        'maart': '03',
                        'april': '04',
                        'mei': '05',
                        'juni': '06',
                        'juli': '07',
                        'augustus': '08',
                        'september': '09',
                        'oktober': '10',
                        'november': '11',
                        'december': '12'
                    }
                    # Split the date text
                    day, month, year = date_text.split()
                    # Convert month name to number
                    month_num = dutch_months.get(month.lower())
                    if month_num:
                        # Create a standardized date string
                        date_str = f"{day} {month_num} {year}"
                        # Parse the date
                        item.date = datetime.strptime(date_str, "%d %m %Y")
                except Exception:
                    pass

            # Extract zone information
            zone_items = info_list.select(
                'li[itemprop="about"] a.elementor-post-info__terms-list-item'
            )
            if zone_items:
                item.zones = [zone.get_text(strip=True) for zone in zone_items]

            # Extract knowledge base category and type innovatie
            category_items = info_list.select(
                'li[itemprop="about"] span.elementor-post-info__terms-list-item'
            )
            for cat_item in category_items:
                text = cat_item.get_text(strip=True)
                # Check if it's a knowledge base category
                if text in ['Product', 'Publicatie', 'Project']:
                    item.item_type = text
                # Check if it's a type innovatie
                elif text in [
                    'Strategie', 'Goede voorbeelden', 'Onderzoek',
                    'Instrumenten & Tools', 'Experimenten'
                ]:
                    item.type_innovatie.append(text)

        # Extract main content (similar to original function)
        main_content_parts = []

        # First find the main post container
        main_post = soup.select_one('div[data-elementor-type="wp-post"]')
        if main_post:
            # Find all elementor-top-section elements within the main post
            top_sections = main_post.select(
                'section.elementor-section.elementor-top-section'
            )

            # Process each top section
            for section in top_sections:
                # Look for text editor widgets in this section
                text_editors = section.select(
                    'div.elementor-widget-text-editor '
                    'div.elementor-widget-container'
                )
                if text_editors:
                    # Combine text from all text editors in this section
                    section_text = ' '.join(
                        editor.get_text(strip=True) for editor in text_editors
                    )
                    if section_text:
                        main_content_parts.append(section_text)

        # If we still don't have content, try a more generic approach
        if not main_content_parts:
            text_elements = soup.select(
                'div.elementor-widget-text-editor div.elementor-widget-container'
            )
            if text_elements:
                main_content_parts.append(' '.join(
                    elem.get_text(separator=' ', strip=True) for elem in text_elements
                ))

        # Add a section separator before toggle content if we have main content
        if main_content_parts:
            main_content_parts.append(" \n\n--- Toggle Content ---\n ")

        # NEW: Extract toggle/dropdown content
        toggle_sections = soup.select('div.elementor-toggle')
        has_toggle_content = False
        for toggle_section in toggle_sections:
            toggle_items = toggle_section.select('div.elementor-toggle-item')
            for toggle_item in toggle_items:
                # Get the toggle title
                title_elem = toggle_item.select_one('a.elementor-toggle-title')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Get the toggle content
                content_elem = toggle_item.select_one('div.elementor-tab-content')
                if not content_elem:
                    continue

                content = content_elem.get_text(separator=' ', strip=True)

                # Add to main content parts with proper formatting
                toggle_text = f"## {title} {content}"
                main_content_parts.append(toggle_text)
                has_toggle_content = True

        # Add a section separator before data-action content if we have toggle content
        if has_toggle_content:
            main_content_parts.append(" \n\n--- Interactive Elements ---\n ")

        # NEW: Extract content from elements with data-action attributes
        data_action_elements = soup.select('[data-action]')
        has_data_action_content = False
        for element in data_action_elements:
            # Get the action type and element text
            element_text = element.get_text(separator=' ', strip=True)

            if element_text:
                main_content_parts.append(element_text)
                has_data_action_content = True

        # NEW: Look for buttons with spans that might contain text
        buttons = soup.select('button.trigger')
        for button in buttons:
            # First check if it has a data-action attribute
            data_action = button.get('data-action')
            if data_action:
                # Get the button text
                button_text = button.get_text(separator=' ', strip=True)
                if button_text:
                    main_content_parts.append(f"Button ({data_action}): {button_text}")

        # NEW: Look for accordion content
        accordion_items = soup.select('div.elementor-accordion-item')
        has_accordion_content = False
        for accordion_item in accordion_items:
            # Get the accordion title
            title_elem = accordion_item.select_one('a.elementor-accordion-title')
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)

            # Get the accordion content
            content_elem = accordion_item.select_one('div.elementor-tab-content')
            if not content_elem:
                continue

            content = content_elem.get_text(separator=' ', strip=True)

            # Add to main content parts with proper formatting
            accordion_text = f"## {title} {content}"
            main_content_parts.append(accordion_text)
            has_accordion_content = True

        # Add a section separator before accordion content if we have accordion content
        if has_accordion_content:
            main_content_parts.append(" \n\n--- Accordion Content ---\n ")

        # Combine all content parts with double newlines between each part for better readability
        if main_content_parts:
            main_content = " \n\n ".join(main_content_parts)
            # Remove unwanted phrases
            for phrase in [
                "Download de presentatie hier",
                "Deel deze pagina",
                "Deze website maakt gebruik van cookies. Lees hier over onze Coookies"
            ]:
                main_content = main_content.replace(phrase, "")
            item.main_content = main_content
        else:
            # FALLBACK: Try multiple alternative content extraction methods
            main_content = self._extract_content_fallback(soup)
            item.main_content = main_content

        # Add accordion info to main_content
        if has_accordion_content:
            if item.main_content:
                item.main_content += "\n\n--- Additional Accordion Content ---\n"
            else:
                item.main_content = "--- Accordion Content ---\n"

        # Log content extraction results
        if item.main_content and item.main_content.strip():
            logger.info(f"Successfully extracted {len(item.main_content)} characters of content for {item.title}")
        else:
            logger.warning(f"No content extracted for {item.title} - URL may be inaccessible or have no content")

        # --- IMAGE EXTRACTION (ALL .png/.jpg/.jpeg) ---
        # REMOVE global image extraction: do NOT add images from soup.select('img')

        # --- GENERIC FILE EXTRACTION ---
        # 1. <a href=...> for pdfs, images, videos
        for a in soup.find_all('a', href=True):
            href = a['href']
            if any(href.lower().endswith(ext) for ext in ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.mp4', '.mov', '.avi', '.wmv', '.webm']):
                if href not in item.associated_files:
                    item.associated_files.append(href)
        # 2. <iframe src=...> for YouTube
        for iframe in soup.find_all('iframe', src=True):
            src = iframe['src']
            if 'youtube.com' in src or 'youtu.be' in src:
                # Normalize to watch?v= form if possible
                if 'embed/' in src:
                    vid = src.split('embed/')[-1].split('?')[0]
                    yt_url = f'https://www.youtube.com/watch?v={vid}'
                else:
                    yt_url = src
                if yt_url not in item.associated_files:
                    item.associated_files.append(yt_url)
        # 3. data-settings (JSON) for youtube_url
        for el in soup.find_all(attrs={'data-settings': True}):
            import json as _json
            try:
                settings = _json.loads(el['data-settings'].replace('&quot;', '"'))
                yt_url = settings.get('youtube_url')
                if yt_url and yt_url not in item.associated_files:
                    item.associated_files.append(yt_url)
            except Exception:
                pass
        # 4. data-elementor-lightbox (JSON) for url
        for el in soup.find_all(attrs={'data-elementor-lightbox': True}):
            import json as _json
            try:
                lightbox = _json.loads(el['data-elementor-lightbox'].replace('&quot;', '"'))
                url = lightbox.get('url')
                if url and ('youtube.com' in url or 'youtu.be' in url):
                    # Normalize to watch?v= form if possible
                    if 'embed/' in url:
                        vid = url.split('embed/')[-1].split('?')[0]
                        yt_url = f'https://www.youtube.com/watch?v={vid}'
                    else:
                        yt_url = url
                    if yt_url not in item.associated_files:
                        item.associated_files.append(yt_url)
            except Exception:
                pass
        # --- END GENERIC FILE EXTRACTION ---

        # Split files into pdfs, videos, pictures, and other_files (no overlap)
        self._split_files(item)

        # At the end of _scrape_item_details, guarantee main_content is a string
        if item.main_content is None:
            item.main_content = ""

    def _extract_content_fallback(self, soup: BeautifulSoup) -> str:
        """
        Fallback content extraction using multiple methods when primary extraction fails.
        Returns the best content found or empty string.
        """
        content_candidates = []

        # Method 1: Try article content
        article = soup.find('article')
        if article:
            text = article.get_text(separator=' ', strip=True)
            if text and len(text) > 50:  # Minimum content threshold
                content_candidates.append(("article", text))

        # Method 2: Try main content area
        main_content = soup.find('main') or soup.find('div', class_='main-content') or soup.find('div', id='main-content')
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
            if text and len(text) > 50:
                content_candidates.append(("main-content", text))

        # Method 3: Try entry content
        entry_content = soup.find('div', class_='entry-content')
        if entry_content:
            text = entry_content.get_text(separator=' ', strip=True)
            if text and len(text) > 50:
                content_candidates.append(("entry-content", text))

        # Method 4: Try post content
        post_content = soup.find('div', class_='post-content') or soup.find('div', class_='content')
        if post_content:
            text = post_content.get_text(separator=' ', strip=True)
            if text and len(text) > 50:
                content_candidates.append(("post-content", text))

        # Method 5: Try all paragraphs
        paragraphs = soup.find_all('p')
        if paragraphs:
            text = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            if text and len(text) > 50:
                content_candidates.append(("paragraphs", text))

        # Method 6: Try all divs with text content
        text_divs = []
        for div in soup.find_all('div'):
            text = div.get_text(strip=True)
            if text and len(text) > 100 and not any(skip in text.lower() for skip in ['cookie', 'privacy', 'menu', 'footer', 'header']):
                text_divs.append(text)

        if text_divs:
            combined_text = ' '.join(text_divs[:5])  # Limit to first 5 divs
            if len(combined_text) > 100:
                content_candidates.append(("text-divs", combined_text))

        # Method 7: Try all text content (last resort)
        all_text = soup.get_text(separator=' ', strip=True)
        if all_text and len(all_text) > 200:
            # Clean up the text
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            cleaned_text = ' '.join(lines)
            if len(cleaned_text) > 200:
                content_candidates.append(("all-text", cleaned_text))

        # Select the best candidate based on length and quality
        if content_candidates:
            # Sort by length (prefer longer content) and method priority
            method_priority = {
                "article": 1,
                "entry-content": 2,
                "post-content": 3,
                "main-content": 4,
                "paragraphs": 5,
                "text-divs": 6,
                "all-text": 7
            }

            content_candidates.sort(key=lambda x: (len(x[1]), -method_priority.get(x[0], 0)), reverse=True)
            best_method, best_content = content_candidates[0]

            logger.info(f"Fallback content extraction successful using method: {best_method}")
            return best_content

        logger.warning("All fallback content extraction methods failed")
        return ""

    def _split_files(self, item):
        pdfs = []
        videos = []
        pictures = []
        others = []
        seen = set()
        for f in item.associated_files:
            f_clean = f.lstrip('@')
            if f_clean in seen:
                continue
            seen.add(f_clean)
            if (
                'youtube.com' in f_clean or 'youtu.be' in f_clean or
                f_clean.lower().endswith(('.mp4', '.mov', '.avi', '.wmv', '.webm'))
            ):
                videos.append(f_clean)
            elif f_clean.lower().endswith('.pdf'):
                pdfs.append(f_clean)
            elif f_clean.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg')):
                pictures.append(f_clean)
            else:
                others.append(f_clean)
        item.pdfs = pdfs
        item.videos = videos
        item.pictures = pictures
        item.other_files = others

    async def scrape_item(self, url: str, title: str = None) -> KnowledgeBaseItem:
        """
        Scrape a single item including all content types.

        Args:
            url: URL of the item to scrape
            title: Optional title for the item

        Returns:
            KnowledgeBaseItem with all content
        """
        if not title:
            title = "Item"

        item = KnowledgeBaseItem(title=title, url=url)
        await self._scrape_item_details(item)
        return item

    def save_results(self, output_path: str):
        """Save the scraped results to a file."""
        data = [item.to_dict() for item in self.items]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_to_csv(self, output_path: str):
        """Export the scraped results to a CSV file."""
        try:
            import pandas as pd
            df = pd.DataFrame([item.to_dict() for item in self.items])
            df.to_csv(output_path, index=False)
        except ImportError:
            # Fallback: manual CSV
            import csv
            data = [item.to_dict() for item in self.items]
            if not data:
                return
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                for row in data:
                    writer.writerow(row)

    def export_to_markdown(self, output_path: str):
        """Export the scraped results to a Markdown file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in self.items:
                f.write(f"# {item.title}\n")
                f.write(f"**URL:** {item.url}\n\n")
                if item.date:
                    f.write(f"**Date:** {item.date}\n\n")
                if item.item_type:
                    f.write(f"**Type:** {item.item_type}\n\n")
                if item.zones:
                    f.write(f"**Zones:** {', '.join(item.zones)}\n\n")
                if item.type_innovatie:
                    f.write(f"**Type Innovatie:** {', '.join(item.type_innovatie)}\n\n")
                if item.pdfs:
                    f.write(f"**PDFs:** {', '.join(item.pdfs)}\n\n")
                if item.videos:
                    f.write(f"**Videos:** {', '.join(item.videos)}\n\n")
                if item.pictures:
                    f.write(f"**Pictures:** {', '.join(item.pictures)}\n\n")
                if item.main_content:
                    f.write(f"## Content\n{item.main_content}\n\n")
                f.write("---\n\n")

    async def scrape_and_save(
        self,
        output_path: str = "output/scraped/versnellingsplan_knowledge_base.json"
    ):
        """Scrape the knowledge base and save the results to a file."""
        items = await self.scrape()
        self.save_results(output_path)
        return items

    def validate_main_page_items(self, items):
        failed = 0
        for idx, item in enumerate(items):
            try:
                MainPageItem(**item if isinstance(item, dict) else item.dict())
            except ValidationError as e:
                failed += 1
                if failed <= 3:
                    err = e.errors()[0]
                    reason = err.get('msg', 'Unknown error')
                    logger.error(f"MainPageItem validation error: {item.get('title', 'unknown')} ({item.get('url', 'unknown')}): {reason}")
        if failed > 3:
            logger.error(f"...and {failed-3} more main page item validation errors.")
        if failed:
            raise ValueError(f"MainPageItem validation failed for {failed} items. See logs for details.")

    def validate_items(self):
        """Validate all items using the Pydantic model and log errors."""
        from pydantic import ValidationError
        failed = 0
        sample_errors = []
        for idx, item in enumerate(self.items):
            try:
                KnowledgeBaseItemValidation(**item.to_dict())
            except ValidationError as e:
                failed += 1
                if len(sample_errors) < 3:
                    # Get main reason from first error
                    err = e.errors()[0]
                    reason = err.get('msg', 'Unknown error')
                    logger.error(f"Validation error: {item.title} ({item.url}): {reason}")
        if failed > 3:
            logger.error(f"...and {failed-3} more validation errors.")
        if failed:
            raise RuntimeError(f"Validation failed for {failed} items. See logs for details.")
        else:
            logger.info("All items validated successfully.")

    def _format_date(self, date_value) -> str:
        """
        Format date value to string, handling both datetime objects and strings.

        Args:
            date_value: Date value (datetime object or string)

        Returns:
            Formatted date string or None
        """
        if not date_value:
            return None

        if hasattr(date_value, 'isoformat'):
            return date_value.isoformat()
        elif isinstance(date_value, str):
            return date_value
        else:
            return str(date_value)

    def _clean_text_for_rag(self, text: str) -> str:
        """
        Clean text specifically for RAG applications.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text optimized for RAG
        """
        if not text:
            return ""

        import re

        # Normalize quotes and problematic characters
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('\\', '/')
        text = text.replace('\t', ' ')

        # Remove escaped quotes (both single and double)
        text = text.replace('\\"', '"')
        text = text.replace("\\'", "'")

        # Normalize newlines
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Replace all newlines with spaces (for RAG, we want continuous text)
        text = text.replace('\n', ' ')

        # Remove excessive whitespace
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single

        # Clean up and strip
        text = text.strip()

        return text

    def _create_rag_ready_chunks(self, item: KnowledgeBaseItem) -> List[Dict[str, Any]]:
        """
        Create RAG-ready chunks from a page item using text chunking logic.

        Args:
            item: KnowledgeBaseItem to chunk

        Returns:
            List of RAG-ready chunk dictionaries
        """
        chunks = []
        chunk_id = 1

        if not item.main_content or not item.main_content.strip():
            # If no main content, create a single chunk with basic info
            fallback_content = f"Page: {item.title}. URL: {item.url}"
            # Only create chunk if content is at least 50 characters
            if len(fallback_content.strip()) >= 50:
                chunk_item = {
                    'id': f"{item.title.replace(' ', '_').replace('(', '').replace(')', '')}_chunk_{chunk_id:02d}",
                    'title': item.title,
                    'content': fallback_content,
                    'source_type': 'page',
                    'sourcepage': item.url,
                    'sourcefile': None,
                    'page_number': None,
                    'date': self._format_date(item.date),
                    'zones': item.zones or [],
                    'type_innovatie': item.type_innovatie or [],
                    'pdfs': item.pdfs or [],
                    'videos': item.videos or [],
                    'pictures': item.pictures or []
                }
                chunks.append(chunk_item)
            return chunks

        # Clean the main content
        cleaned_content = self._clean_text_for_rag(item.main_content)

        # Split content into sentences for chunking
        import re
        sentences = re.split(r'[.!?]+', cleaned_content)

        current_chunk_text = ""
        current_chunk_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # If adding this sentence would make the chunk too large, save current chunk and start new one
            if len(current_chunk_text + " " + sentence) > 1500:
                if current_chunk_text:
                    # Only create chunk if content is at least 50 characters
                    if len(current_chunk_text.strip()) >= 50:
                        # Create chunk from current content
                        chunk_item = {
                            'id': f"{item.title.replace(' ', '_').replace('(', '').replace(')', '')}_chunk_{chunk_id:02d}",
                            'title': item.title,
                            'content': current_chunk_text.strip(),
                            'source_type': 'page',
                            'sourcepage': item.url,
                            'sourcefile': None,
                            'page_number': None,
                            'date': self._format_date(item.date),
                            'zones': item.zones or [],
                            'type_innovatie': item.type_innovatie or [],
                            'pdfs': item.pdfs or [],
                            'videos': item.videos or [],
                            'pictures': item.pictures or []
                        }
                        chunks.append(chunk_item)
                        chunk_id += 1

                # Start new chunk with current sentence
                current_chunk_text = sentence
                current_chunk_sentences = [sentence]
            else:
                # Add sentence to current chunk
                current_chunk_text += " " + sentence if current_chunk_text else sentence
                current_chunk_sentences.append(sentence)

        # Add final chunk if there's content
        if current_chunk_text:
            # Only create chunk if content is at least 50 characters
            if len(current_chunk_text.strip()) >= 50:
                chunk_item = {
                    'id': f"{item.title.replace(' ', '_').replace('(', '').replace(')', '')}_chunk_{chunk_id:02d}",
                    'title': item.title,
                    'content': current_chunk_text.strip(),
                    'source_type': 'page',
                    'sourcepage': item.url,
                    'sourcefile': None,
                    'page_number': None,
                    'date': self._format_date(item.date),
                    'zones': item.zones or [],
                    'type_innovatie': item.type_innovatie or [],
                    'pdfs': item.pdfs or [],
                    'videos': item.videos or [],
                    'pictures': item.pictures or []
                }
                chunks.append(chunk_item)

        # If no chunks were created (content was too short), create a single chunk
        if not chunks:
            # Only create chunk if content is at least 50 characters
            if len(cleaned_content.strip()) >= 50:
                chunk_item = {
                    'id': f"{item.title.replace(' ', '_').replace('(', '').replace(')', '')}_chunk_01",
                    'title': item.title,
                    'content': cleaned_content,
                    'source_type': 'page',
                    'sourcepage': item.url,
                    'sourcefile': None,
                    'page_number': None,
                    'date': self._format_date(item.date),
                    'zones': item.zones or [],
                    'type_innovatie': item.type_innovatie or [],
                    'pdfs': item.pdfs or [],
                    'videos': item.videos or [],
                    'pictures': item.pictures or []
                }
                chunks.append(chunk_item)

        return chunks

    def create_rag_ready_output(self, output_path: str = None) -> List[Dict[str, Any]]:
        """
        Create RAG-ready chunks from all scraped items and optionally save to file.

        Args:
            output_path: Optional path to save the RAG-ready output

        Returns:
            List of RAG-ready chunk dictionaries
        """
        all_chunks = []

        for item in self.items:
            chunks = self._create_rag_ready_chunks(item)
            all_chunks.extend(chunks)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_chunks, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(all_chunks)} RAG-ready chunks to {output_path}")

        return all_chunks
