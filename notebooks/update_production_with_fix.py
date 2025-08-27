#!/usr/bin/env python3
"""
Update the latest production detailed_items.json with fixes from stubborn pages script.
"""

import json
from pathlib import Path
from datetime import datetime


def update_production_with_fixes():
    """Update production file with fixed stubborn pages."""
    print("🔄 Updating Production File with Fixes")
    print("=" * 50)

    # Paths
    project_root = Path(__file__).parent.parent
    production_file = project_root / "output/production/detailed_items_20250827_145536.json"

    # Find the latest stubborn pages fix
    fix_files = list((project_root / "output/production").glob("stubborn_pages_fixed_*.json"))
    if not fix_files:
        print("❌ No stubborn pages fix file found!")
        return

    latest_fix = sorted(fix_files)[-1]
    print(f"📥 Production file: {production_file}")
    print(f"🔧 Fix file: {latest_fix}")

    # Load both files
    with open(production_file, 'r', encoding='utf-8') as f:
        production_data = json.load(f)

    with open(latest_fix, 'r', encoding='utf-8') as f:
        fix_data = json.load(f)

    print(f"📊 Production items: {len(production_data)}")
    print(f"🔧 Fix items: {len(fix_data)}")

    # Update production data with fixes
    updates_made = 0
    for fix_item in fix_data:
        fix_title = fix_item['title']
        fix_url = fix_item['url']

        # Find the corresponding item in production data
        for i, prod_item in enumerate(production_data):
            if (prod_item['title'] == fix_title or
                prod_item['url'] == fix_url):

                print(f"🔄 Updating: {fix_title}")
                print(f"   📄 Old content: {len(prod_item.get('main_content', ''))} chars")
                print(f"   📄 New content: {len(fix_item.get('main_content', ''))} chars")

                # Replace the entire item with the fixed version
                production_data[i] = fix_item
                updates_made += 1
                break

    if updates_made == 0:
        print("⚠️  No matching items found to update!")
        return

    # Create backup of original
    backup_file = production_file.with_suffix('.json.backup')
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(production_data, f, indent=2, ensure_ascii=False)
    print(f"💾 Backup created: {backup_file}")

    # Save updated production file
    with open(production_file, 'w', encoding='utf-8') as f:
        json.dump(production_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated {updates_made} items in production file")
    print(f"💾 Updated file: {production_file}")

    # Show summary
    print(f"\n📈 Summary:")
    print(f"   Total items: {len(production_data)}")
    print(f"   Items updated: {updates_made}")

    # Count success rate after update
    failed_items = sum(1 for item in production_data
                      if item.get('main_content', '').startswith('Failed to scrape after'))
    success_items = len(production_data) - failed_items
    success_rate = (success_items / len(production_data)) * 100

    print(f"   Successful items: {success_items}")
    print(f"   Failed items: {failed_items}")
    print(f"   Success rate: {success_rate:.1f}%")


if __name__ == "__main__":
    update_production_with_fixes()
