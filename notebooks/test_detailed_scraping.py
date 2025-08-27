#!/usr/bin/env python3
"""
Test script for improved detailed scraping with enhanced delays and logging.
This script focuses specifically on testing detailed items scraping.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag_scraping.config import load_config_with_paths
from rag_scraping.pipeline import scrape_detailed_items


async def test_detailed_scraping():
    """Test detailed scraping with improved delays and logging."""
    print("🚀 Testing improved detailed scraping...")

    try:
        # Load configuration from parent directory
        config_path = Path(__file__).parent.parent / "config.yaml"
        config = load_config_with_paths(config_path=config_path, run_type="demo")

        # Test with only 5 items to verify the improvements
        print(f"📋 Configuration loaded with delays:")
        print(f"   - Request delay: {config['scraping']['request_delay']}s")
        print(f"   - Main page to details delay: {config['scraping']['main_page_to_details_delay']}s")
        print(f"   - Min/Max delay: {config['scraping']['min_delay']}-{config['scraping']['max_delay']}s")

        print("\n📡 Starting detailed scraping test (max 5 items)...")

        # Run the improved scraping function
        detailed_items, stats = await scrape_detailed_items(
            config=config,
            max_items=5,  # Small test sample
            filter_type=None
        )

        print("\n📊 Test Results:")
        print(f"   ✅ Total items processed: {stats['total_items']}")
        print(f"   ✅ Successful scrapes: {stats['successful_scrapes']}")
        print(f"   ❌ Failed scrapes: {stats['failed_scrapes']}")
        print(f"   🚨 Server errors: {stats['server_errors']}")
        print(f"   📈 Success rate: {stats['success_rate']:.1f}%")
        print(f"   ⏱️  Duration: {stats['duration']}")

        # Check for server errors specifically
        server_error_items = []
        for item in detailed_items:
            if "server encountered an internal error" in item.main_content.lower():
                server_error_items.append(item.title)

        if server_error_items:
            print(f"\n🔍 Items with server errors ({len(server_error_items)}):")
            for title in server_error_items:
                print(f"   - {title}")
        else:
            print("\n✨ No server errors detected!")

        # Show log file locations
        print(f"\n📁 Check logs in:")
        print(f"   - Detailed log: output/demo/logs/detailed_log_{config['timestamp']}.log")
        print(f"   - Summary: output/demo/logs/log_summary_{config['timestamp']}.md")

        print(f"\n💾 Output saved to: output/demo/detailed_items_{config['timestamp']}.json")

        return stats['server_errors'] == 0  # Return True if no server errors

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to run the test."""
    print("🧪 Detailed Scraping Test")
    print("=" * 50)

    success = asyncio.run(test_detailed_scraping())

    print("\n" + "=" * 50)
    if success:
        print("✅ TEST PASSED: No server errors detected!")
        print("💡 The improved delays and logging are working correctly.")
    else:
        print("⚠️  TEST NEEDS REVIEW: Check the logs for server errors.")
        print("💡 Consider increasing delays further if server errors persist.")
    print("=" * 50)


if __name__ == "__main__":
    main()
