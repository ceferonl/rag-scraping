import asyncio
import json
from datetime import datetime
from pathlib import Path

from rag_scraping.versnellingsplan import VersnellingsplanScraper


async def scrape_entire_site():
    print("Starting site scrape...")
    scraper = VersnellingsplanScraper()

    # Create output directories if they don't exist
    output_dir = Path("output/scraped")
    logs_dir = Path("output/logs")
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Scrape the site
    items = await scraper.scrape()

    # Prepare output data
    output_data = {
        "scrape_date": datetime.now().isoformat(),
        "total_items": len(items),
        "items": []
    }

    # Process each item
    for item in items:
        item_data = {
            "title": item.title,
            "url": item.url,
            "item_type": item.item_type,
            "date": item.date.isoformat() if item.date else None,
            "content_length": len(item.main_content) if item.main_content else 0,
            "zones": item.zones,
            "type_innovatie": item.type_innovatie,
            "associated_files": item.associated_files
        }
        output_data["items"].append(item_data)

    # Save to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"versnellingsplan_scrape_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    # Prepare statistics
    stats = {
        "scrape_date": datetime.now().isoformat(),
        "total_items": len(items),
        "items_with_content": sum(1 for item in items if item.main_content),
        "items_with_files": sum(1 for item in items if item.associated_files),
        "items_by_type": {},
        "items_by_zone": {},
        "items_by_innovatie": {}
    }

    # Count items by type
    for item in items:
        if item.item_type:
            stats["items_by_type"][item.item_type] = (
                stats["items_by_type"].get(item.item_type, 0) + 1
            )

        for zone in item.zones:
            stats["items_by_zone"][zone] = stats["items_by_zone"].get(zone, 0) + 1

        for innovatie in item.type_innovatie:
            stats["items_by_innovatie"][innovatie] = (
                stats["items_by_innovatie"].get(innovatie, 0) + 1
            )

    # Save statistics to logs
    stats_file = logs_dir / f"scrape_stats_{timestamp}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print("\nScraping completed!")
    print(f"Total items scraped: {len(items)}")
    print(f"Output saved to: {output_file}")
    print(f"Statistics saved to: {stats_file}")

    # Print statistics
    print("\nStatistics:")
    print(f"- Total items: {stats['total_items']}")
    print(f"- Items with content: {stats['items_with_content']}")
    print(f"- Items with files: {stats['items_with_files']}")
    print("\nItems by type:")
    for item_type, count in stats["items_by_type"].items():
        print(f"- {item_type}: {count}")
    print("\nItems by zone:")
    for zone, count in stats["items_by_zone"].items():
        print(f"- {zone}: {count}")
    print("\nItems by innovatie type:")
    for innovatie, count in stats["items_by_innovatie"].items():
        print(f"- {innovatie}: {count}")

if __name__ == "__main__":
    asyncio.run(scrape_entire_site())
