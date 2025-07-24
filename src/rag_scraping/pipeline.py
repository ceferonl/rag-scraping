"""
Functional pipeline for RAG Scraping.

This module provides pure functions for the scraping pipeline,
replacing the class-based approach with a more functional design.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import load_config_with_paths
from .scraping import scrape_main_page, scrape_item_details
from .pdf_processing import process_all_pdfs
from .rag_chunking import create_rag_chunks
from .models import MainPageItem, KnowledgeBaseItem


def setup_logging(config: Dict[str, Any]) -> None:
    """Setup logging based on configuration."""
    logging.basicConfig(
        level=getattr(logging, config['logging']['level']),
        format=config['logging']['format']
    )


async def scrape_main_page_only(config: Dict[str, Any]) -> List[MainPageItem]:
    """
    Scrape only the main page and return list of items.

    Args:
        config: Configuration dictionary

    Returns:
        List of main page items
    """
    logger = logging.getLogger(__name__)
    logger.info("Scraping main page only...")

    items = await scrape_main_page(config)

    # Save main page items
    output_paths = config['output_paths']
    timestamp = config['timestamp']
    output_file = output_paths['base_dir'] / f"main_page_items_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([item.model_dump() for item in items], f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(items)} main page items to {output_file}")
    return items


async def scrape_detailed_items(
    config: Dict[str, Any],
    max_items: Optional[int] = None,
    filter_type: Optional[str] = None
) -> List[KnowledgeBaseItem]:
    """
    Scrape detailed information for items.

    Args:
        config: Configuration dictionary
        max_items: Maximum number of items to scrape
        filter_type: Filter by item type

    Returns:
        List of detailed knowledge base items
    """
    logger = logging.getLogger(__name__)
    logger.info("Scraping detailed items...")

    # First get main page items
    main_items = await scrape_main_page(config)

    # Apply filters
    if filter_type:
        main_items = [item for item in main_items if item.item_type == filter_type]
        logger.info(f"Filtered to {len(main_items)} items of type '{filter_type}'")

    if max_items:
        main_items = main_items[:max_items]
        logger.info(f"Limited to {len(main_items)} items")

    # Scrape details for each item
    detailed_items = []
    for i, main_item in enumerate(main_items, 1):
        logger.info(f"Scraping details for item {i}/{len(main_items)}: {main_item.title}")

        detailed_item = await scrape_item_details(main_item, config)
        detailed_items.append(detailed_item)

        # Add delay between items for polite scraping
        if i < len(main_items):
            await asyncio.sleep(config['scraping']['request_delay'])

    # Save detailed items
    output_paths = config['output_paths']
    timestamp = config['timestamp']
    output_file = output_paths['base_dir'] / f"detailed_items_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([item.to_dict() for item in detailed_items], f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(detailed_items)} detailed items to {output_file}")
    return detailed_items


def process_pdfs_from_file(
    input_file: str,
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Process PDFs from a detailed items file.

    Args:
        input_file: Path to detailed items JSON file
        config: Configuration dictionary

    Returns:
        List of PDF processing results
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Processing PDFs from file: {input_file}")

    # Load detailed items
    with open(input_file, 'r', encoding='utf-8') as f:
        detailed_items_data = json.load(f)

    # Convert to KnowledgeBaseItem objects
    detailed_items = []
    for item_data in detailed_items_data:
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
        detailed_items.append(item)

    # Process PDFs with all intermediate outputs
    raw, cleaned, rag_ready = process_all_pdfs(detailed_items, config)
    return rag_ready


async def run_full_pipeline(
    config: Dict[str, Any],
    max_items: Optional[int] = None,
    filter_type: Optional[str] = None,
    include_pdfs: bool = True
) -> Dict[str, Any]:
    """
    Run the complete scraping pipeline.

    Args:
        config: Configuration dictionary
        max_items: Maximum number of items to scrape
        filter_type: Filter by item type
        include_pdfs: Whether to process PDFs

    Returns:
        Dictionary with pipeline results
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting full pipeline...")

    # Step 1: Scrape detailed items
    detailed_items = await scrape_detailed_items(config, max_items, filter_type)

    # Step 2: Create RAG chunks from pages
    logger.info("Creating RAG chunks from pages...")
    page_chunks = create_rag_chunks(detailed_items, config, source_type='page')

    # Step 3: Process PDFs if requested
    pdf_chunks = []
    if include_pdfs:
        logger.info("Processing PDFs...")
        _, _, pdf_chunks = process_all_pdfs(detailed_items, config)

    # Step 4: Combine all chunks
    all_chunks = page_chunks + pdf_chunks

    # Step 5: Save unified output
    output_paths = config['output_paths']
    timestamp = config['timestamp']
    unified_file = output_paths['base_dir'] / f"rag_ready_unified_{timestamp}.json"

    with open(unified_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    logger.info(f"Pipeline complete! Saved {len(all_chunks)} total chunks to {unified_file}")

    return {
        'detailed_items': detailed_items,
        'page_chunks': page_chunks,
        'pdf_chunks': pdf_chunks,
        'all_chunks': all_chunks,
        'output_files': {
            'detailed_items': output_paths['base_dir'] / f"detailed_items_{timestamp}.json",
            'unified_chunks': unified_file
        }
    }


async def run_demo_pipeline(config: Dict[str, Any], max_items: int = 5) -> Dict[str, Any]:
    """
    Run a demo pipeline with limited items.

    Args:
        config: Configuration dictionary
        max_items: Maximum number of items for demo

    Returns:
        Pipeline results
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Running demo pipeline with {max_items} items...")

    return await run_full_pipeline(
        config=config,
        max_items=max_items,
        include_pdfs=True
    )


async def run_production_pipeline(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the full production pipeline.

    Args:
        config: Configuration dictionary

    Returns:
        Pipeline results
    """
    logger = logging.getLogger(__name__)
    logger.info("Running production pipeline...")

    return await run_full_pipeline(
        config=config,
        include_pdfs=True
    )
