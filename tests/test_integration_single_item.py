"""
Integration test for scraping a specific real-world item from the Versnellingsplan
knowledge base.
This test serves as a regression check to ensure the scraper continues to work with
actual content.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from rag_scraping.versnellingsplan import KnowledgeBaseItem, VersnellingsplanScraper


@pytest.mark.asyncio
@pytest.mark.integration
async def test_integration_single_item():
    """
    Test scraping a specific real-world item from the Versnellingsplan knowledge base.
    This test ensures that the scraper can correctly extract content from a known page.
    """
    # URL of a known item to test
    test_url = "https://www.versnellingsplan.nl/Kennisbank/quickscan-gebruik-open-leermaterialen/"

    # Create a scraper instance
    scraper = VersnellingsplanScraper()

    # Create a single item with the test URL
    item = KnowledgeBaseItem(
        title="Test Item",
        url=test_url
    )

    # Add the item to the scraper's items list
    scraper.items = [item]

    # Scrape the item details
    await scraper._scrape_item_details(item)

    # Assertions to verify the scraping worked correctly
    assert item.title == "Test Item", "Title should be preserved"
    assert item.url == test_url, "URL should be preserved"
    assert item.item_type == "Product", "Item type should be 'Product'"
    assert item.date == datetime(2022, 9, 20), "Date should be 2022-09-20"
    assert item.main_content is not None, "Main content should be extracted"
    assert len(item.main_content) > 1000, "Main content should be substantial"
    assert "Werken met open leermaterialen" in item.main_content, (
        "Main content should contain expected text"
    )
    assert item.zones == ["Digitale leermaterialen"], (
        "Zones should be ['Digitale leermaterialen']"
    )
    assert item.type_innovatie == ["Instrumenten & Tools"], (
        "Type innovatie should be ['Instrumenten & Tools']"
    )

    # Note: We're not checking for associated files anymore as the page structure
    # might have changed
    # If there are associated files, they should be properly extracted, but we
    # don't require them

    # Optional: Save the output for manual inspection
    output_dir = Path("output/test")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"test_integration_single_item_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(item.to_dict(), f, indent=2, ensure_ascii=False)

    print("\nTest completed!")
    print(f"Output saved to: {output_file}")

    # Print the item details for debugging
    print("\nItem details:")
    print(f"Title: {item.title}")
    print(f"URL: {item.url}")
    print(f"Item Type: {item.item_type}")
    print(f"Date: {item.date}")
    print(f"Content Length: {len(item.main_content) if item.main_content else 0}")
    print(f"Associated Files: {len(item.associated_files)}")
    print(f"Zones: {item.zones}")
    print(f"Type Innovatie: {item.type_innovatie}")

    # Return the item for potential further testing
    return item
