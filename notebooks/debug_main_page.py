#!/usr/bin/env python3
"""
Debug script to understand why main page scraping returns 0 items.
"""

import asyncio
import sys
from pathlib import Path
from bs4 import BeautifulSoup

# Add the src directory to Python path  
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag_scraping.config import load_config_with_paths
from rag_scraping.scraping import scrape_with_retry


async def debug_main_page():
    """Debug main page scraping to see what's wrong."""
    print("🐛 Debugging Main Page Scraping")
    print("=" * 40)
    
    try:
        # Load configuration
        config_path = Path(__file__).parent.parent / "config.yaml"
        config = load_config_with_paths(config_path=config_path, run_type="production")
        
        base_url = config['scraping']['base_url']
        print(f"🌐 Fetching: {base_url}")
        
        # Fetch the main page
        result = await scrape_with_retry(base_url, config)
        
        if not result or not result.success:
            print("❌ Failed to fetch main page")
            return
            
        print(f"✅ Successfully fetched page")
        print(f"📄 HTML length: {len(result.html) if result.html else 0} characters")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(result.html, 'html.parser')
        
        # Check what we find
        item_divs = soup.find_all('div', class_='elementor-post__card')
        print(f"🔍 Found {len(item_divs)} div.elementor-post__card elements")
        
        # Check for any divs with similar classes
        all_divs = soup.find_all('div')
        elementor_divs = [div for div in all_divs if div.get('class') and any('elementor' in cls for cls in div.get('class', []))]
        print(f"📊 Total divs: {len(all_divs)}")
        print(f"📊 Elementor divs: {len(elementor_divs)}")
        
        # Show some sample class names
        unique_classes = set()
        for div in all_divs[:100]:  # Sample first 100 divs
            if div.get('class'):
                for cls in div.get('class'):
                    if 'elementor' in cls or 'post' in cls or 'card' in cls:
                        unique_classes.add(cls)
        
        print(f"🏷️  Relevant classes found: {sorted(unique_classes)}")
        
        # Check page title to make sure we got the right page
        title = soup.find('title')
        print(f"📝 Page title: {title.get_text() if title else 'No title found'}")
        
        # Look for any error messages or unusual content
        body = soup.find('body')
        if body:
            body_text = body.get_text()[:500]  # First 500 chars
            print(f"📄 Body text preview: {body_text}")
            
            # Check for error messages
            if any(error in body_text.lower() for error in ['error', 'not found', 'maintenance', 'unavailable']):
                print("⚠️  Potential error detected in page content")
        
    except Exception as e:
        print(f"❌ Debug failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_main_page())