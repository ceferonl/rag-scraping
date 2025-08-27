"""
Functional pipeline for RAG Scraping.

This module provides pure functions for the scraping pipeline,
replacing the class-based approach with a more functional design.
"""

import asyncio
import json
import logging
import logging.handlers
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from .config import load_config_with_paths
from .scraping import scrape_main_page, scrape_item_details, delay_between_requests
from .pdf_processing import process_all_pdfs
from .rag_chunking import create_rag_chunks
from .models import MainPageItem, KnowledgeBaseItem


def setup_logging(config: Dict[str, Any]) -> tuple[str, str]:
    """
    Setup comprehensive logging based on configuration.

    Returns:
        Tuple of (detailed_log_path, summary_log_path)
    """
    log_config = config['logging']
    timestamp = config['timestamp']
    output_paths = config['output_paths']

    # Create logs directory as subfolder of output
    log_dir = output_paths['base_dir'] / log_config['log_subdir']
    log_dir.mkdir(exist_ok=True)

    # Setup detailed log file path
    detailed_log_file = log_config['detailed_log_file'].format(timestamp=timestamp)
    detailed_log_path = log_dir / detailed_log_file

    # Setup summary log file path
    summary_log_file = log_config['summary_log_file'].format(timestamp=timestamp)
    summary_log_path = log_dir / summary_log_file

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_config['level']))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(log_config['format'])
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler for detailed logs
    if log_config.get('log_to_file', True):
        file_handler = logging.FileHandler(detailed_log_path, encoding='utf-8')
        file_formatter = logging.Formatter(log_config['format'])
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    return str(detailed_log_path), str(summary_log_path)


def create_log_summary(
    detailed_log_path: str,
    summary_log_path: str,
    scraping_stats: Dict[str, Any],
    config: Dict[str, Any]
) -> None:
    """
    Create a markdown summary of the scraping session.

    Args:
        detailed_log_path: Path to detailed log file
        summary_log_path: Path to summary markdown file
        scraping_stats: Dictionary with scraping statistics
    """
    try:
        # Read the detailed log to analyze
        errors = []
        warnings = []
        key_events = []

        if os.path.exists(detailed_log_path):
            with open(detailed_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'ERROR' in line:
                        errors.append(line.strip())
                    elif 'WARNING' in line:
                        warnings.append(line.strip())
                    elif any(keyword in line for keyword in [
                        'Successfully', 'Starting', 'Completed', 'Fetching', 'Saved'
                    ]):
                        key_events.append(line.strip())

        # Get run parameters
        run_type = config['output_paths']['base_dir'].name  # demo or production
        max_items = scraping_stats.get('max_items', 'All')
        filter_type = scraping_stats.get('filter_type', 'None')

        # Create summary content
        summary_content = f"""# Scraping Session Summary

**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Run Type**: {run_type}
**Detailed Log**: {detailed_log_path}

## Run Parameters

- **Max Items**: {max_items}
- **Filter Type**: {filter_type}
- **Run Type**: {run_type}
- **Base URL**: {config['scraping']['base_url']}
- **Output Directory**: {config['output_paths']['base_dir']}

## Performance Statistics

- **Total Items Processed**: {scraping_stats.get('total_items', 0)}
- **Successful Scrapes**: {scraping_stats.get('successful_scrapes', 0)}
- **Failed Scrapes**: {scraping_stats.get('failed_scrapes', 0)}
- **Server Errors**: {scraping_stats.get('server_errors', 0)}
- **Success Rate**: {scraping_stats.get('success_rate', 0):.1f}%
- **Duration**: {scraping_stats.get('duration', 'N/A')}
- **Start Time**: {scraping_stats.get('start_time', 'N/A')}
- **End Time**: {scraping_stats.get('end_time', 'N/A')}

## Scraping Configuration

- **Request Delay**: {scraping_stats.get('request_delay', 'N/A')}s
- **Main Page to Details Delay**: {scraping_stats.get('main_page_delay', 'N/A')}s
- **Min/Max Random Delay**: {scraping_stats.get('min_delay', 'N/A')}-{scraping_stats.get('max_delay', 'N/A')}s
- **Max Retries**: {config['scraping']['max_retries']}
- **Timeout**: {config['scraping']['timeout']}s
- **Retry Delays**: {config['scraping']['retry_delays']}

## System Configuration

- **Log Level**: {config['logging']['level']}
- **Log Directory**: {config['output_paths']['base_dir']}/{config['logging']['log_subdir']}
- **RAG Chunk Size**: {config['rag']['min_chunk_size']}-{config['rag']['max_chunk_size']} chars
- **User Agent**: {config['scraping']['user_agent']}

## Errors ({len(errors)})

```
{chr(10).join(errors[:10])}  # Show first 10 errors
{f'... and {len(errors) - 10} more errors' if len(errors) > 10 else ''}
```

## Warnings ({len(warnings)})

```
{chr(10).join(warnings[:5])}  # Show first 5 warnings
{f'... and {len(warnings) - 5} more warnings' if len(warnings) > 5 else ''}
```

## Key Events

```
{chr(10).join(key_events[-20:])}  # Show last 20 key events
```

## Recommendations

"""

        # Add recommendations based on results
        if scraping_stats.get('server_errors', 0) > 0:
            summary_content += "- Consider increasing delays further to reduce server errors\n"

        if scraping_stats.get('success_rate', 100) < 90:
            summary_content += "- Success rate is low, check network connectivity and server response\n"

        if len(errors) > scraping_stats.get('total_items', 1) * 0.1:
            summary_content += "- High error rate detected, review error patterns\n"

        summary_content += "\n---\n*Generated automatically by RAG Scraping Pipeline*\n"

        # Write summary file
        with open(summary_log_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)

    except Exception as e:
        # Fallback summary if analysis fails
        with open(summary_log_path, 'w', encoding='utf-8') as f:
            f.write(f"""# Scraping Session Summary

**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Status**: Error creating detailed summary

## Error
```
{str(e)}
```

## Basic Stats
- **Total Items**: {scraping_stats.get('total_items', 0)}
- **Success Rate**: {scraping_stats.get('success_rate', 0):.1f}%

See detailed log: {detailed_log_path}
""")


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
) -> tuple[List[KnowledgeBaseItem], Dict[str, Any]]:
    """
    Scrape detailed information for items with comprehensive logging.

    Args:
        config: Configuration dictionary
        max_items: Maximum number of items to scrape
        filter_type: Filter by item type

    Returns:
        Tuple of (detailed knowledge base items, scraping statistics)
    """
    # Setup logging
    detailed_log_path, summary_log_path = setup_logging(config)
    logger = logging.getLogger(__name__)

    # Initialize statistics
    stats = {
        'total_items': 0,
        'successful_scrapes': 0,
        'failed_scrapes': 0,
        'server_errors': 0,
        'success_rate': 0.0,
        'request_delay': config['scraping']['request_delay'],
        'main_page_delay': config['scraping']['main_page_to_details_delay'],
        'min_delay': config['scraping']['min_delay'],
        'max_delay': config['scraping']['max_delay'],
        'max_items': max_items,
        'filter_type': filter_type,
        'start_time': datetime.now(),
    }

    logger.info("=" * 60)
    logger.info("STARTING DETAILED ITEMS SCRAPING SESSION")
    logger.info("=" * 60)
    logger.info(f"Configuration: delay={stats['request_delay']}s, main_page_delay={stats['main_page_delay']}s")

    try:
        # First get main page items
        logger.info("Step 1: Scraping main page...")
        main_items = await scrape_main_page(config)
        logger.info(f"Found {len(main_items)} items on main page")

        # Add delay after main page scraping before starting detailed scraping
        logger.info(f"Waiting {stats['main_page_delay']} seconds before starting detailed scraping...")
        await asyncio.sleep(stats['main_page_delay'])

        # Apply filters
        if filter_type:
            main_items = [item for item in main_items if item.item_type == filter_type]
            logger.info(f"Filtered to {len(main_items)} items of type '{filter_type}'")

        if max_items:
            main_items = main_items[:max_items]
            logger.info(f"Limited to {len(main_items)} items")

        stats['total_items'] = len(main_items)

        logger.info("Step 2: Starting detailed scraping...")
        logger.info(f"Will scrape {len(main_items)} items with {stats['request_delay']}s delays")

        # Scrape details for each item
        detailed_items = []
        for i, main_item in enumerate(main_items, 1):
            logger.info(f"[{i}/{len(main_items)}] Scraping: {main_item.title}")

            try:
                detailed_item = await scrape_item_details(main_item, config)

                # Check for server errors in the content
                if "server encountered an internal error" in detailed_item.main_content.lower():
                    stats['server_errors'] += 1
                    stats['failed_scrapes'] += 1
                    logger.error(f"Server error detected for item: {main_item.title}")
                else:
                    stats['successful_scrapes'] += 1
                    logger.info(f"✓ Successfully scraped: {main_item.title}")

                detailed_items.append(detailed_item)

            except Exception as e:
                stats['failed_scrapes'] += 1
                logger.error(f"✗ Failed to scrape {main_item.title}: {e}")
                # Add empty item to maintain list integrity
                detailed_items.append(KnowledgeBaseItem(
                    title=main_item.title,
                    url=main_item.url,
                    item_type=main_item.item_type,
                    main_content=f"Failed to scrape: {str(e)}"
                ))

            # Add delay between items for polite scraping
            if i < len(main_items):
                logger.info(f"Waiting {stats['request_delay']}s before next item...")
                await asyncio.sleep(stats['request_delay'])

        # Calculate final statistics
        stats['success_rate'] = (stats['successful_scrapes'] / stats['total_items'] * 100) if stats['total_items'] > 0 else 0
        stats['end_time'] = datetime.now()
        stats['duration'] = stats['end_time'] - stats['start_time']

        # Save detailed items
        output_paths = config['output_paths']
        timestamp = config['timestamp']
        output_file = output_paths['base_dir'] / f"detailed_items_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([item.to_dict() for item in detailed_items], f, indent=2, ensure_ascii=False)

        # Log final results
        logger.info("=" * 60)
        logger.info("SCRAPING SESSION COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Total items processed: {stats['total_items']}")
        logger.info(f"Successful scrapes: {stats['successful_scrapes']}")
        logger.info(f"Failed scrapes: {stats['failed_scrapes']}")
        logger.info(f"Server errors: {stats['server_errors']}")
        logger.info(f"Success rate: {stats['success_rate']:.1f}%")
        logger.info(f"Duration: {stats['duration']}")
        logger.info(f"Output saved to: {output_file}")

        # Create log summary
        create_log_summary(detailed_log_path, summary_log_path, stats, config)
        logger.info(f"Log summary saved to: {summary_log_path}")

        return detailed_items, stats

    except Exception as e:
        logger.error(f"Fatal error in scraping session: {e}")
        stats['end_time'] = datetime.now()
        stats['duration'] = stats['end_time'] - stats['start_time']
        create_log_summary(detailed_log_path, summary_log_path, stats, config)
        raise


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
    detailed_items, scraping_stats = await scrape_detailed_items(config, max_items, filter_type)

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
        'scraping_stats': scraping_stats,
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
