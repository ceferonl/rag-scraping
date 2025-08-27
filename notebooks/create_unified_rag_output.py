#!/usr/bin/env python3
"""
Create unified RAG-ready output from both page chunks and PDF chunks.

This script combines the newly created page chunks and PDF chunks into a single
unified RAG-ready output file.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

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

def find_latest_file(pattern: str, directory: str = "output/demo") -> str:
    """Find the latest file matching a pattern."""
    output_path = Path(directory)
    files = list(output_path.glob(pattern))

    if not files:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")

    # Return the most recent file
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    return str(latest_file)

def main():
    """Main function to create unified RAG-ready output."""
    output_dir = "output/demo"

    try:
        # Find the latest files
        logger.info("Finding latest files...")

        # Find latest page chunks
        page_chunks_file = find_latest_file("detailed_items_rag_ready_*.json")
        logger.info(f"Found page chunks file: {page_chunks_file}")

        # Find latest PDF chunks
        pdf_chunks_file = find_latest_file("pdf_items_rag_ready_*.json")
        logger.info(f"Found PDF chunks file: {pdf_chunks_file}")

        # Load both chunk files
        logger.info("Loading chunk files...")
        page_chunks = load_json_file(page_chunks_file)
        pdf_chunks = load_json_file(pdf_chunks_file)

        logger.info(f"Loaded {len(page_chunks)} page chunks")
        logger.info(f"Loaded {len(pdf_chunks)} PDF chunks")

        # Combine all chunks
        all_chunks = page_chunks + pdf_chunks
        logger.info(f"Combined {len(all_chunks)} total chunks")

        # Save unified output
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unified_output_file = Path(output_dir) / f"rag_ready_unified_{timestamp}.json"

        with open(unified_output_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved unified RAG-ready output to: {unified_output_file}")

        # Print summary
        print(f"\n=== Unified RAG-Ready Output Summary ===")
        print(f"Page chunks file: {page_chunks_file}")
        print(f"PDF chunks file: {pdf_chunks_file}")
        print(f"Unified output file: {unified_output_file}")
        print(f"Page chunks: {len(page_chunks)}")
        print(f"PDF chunks: {len(pdf_chunks)}")
        print(f"Total chunks: {len(all_chunks)}")

        # Analyze chunk sizes
        small_chunks = [c for c in all_chunks if len(c.get('content', '').strip()) < 100]
        empty_chunks = [c for c in all_chunks if not c.get('content', '').strip()]

        print(f"Chunks with <100 characters: {len(small_chunks)}")
        print(f"Chunks with empty content: {len(empty_chunks)}")

        # Analyze by source type
        page_source_chunks = [c for c in all_chunks if c.get('source_type') == 'page']
        pdf_source_chunks = [c for c in all_chunks if c.get('source_type') == 'pdf']

        print(f"Chunks from pages: {len(page_source_chunks)}")
        print(f"Chunks from PDFs: {len(pdf_source_chunks)}")

        # Sample content analysis
        if all_chunks:
            avg_content_length = sum(len(c.get('content', '')) for c in all_chunks) / len(all_chunks)
            max_content_length = max(len(c.get('content', '')) for c in all_chunks)
            min_content_length = min(len(c.get('content', '')) for c in all_chunks)

            print(f"Content length stats:")
            print(f"  Average: {avg_content_length:.1f} characters")
            print(f"  Maximum: {max_content_length} characters")
            print(f"  Minimum: {min_content_length} characters")

        print(f"\n✅ Successfully created unified RAG-ready output!")
        print(f"📁 File: {unified_output_file}")
        print(f"📊 Total chunks: {len(all_chunks)}")

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"❌ Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
