#!/usr/bin/env python3
"""
Create a complete unified RAG-ready output from ALL available data.

This script combines ALL RAG-ready chunks from both old and new scraping runs
to create a comprehensive dataset with everything we've ever scraped.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Set

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def load_json_file(file_path: str) -> List[Dict[str, Any]]:
    """Load JSON file and return list of dictionaries."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_all_rag_files(directory: str = "output/demo") -> List[str]:
    """Find all RAG-ready files in the directory."""
    output_path = Path(directory)

    # Find all unified RAG files
    unified_files = list(output_path.glob("rag_ready_unified_*.json"))

    # Find all detailed items RAG files
    detailed_rag_files = list(output_path.glob("detailed_items_rag_ready_*.json"))

    # Find all PDF RAG files
    pdf_rag_files = list(output_path.glob("pdf_items_rag_ready_*.json"))

    all_files = unified_files + detailed_rag_files + pdf_rag_files
    return [str(f) for f in all_files]

def deduplicate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate chunks based on content and source."""
    seen = set()
    unique_chunks = []

    for chunk in chunks:
        # Create a unique identifier based on content and source
        content = chunk.get('content', '').strip()
        source = chunk.get('sourcepage', '') or chunk.get('sourcefile', '')
        title = chunk.get('title', '')

        # Create a unique key
        unique_key = f"{content[:100]}_{source}_{title}"

        if unique_key not in seen:
            seen.add(unique_key)
            unique_chunks.append(chunk)

    return unique_chunks

def main():
    """Main function to create complete unified RAG-ready output."""
    output_dir = "output/demo"

    try:
        # Find all RAG-ready files
        logger.info("Finding all RAG-ready files...")
        rag_files = find_all_rag_files(output_dir)

        if not rag_files:
            logger.error("No RAG-ready files found!")
            return

        logger.info(f"Found {len(rag_files)} RAG-ready files:")
        for file_path in rag_files:
            logger.info(f"  - {Path(file_path).name}")

        # Load all chunks from all files
        all_chunks = []
        file_stats = {}

        for file_path in rag_files:
            try:
                logger.info(f"Loading {Path(file_path).name}...")
                chunks = load_json_file(file_path)
                all_chunks.extend(chunks)
                file_stats[Path(file_path).name] = len(chunks)
                logger.info(f"  Loaded {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                continue

        logger.info(f"Total chunks loaded: {len(all_chunks)}")

        # Deduplicate chunks
        logger.info("Deduplicating chunks...")
        unique_chunks = deduplicate_chunks(all_chunks)
        logger.info(f"After deduplication: {len(unique_chunks)} unique chunks")

        # Save complete unified output
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        complete_output_file = Path(output_dir) / f"rag_ready_complete_{timestamp}.json"

        with open(complete_output_file, 'w', encoding='utf-8') as f:
            json.dump(unique_chunks, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved complete unified RAG-ready output to: {complete_output_file}")

        # Print comprehensive summary
        print(f"\n=== Complete Unified RAG-Ready Output Summary ===")
        print(f"Complete output file: {complete_output_file}")
        print(f"Total unique chunks: {len(unique_chunks)}")
        print(f"Chunks removed by deduplication: {len(all_chunks) - len(unique_chunks)}")

        print(f"\n--- Source Files ---")
        for filename, count in file_stats.items():
            print(f"  {filename}: {count} chunks")

        # Analyze by source type
        page_source_chunks = [c for c in unique_chunks if c.get('source_type') == 'page']
        pdf_source_chunks = [c for c in unique_chunks if c.get('source_type') == 'pdf']

        print(f"\n--- Content Analysis ---")
        print(f"Chunks from pages: {len(page_source_chunks)}")
        print(f"Chunks from PDFs: {len(pdf_source_chunks)}")

        # Analyze chunk sizes
        small_chunks = [c for c in unique_chunks if len(c.get('content', '').strip()) < 100]
        empty_chunks = [c for c in unique_chunks if not c.get('content', '').strip()]

        print(f"Chunks with <100 characters: {len(small_chunks)}")
        print(f"Chunks with empty content: {len(empty_chunks)}")

        # Content length stats
        if unique_chunks:
            content_lengths = [len(c.get('content', '')) for c in unique_chunks]
            avg_content_length = sum(content_lengths) / len(content_lengths)
            max_content_length = max(content_lengths)
            min_content_length = min(content_lengths)

            print(f"\n--- Content Length Stats ---")
            print(f"Average: {avg_content_length:.1f} characters")
            print(f"Maximum: {max_content_length} characters")
            print(f"Minimum: {min_content_length} characters")

        # Sample unique titles
        unique_titles = set(c.get('title', '') for c in unique_chunks)
        print(f"\n--- Unique Sources ---")
        print(f"Unique titles: {len(unique_titles)}")
        print(f"Sample titles:")
        for title in sorted(list(unique_titles))[:10]:
            print(f"  • {title}")
        if len(unique_titles) > 10:
            print(f"  ... and {len(unique_titles) - 10} more")

        print(f"\n✅ Successfully created complete unified RAG-ready output!")
        print(f"📁 File: {complete_output_file}")
        print(f"📊 Total unique chunks: {len(unique_chunks)}")
        print(f"🔄 This includes ALL content from ALL scraping runs!")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
