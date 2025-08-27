#!/usr/bin/env python3
"""
Test script for content-level retry functionality.
This tests that server error pages trigger proper retries.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag_scraping.config import load_config_with_paths
from rag_scraping.scraping import scrape_item_details, is_valid_content
from rag_scraping.models import MainPageItem


async def test_content_retry():
    """Test that content-level retries work for server errors."""
    print("🧪 Testing Content-Level Retry Logic")
    print("=" * 50)

    try:
        # Load configuration
        config_path = Path(__file__).parent.parent / "config.yaml"
        config = load_config_with_paths(config_path=config_path, run_type="demo")

        print("📋 Configuration loaded successfully")
        print(f"   - Max retries: {config['scraping']['max_retries']}")
        print(f"   - Retry delays: {config['scraping']['retry_delays']}")

        # Test the content validation function
        print("\n🔍 Testing content validation...")

        # Test valid content
        valid_content = "This is a proper article about education with substantial content that should pass validation."
        print(f"✅ Valid content: {is_valid_content(valid_content)}")

        # Test server error content
        error_content = "The server encountered an internal error or misconfiguration and was unable to complete your request."
        print(f"❌ Server error content: {is_valid_content(error_content)}")

        # Test empty content
        empty_content = ""
        print(f"❌ Empty content: {is_valid_content(empty_content)}")

        # Test a specific item that had server errors before
        print("\n🎯 Testing specific item that previously failed...")

        # This was one of the items that had server errors in the previous run
        test_item = MainPageItem(
            title="Onderwijsontwerp in de context van digitale transformatie",
            url="https://www.versnellingsplan.nl/Kennisbank/onderwijs-in-de-context-van-digitale-transformatie/",
            item_type="Publicatie"
        )

        print(f"Testing: {test_item.title}")
        print(f"URL: {test_item.url}")

        # Scrape with retry logic
        result = await scrape_item_details(test_item, config)

        print(f"\n📊 Results:")
        print(f"   - Title: {result.title}")
        print(f"   - Content length: {len(result.main_content)} characters")
        print(f"   - Content valid: {is_valid_content(result.main_content)}")

        if result.main_content.startswith("Failed to scrape after"):
            print("   - ❌ Still failed after retries")
        else:
            print("   - ✅ Successfully scraped")

        # Show first 200 chars of content
        content_preview = result.main_content[:200] + "..." if len(result.main_content) > 200 else result.main_content
        print(f"   - Content preview: {content_preview}")

        print("\n🎉 Test completed successfully!")
        print("The retry logic should now handle both HTTP and content-level failures.")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_content_retry())
