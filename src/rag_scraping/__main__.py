"""
Main entry point for the Versnellingsplan scraper.
"""

import asyncio
from pathlib import Path

from .versnellingsplan import VersnellingsplanScraper


async def main():
    # Create output directory if it doesn't exist
    output_dir = Path("output/scraped")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize and run the scraper
    scraper = VersnellingsplanScraper()
    await scraper.scrape_knowledge_base()

    # Save results
    output_file = output_dir / "versnellingsplan_data.json"
    scraper.save_results(str(output_file))
    print(f"Results saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
