#!/usr/bin/env python3
"""
Create RAG-ready chunks from detailed items.

This script takes detailed items (from re-scraping) and converts them to RAG-ready chunks
using the existing chunking logic in the VersnellingsplanScraper.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from rag_scraping.pages import VersnellingsplanScraper, KnowledgeBaseItem

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def load_detailed_items(file_path: str) -> List[Dict[str, Any]]:
    """Load detailed items from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def convert_to_knowledge_base_items(detailed_items: List[Dict[str, Any]]) -> List[KnowledgeBaseItem]:
    """Convert detailed items to KnowledgeBaseItem objects."""
    items = []

    for item_data in detailed_items:
        item = KnowledgeBaseItem(
            title=item_data.get('title', ''),
            url=item_data.get('url', ''),
            date=item_data.get('date'),
            zones=item_data.get('zones', []),
            type_innovatie=item_data.get('type_innovatie', []),
            pdfs=item_data.get('pdfs', []),
            videos=item_data.get('videos', []),
            pictures=item_data.get('pictures', []),
            main_content=item_data.get('main_content', '')
        )
        items.append(item)

    return items

def main():
    """Main function to create RAG-ready chunks from detailed items."""
    # Configuration
    input_file = "output/demo/rescraped_items_20250718_195101.json"
    output_dir = "output/demo"

    # Check if input file exists
    if not Path(input_file).exists():
        logger.error(f"Input file not found: {input_file}")
        return

    logger.info(f"Loading detailed items from: {input_file}")

    # Load detailed items
    detailed_items = load_detailed_items(input_file)
    logger.info(f"Loaded {len(detailed_items)} detailed items")

    # Convert to KnowledgeBaseItem objects
    knowledge_base_items = convert_to_knowledge_base_items(detailed_items)
    logger.info(f"Converted to {len(knowledge_base_items)} KnowledgeBaseItem objects")

    # Create scraper and set items
    scraper = VersnellingsplanScraper()
    scraper.items = knowledge_base_items

    # Create RAG-ready chunks
    logger.info("Creating RAG-ready chunks...")
    rag_ready_chunks = scraper.create_rag_ready_output()

    logger.info(f"Created {len(rag_ready_chunks)} RAG-ready chunks")

    # Save RAG-ready chunks
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = Path(output_dir) / f"detailed_items_rag_ready_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rag_ready_chunks, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved RAG-ready chunks to: {output_file}")

    # Print summary
    print(f"\n=== RAG-Ready Chunks Summary ===")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Total detailed items: {len(detailed_items)}")
    print(f"Total RAG-ready chunks: {len(rag_ready_chunks)}")

    # Analyze chunk sizes
    small_chunks = [c for c in rag_ready_chunks if len(c.get('content', '').strip()) < 100]
    empty_chunks = [c for c in rag_ready_chunks if not c.get('content', '').strip()]

    print(f"Chunks with <100 characters: {len(small_chunks)}")
    print(f"Chunks with empty content: {len(empty_chunks)}")

    if small_chunks:
        print(f"\n--- Sample Small Chunks ---")
        for chunk in small_chunks[:3]:
            print(f"  • {chunk.get('title', 'Unknown')} ({len(chunk.get('content', ''))} chars)")
            print(f"    Content: {repr(chunk.get('content', '')[:100])}")

    if empty_chunks:
        print(f"\n--- Empty Chunks ---")
        for chunk in empty_chunks[:3]:
            print(f"  • {chunk.get('title', 'Unknown')} (ID: {chunk.get('id', '')})")

if __name__ == "__main__":
    main()
