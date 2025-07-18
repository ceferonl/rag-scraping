"""
RAG Scraping CLI Entry Point

This module provides the command-line interface for the RAG scraping tool,
replacing the old demo file with a clean, functional approach.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from .config import load_config_with_paths
from .pipeline import (
    setup_logging,
    scrape_main_page_only,
    scrape_detailed_items,
    process_pdfs_from_file,
    run_demo_pipeline,
    run_production_pipeline
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Versnellingsplan RAG Scraper - Functional Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run demo pipeline (5 items)
  python -m rag_scraping --demo

  # Run production pipeline
  python -m rag_scraping --production

  # Scrape main page only
  python -m rag_scraping --main-page-only

  # Scrape detailed items with limits
  python -m rag_scraping --detailed --max-items 10

  # Process PDFs from existing file
  python -m rag_scraping --process-pdfs detailed_items_20250718_123456.json

  # Use custom config and run type
  python -m rag_scraping --config my_config.yaml --run-type main --demo
        """
    )

    # Configuration options
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Configuration file path (default: config.yaml)'
    )
    parser.add_argument(
        '--run-type',
        choices=['demo', 'main'],
        help='Run type (demo or main). Overrides config default.'
    )

    # Pipeline modes (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--demo',
        action='store_true',
        help='Run demo pipeline (limited items)'
    )
    mode_group.add_argument(
        '--production',
        action='store_true',
        help='Run full production pipeline'
    )
    mode_group.add_argument(
        '--main-page-only',
        action='store_true',
        help='Scrape main page only (no details)'
    )
    mode_group.add_argument(
        '--detailed',
        action='store_true',
        help='Scrape detailed items only'
    )
    mode_group.add_argument(
        '--process-pdfs',
        metavar='FILE',
        help='Process PDFs from detailed items file'
    )

    # Filtering options
    parser.add_argument(
        '--max-items',
        type=int,
        help='Maximum number of items to process'
    )
    parser.add_argument(
        '--filter-type',
        choices=['Publicatie', 'Product', 'Project'],
        help='Filter by item type'
    )

    # Demo-specific options
    parser.add_argument(
        '--demo-items',
        type=int,
        default=5,
        help='Number of items for demo (default: 5)'
    )

    # Output options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose logging'
    )

    return parser.parse_args()


async def main():
    """Main CLI entry point."""
    args = parse_args()

    try:
        # Load configuration
        config = load_config_with_paths(args.config, args.run_type)

        # Setup logging
        setup_logging(config)
        if args.verbose:
            import logging
            logging.getLogger().setLevel(logging.DEBUG)

        # Run appropriate pipeline based on arguments
        if args.demo:
            print(f"🚀 Running DEMO pipeline with {args.demo_items} items...")
            print(f"📁 Output directory: {config['output_paths']['base_dir']}")
            print(f"🏷️  Run type: {config['output_paths']['run_type']}")
            print()

            result = await run_demo_pipeline(config, args.demo_items)

            print(f"\n✅ Demo pipeline complete!")
            print(f"📊 Results:")
            print(f"   - Detailed items: {len(result['detailed_items'])}")
            print(f"   - Page chunks: {len(result['page_chunks'])}")
            print(f"   - PDF chunks: {len(result['pdf_chunks'])}")
            print(f"   - Total chunks: {len(result['all_chunks'])}")
            print(f"📁 Files saved:")
            for name, path in result['output_files'].items():
                print(f"   - {name}: {path}")

        elif args.production:
            print("🚀 Running PRODUCTION pipeline...")
            print(f"📁 Output directory: {config['output_paths']['base_dir']}")
            print(f"🏷️  Run type: {config['output_paths']['run_type']}")
            print()

            result = await run_production_pipeline(config)

            print(f"\n✅ Production pipeline complete!")
            print(f"📊 Results:")
            print(f"   - Detailed items: {len(result['detailed_items'])}")
            print(f"   - Page chunks: {len(result['page_chunks'])}")
            print(f"   - PDF chunks: {len(result['pdf_chunks'])}")
            print(f"   - Total chunks: {len(result['all_chunks'])}")
            print(f"📁 Files saved:")
            for name, path in result['output_files'].items():
                print(f"   - {name}: {path}")

        elif args.main_page_only:
            print("📄 Scraping main page only...")
            print(f"📁 Output directory: {config['output_paths']['base_dir']}")
            print()

            items = await scrape_main_page_only(config)

            print(f"\n✅ Main page scraping complete!")
            print(f"📊 Found {len(items)} items")

        elif args.detailed:
            print("🔍 Scraping detailed items...")
            print(f"📁 Output directory: {config['output_paths']['base_dir']}")
            if args.max_items:
                print(f"📊 Max items: {args.max_items}")
            if args.filter_type:
                print(f"🔧 Filter type: {args.filter_type}")
            print()

            items = await scrape_detailed_items(
                config,
                max_items=args.max_items,
                filter_type=args.filter_type
            )

            print(f"\n✅ Detailed scraping complete!")
            print(f"📊 Scraped {len(items)} detailed items")

        elif args.process_pdfs:
            print(f"📄 Processing PDFs from: {args.process_pdfs}")
            print(f"📁 Output directory: {config['output_paths']['base_dir']}")
            print()

            # Check if file exists
            input_file = Path(args.process_pdfs)
            if not input_file.exists():
                print(f"❌ Error: File not found: {input_file}")
                sys.exit(1)

            chunks = process_pdfs_from_file(str(input_file), config)

            print(f"\n✅ PDF processing complete!")
            print(f"📊 Created {len(chunks)} PDF chunks")

    except FileNotFoundError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
