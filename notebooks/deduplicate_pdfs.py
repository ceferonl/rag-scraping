#!/usr/bin/env python3
"""
Temporary script to remove duplicate PDFs from existing production data.
This fixes the duplicate PDF issue in detailed_items.json files.
"""

import json
from pathlib import Path
from collections import Counter


def deduplicate_pdfs_in_file(file_path: Path) -> dict:
    """
    Remove duplicate PDFs from a detailed_items.json file.

    Args:
        file_path: Path to the JSON file to fix

    Returns:
        Dictionary with statistics about the deduplication
    """
    print(f"🔧 Processing: {file_path}")

    # Load the data
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stats = {
        'total_items': len(data),
        'items_with_pdfs': 0,
        'total_pdf_refs_before': 0,
        'total_pdf_refs_after': 0,
        'duplicates_removed': 0,
        'items_fixed': 0
    }

    # Process each item
    for item in data:
        if 'pdfs' in item and item['pdfs']:
            stats['items_with_pdfs'] += 1
            original_count = len(item['pdfs'])
            stats['total_pdf_refs_before'] += original_count

            # Remove duplicates while preserving order
            seen = set()
            unique_pdfs = []
            for pdf_url in item['pdfs']:
                if pdf_url not in seen:
                    seen.add(pdf_url)
                    unique_pdfs.append(pdf_url)

            # Update the item
            item['pdfs'] = unique_pdfs
            new_count = len(unique_pdfs)
            stats['total_pdf_refs_after'] += new_count

            if original_count != new_count:
                stats['items_fixed'] += 1
                duplicates = original_count - new_count
                stats['duplicates_removed'] += duplicates
                print(f"  ✓ Fixed '{item.get('title', 'Unknown')}': {original_count} → {new_count} PDFs (-{duplicates})")

    # Save the fixed data
    backup_path = file_path.with_suffix('.backup.json')
    file_path.rename(backup_path)
    print(f"📁 Backup created: {backup_path}")

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"💾 Updated file saved: {file_path}")

    return stats


def main():
    """Main function to deduplicate PDFs in production files."""
    print("🚀 PDF Deduplication Script")
    print("=" * 50)

    project_root = Path(__file__).parent.parent

    # Find all detailed_items files in production
    production_dir = project_root / "output" / "production"
    json_files = list(production_dir.glob("detailed_items_*.json"))

    if not json_files:
        print("❌ No detailed_items files found in production!")
        return

    print(f"📁 Found {len(json_files)} detailed_items files:")
    for file_path in sorted(json_files):
        print(f"  - {file_path.name}")

    print()

    total_stats = {
        'files_processed': 0,
        'total_items': 0,
        'items_with_pdfs': 0,
        'total_duplicates_removed': 0,
        'items_fixed': 0
    }

    # Process each file
    for file_path in sorted(json_files):
        stats = deduplicate_pdfs_in_file(file_path)

        total_stats['files_processed'] += 1
        total_stats['total_items'] += stats['total_items']
        total_stats['items_with_pdfs'] += stats['items_with_pdfs']
        total_stats['total_duplicates_removed'] += stats['duplicates_removed']
        total_stats['items_fixed'] += stats['items_fixed']

        print(f"  📊 Stats: {stats['items_fixed']} items fixed, {stats['duplicates_removed']} duplicates removed")
        print()

    # Final summary
    print("✅ PDF Deduplication Complete!")
    print("=" * 50)
    print(f"📁 Files processed: {total_stats['files_processed']}")
    print(f"📄 Total items: {total_stats['total_items']}")
    print(f"📎 Items with PDFs: {total_stats['items_with_pdfs']}")
    print(f"🔧 Items fixed: {total_stats['items_fixed']}")
    print(f"🗑️  Total duplicates removed: {total_stats['total_duplicates_removed']}")

    if total_stats['total_duplicates_removed'] > 0:
        print(f"\n🎉 Successfully removed {total_stats['total_duplicates_removed']} duplicate PDF references!")
    else:
        print("\n✨ No duplicates found - all files were already clean!")


if __name__ == "__main__":
    main()
