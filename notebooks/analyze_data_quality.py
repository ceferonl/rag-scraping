#!/usr/bin/env python3
"""
Data Quality Analysis Script for RAG Scraping

This script analyzes the quality of scraped data and identifies issues that need to be fixed.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def analyze_detailed_items(file_path: str):
    """Analyze detailed items for data quality issues."""
    print(f"\n=== Analyzing Detailed Items: {file_path} ===")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_items = len(data)
    empty_content_items = []
    short_content_items = []

    for item in data:
        content = item.get('main_content', '')
        title = item.get('title', 'Unknown')

        if not content or not content.strip():
            empty_content_items.append({
                'title': title,
                'url': item.get('url', ''),
                'item_type': item.get('item_type', ''),
                'content_length': len(content)
            })
        elif len(content.strip()) < 100:
            short_content_items.append({
                'title': title,
                'url': item.get('url', ''),
                'content_length': len(content.strip()),
                'content_preview': content.strip()[:100]
            })

    print(f"Total items: {total_items}")
    print(f"Items with empty content: {len(empty_content_items)}")
    print(f"Items with short content (<100 chars): {len(short_content_items)}")

    if empty_content_items:
        print(f"\n--- Items with Empty Content ---")
        for item in empty_content_items[:10]:  # Show first 10
            print(f"  • {item['title']} ({item['item_type']})")
            print(f"    URL: {item['url']}")
        if len(empty_content_items) > 10:
            print(f"    ... and {len(empty_content_items) - 10} more")

    if short_content_items:
        print(f"\n--- Items with Short Content ---")
        for item in short_content_items[:5]:  # Show first 5
            print(f"  • {item['title']} ({item['content_length']} chars)")
            print(f"    Preview: {item['content_preview']}")

    return {
        'total_items': total_items,
        'empty_content_count': len(empty_content_items),
        'short_content_count': len(short_content_items),
        'empty_content_items': empty_content_items,
        'short_content_items': short_content_items
    }


def analyze_rag_ready_chunks(file_path: str):
    """Analyze RAG-ready chunks for data quality issues."""
    print(f"\n=== Analyzing RAG-Ready Chunks: {file_path} ===")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_chunks = len(data)
    small_chunks = []
    empty_chunks = []

    for chunk in data:
        content = chunk.get('content', '')
        title = chunk.get('title', 'Unknown')

        if not content or not content.strip():
            empty_chunks.append({
                'title': title,
                'id': chunk.get('id', ''),
                'content': repr(content)
            })
        elif len(content.strip()) < 50:
            small_chunks.append({
                'title': title,
                'id': chunk.get('id', ''),
                'content_length': len(content.strip()),
                'content': content.strip()
            })

    print(f"Total chunks: {total_chunks}")
    print(f"Chunks with empty content: {len(empty_chunks)}")
    print(f"Chunks with small content (<50 chars): {len(small_chunks)}")

    if empty_chunks:
        print(f"\n--- Chunks with Empty Content ---")
        for chunk in empty_chunks[:5]:
            print(f"  • {chunk['title']} (ID: {chunk['id']})")
            print(f"    Content: {chunk['content']}")

    if small_chunks:
        print(f"\n--- Chunks with Small Content ---")
        for chunk in small_chunks[:10]:
            print(f"  • {chunk['title']} ({chunk['content_length']} chars)")
            print(f"    Content: {repr(chunk['content'])}")
        if len(small_chunks) > 10:
            print(f"    ... and {len(small_chunks) - 10} more")

    return {
        'total_chunks': total_chunks,
        'empty_chunks_count': len(empty_chunks),
        'small_chunks_count': len(small_chunks),
        'empty_chunks': empty_chunks,
        'small_chunks': small_chunks
    }


def generate_report(output_dir: str = "output/demo"):
    """Generate a comprehensive data quality report."""
    output_path = Path(output_dir)

    # Find the most recent files
    detailed_files = list(output_path.glob("detailed_items_*.json"))
    rag_files = list(output_path.glob("rag_ready_*.json"))

    if not detailed_files:
        print("No detailed items files found!")
        return

    if not rag_files:
        print("No RAG-ready files found!")
        return

    latest_detailed = max(detailed_files, key=lambda f: f.stat().st_mtime)
    latest_rag = max(rag_files, key=lambda f: f.stat().st_mtime)

    print("=" * 60)
    print("RAG SCRAPING DATA QUALITY ANALYSIS")
    print("=" * 60)
    print(f"Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Analyze both file types
    detailed_analysis = analyze_detailed_items(str(latest_detailed))
    rag_analysis = analyze_rag_ready_chunks(str(latest_rag))

    # Generate summary
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_issues = (
        detailed_analysis['empty_content_count'] +
        detailed_analysis['short_content_count'] +
        rag_analysis['empty_chunks_count'] +
        rag_analysis['small_chunks_count']
    )

    print(f"Total data quality issues found: {total_issues}")
    print(f"  - Empty content items: {detailed_analysis['empty_content_count']}")
    print(f"  - Short content items: {detailed_analysis['short_content_count']}")
    print(f"  - Empty chunks: {rag_analysis['empty_chunks_count']}")
    print(f"  - Small chunks: {rag_analysis['small_chunks_count']}")

    if total_issues > 0:
        print(f"\n⚠️  RECOMMENDATIONS:")
        print(f"  1. Re-scrape items with empty content")
        print(f"  2. Improve content extraction for short content")
        print(f"  3. Review chunking strategy for small chunks")
        print(f"  4. Check if website structure has changed")
    else:
        print(f"\n✅ All data quality checks passed!")

    # Save detailed report
    report_file = output_path / f"data_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_data = {
        'analysis_time': datetime.now().isoformat(),
        'detailed_items_analysis': detailed_analysis,
        'rag_chunks_analysis': rag_analysis,
        'total_issues': total_issues
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Detailed report saved to: {report_file}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_dir = "output/demo"

    generate_report(output_dir)
