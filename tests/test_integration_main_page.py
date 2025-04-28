"""
Integration test for scraping the main page from the Versnellingsplan knowledge base.
This test serves as check to ensure the scraper continues to work with the main page.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from rag_scraping.versnellingsplan import VersnellingsplanScraper


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_main_page():
    """
    Test scraping the main knowledge base page from the Versnellingsplan website.
    This test ensures that the scraper can correctly extract items from the main page.
    """
    # Create a scraper instance
    scraper = VersnellingsplanScraper()

    # Scrape the knowledge base
    print("Starting scraping process...")
    items = await scraper.scrape()
    print(f"Scraping completed. Found {len(items)} items.")

    # Basic validation
    assert len(items) > 0, "Should find at least one item"

    # More specific assertions about the items
    for item in items:
        assert item.title, "Each item should have a title"
        assert item.url, "Each item should have a URL"
        assert item.url.startswith("https://www.versnellingsplan.nl/"), (
            "URLs should be from versnellingsplan.nl"
        )
        assert item.main_content is not None, "Each item should have main content"
        assert item.zones is not None, "Each item should have zones list"
        assert item.type_innovatie is not None, (
            "Each item should have type_innovatie list"
        )

    # Check for specific known items that should be on the main page
    known_items = [
        "Quickscan gebruik open leermaterialen",
        "Versnellingsplan",
        "Kennisbank"
    ]

    found_known_items = [
        item.title for item in items
        if any(known in item.title for known in known_items)
    ]
    assert len(found_known_items) > 0, "Should find at least some known items"

    # Check for different item types
    item_types = [item.item_type for item in items if item.item_type]
    expected_types = ["Product", "Publicatie", "Project"]
    found_types = [t for t in expected_types if t in item_types]
    assert len(found_types) > 0, (
        f"Should find at least some of the expected item types: {expected_types}"
    )

    # Optional: Save the output for manual inspection
    output_dir = Path("output/test")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"test_integration_main_page_{timestamp}.json"

    # Save a sample of items for manual inspection
    sample_items = items[:5]
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(
            [item.to_dict() for item in sample_items],
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\nTest completed!")
    print(f"Total items found: {len(items)}")
    print(f"Output saved to: {output_file}")

    # Print some statistics
    print("\nItem statistics:")
    print(f"Total items: {len(items)}")
    print(f"Item types found: {', '.join(item_types)}")
    print(f"Known items found: {', '.join(found_known_items)}")

    # Return the items for potential further testing
    return items


@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_load_results():
    """Test saving and loading results from a live scrape."""
    scraper = VersnellingsplanScraper()

    # Scrape a small sample
    print("Starting scraping process for save/load test...")
    items = await scraper.scrape()
    print(f"Scraping completed. Found {len(items)} items.")

    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        output_path = tmp.name

    try:
        scraper.save_results(output_path)

        # Verify the file exists and has content
        assert Path(output_path).exists(), "Output file should be created"
        assert Path(output_path).stat().st_size > 0, "Output file should not be empty"

        # Load and validate the JSON structure
        import json
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert isinstance(data, list), "Should be a list of items"
        assert len(data) == len(items), "Should have same number of items"

        # Validate first item structure
        first_item = data[0]
        assert 'title' in first_item
        assert 'url' in first_item
        assert 'main_content' in first_item
        assert 'date' in first_item or first_item['date'] is None
        assert 'item_type' in first_item or first_item['item_type'] is None
        assert 'associated_files' in first_item
        assert 'zones' in first_item
        assert 'type_innovatie' in first_item

    finally:
        # Cleanup
        Path(output_path).unlink(missing_ok=True)

