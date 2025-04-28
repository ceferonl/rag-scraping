"""
Versnellingsplan Knowledge Base Scraper

This module provides functionality to scrape the Versnellingsplan knowledge base,
including metadata, content, and associated files.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler


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

    def __post_init__(self):
        if self.associated_files is None:
            self.associated_files = []
        if self.zones is None:
            self.zones = []
        if self.type_innovatie is None:
            self.type_innovatie = []

    def to_dict(self):
        """Convert the item to a dictionary for JSON serialization."""
        data = asdict(self)
        if self.date:
            data['date'] = self.date.isoformat()
        return data


class VersnellingsplanScraper:
    """Scraper for the Versnellingsplan knowledge base."""

    def __init__(self, base_url: str = "https://www.versnellingsplan.nl/kennisbank/"):
        self.base_url = base_url
        self.crawler = AsyncWebCrawler()
        self.items: List[KnowledgeBaseItem] = []

    async def scrape(self) -> List[KnowledgeBaseItem]:
        """Scrape the knowledge base and return a list of items."""
        print(f"Scraping main page: {self.base_url}")
        result = await self.crawler.arun(self.base_url)
        if result.success:
            soup = BeautifulSoup(result.html, 'html.parser')

            # Find all knowledge base items
            for item_div in soup.find_all('div', class_='elementor-post__card'):
                # Extract title and URL from the link
                title_link = item_div.select_one('a.elementor-post__thumbnail__link')
                if not title_link:
                    continue

                url = title_link.get('href')
                if not url:
                    continue

                # Extract title from the text div
                title_elem = item_div.select_one('div.elementor-post__text a')
                title = title_elem.get_text(strip=True) if title_elem else None

                # Extract type from badge if present
                badge = item_div.select_one('div.elementor-post__badge')
                item_type = badge.get_text(strip=True) if badge else None

                if title and url:
                    item = KnowledgeBaseItem(
                        title=title,
                        url=url,
                        item_type=item_type
                    )
                    print(f"Scraping item: {title}")
                    await self._scrape_item_details(item)
                    self.items.append(item)

        return self.items

    async def _scrape_item_details(self, item: KnowledgeBaseItem) -> None:
        """Scrape additional details for a knowledge base item."""
        result = await self.crawler.arun(item.url)
        if result.success:
            soup = BeautifulSoup(result.html, 'html.parser')

            # Extract metadata from the info list - use a more generic selector
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
                        section_text = '\n'.join(
                            editor.get_text(strip=True) for editor in text_editors
                        )
                        if section_text:
                            # If we already have content, append with a separator
                            if item.main_content:
                                item.main_content += "\n\n" + section_text
                            else:
                                item.main_content = section_text

            # If we still don't have content, try a more generic approach
            if not item.main_content:
                text_elements = soup.select(
                    'div.elementor-widget-text-editor div.elementor-widget-container'
                )
                if text_elements:
                    item.main_content = '\n'.join(
                        elem.get_text(strip=True) for elem in text_elements
                    )

            # Extract file attachments
            file_links = soup.select(
                'a[href$=".pdf"], a[href$=".doc"], a[href$=".docx"], '
                'a[href$=".ppt"], a[href$=".pptx"]'
            )
            if file_links:
                item.associated_files = [link['href'] for link in file_links]

    def save_results(self, output_path: str):
        """Save the scraped results to a file."""
        data = [item.to_dict() for item in self.items]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def scrape_and_save(
        self,
        output_path: str = "output/scraped/versnellingsplan_knowledge_base.json"
    ):
        """Scrape the knowledge base and save the results to a file."""
        items = await self.scrape()
        self.save_results(output_path)
        return items
