#!/usr/bin/env python3
"""
Validate existing data files.

This script checks existing data files to ensure they're still valid
and compatible with the new architecture.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag_scraping.models import KnowledgeBaseItem


def validate_json_file(filepath: Path) -> dict:
    """Validate a JSON file and return statistics."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            return {
                'type': 'list',
                'count': len(data),
                'valid': True,
                'error': None
            }
        elif isinstance(data, dict):
            return {
                'type': 'dict',
                'keys': list(data.keys()),
                'valid': True,
                'error': None
            }
        else:
            return {
                'type': 'unknown',
                'valid': False,
                'error': f"Unexpected data type: {type(data)}"
            }

    except json.JSONDecodeError as e:
        return {
            'type': 'invalid_json',
            'valid': False,
            'error': f"JSON decode error: {e}"
        }
    except Exception as e:
        return {
            'type': 'error',
            'valid': False,
            'error': f"File error: {e}"
        }


def validate_detailed_items(filepath: Path) -> dict:
    """Validate detailed items file specifically."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            items_data = json.load(f)

        if not isinstance(items_data, list):
            return {
                'valid': False,
                'error': "Data is not a list"
            }

        stats = {
            'total_items': len(items_data),
            'items_with_content': 0,
            'items_without_content': 0,
            'items_with_pdfs': 0,
            'items_with_videos': 0,
            'items_with_pictures': 0,
            'valid': True,
            'errors': []
        }

        for i, item_data in enumerate(items_data):
            try:
                # Try to create KnowledgeBaseItem
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

                # Count statistics
                if item.main_content and item.main_content.strip():
                    stats['items_with_content'] += 1
                else:
                    stats['items_without_content'] += 1

                if item.pdfs:
                    stats['items_with_pdfs'] += 1
                if item.videos:
                    stats['items_with_videos'] += 1
                if item.pictures:
                    stats['items_with_pictures'] += 1

            except Exception as e:
                stats['errors'].append(f"Item {i}: {e}")

        if stats['errors']:
            stats['valid'] = False

        return stats

    except Exception as e:
        return {
            'valid': False,
            'error': f"Validation error: {e}"
        }


def validate_rag_chunks(filepath: Path) -> dict:
    """Validate RAG chunks file specifically."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)

        if not isinstance(chunks_data, list):
            return {
                'valid': False,
                'error': "Data is not a list"
            }

        stats = {
            'total_chunks': len(chunks_data),
            'page_chunks': 0,
            'pdf_chunks': 0,
            'chunks_with_content': 0,
            'chunks_without_content': 0,
            'avg_content_length': 0,
            'valid': True,
            'errors': []
        }

        total_length = 0

        for i, chunk_data in enumerate(chunks_data):
            try:
                # Check required fields
                required_fields = ['id', 'title', 'content', 'source_type']
                for field in required_fields:
                    if field not in chunk_data:
                        stats['errors'].append(f"Chunk {i}: Missing required field '{field}'")

                # Count by source type
                source_type = chunk_data.get('source_type', 'unknown')
                if source_type == 'page':
                    stats['page_chunks'] += 1
                elif source_type == 'pdf':
                    stats['pdf_chunks'] += 1

                # Check content
                content = chunk_data.get('content', '')
                if content and content.strip():
                    stats['chunks_with_content'] += 1
                    total_length += len(content)
                else:
                    stats['chunks_without_content'] += 1

            except Exception as e:
                stats['errors'].append(f"Chunk {i}: {e}")

        if stats['chunks_with_content'] > 0:
            stats['avg_content_length'] = total_length / stats['chunks_with_content']

        if stats['errors']:
            stats['valid'] = False

        return stats

    except Exception as e:
        return {
            'valid': False,
            'error': f"Validation error: {e}"
        }


def main():
    """Validate all existing data files."""
    print("🔍 Validating Existing Data Files")
    print("=" * 50)

    # Find all data files
    output_dir = Path("output/demo")
    if not output_dir.exists():
        print("❌ Output directory not found: output/demo")
        return 1

    data_files = []
    for pattern in ["*.json"]:
        data_files.extend(output_dir.glob(pattern))

    if not data_files:
        print("❌ No data files found in output/demo")
        return 1

    print(f"📁 Found {len(data_files)} data files")
    print()

    valid_files = 0
    total_files = len(data_files)

    for filepath in sorted(data_files):
        print(f"📄 {filepath.name}")

        # Basic JSON validation
        basic_validation = validate_json_file(filepath)
        if not basic_validation['valid']:
            print(f"  ❌ Invalid JSON: {basic_validation['error']}")
            continue

        print(f"  ✅ Valid JSON ({basic_validation['type']})")

        # Specific validation based on file type
        if 'detailed_items' in filepath.name:
            validation = validate_detailed_items(filepath)
            if validation['valid']:
                print(f"  📊 {validation['total_items']} items")
                print(f"    - With content: {validation['items_with_content']}")
                print(f"    - Without content: {validation['items_without_content']}")
                print(f"    - With PDFs: {validation['items_with_pdfs']}")
                print(f"    - With videos: {validation['items_with_videos']}")
                print(f"    - With pictures: {validation['items_with_pictures']}")
                valid_files += 1
            else:
                error_msg = validation.get('error', 'Unknown error')
                print(f"  ❌ Validation failed: {error_msg}")

        elif 'rag_ready' in filepath.name or 'pdf_items' in filepath.name:
            validation = validate_rag_chunks(filepath)
            if validation['valid']:
                print(f"  📊 {validation['total_chunks']} chunks")
                print(f"    - Page chunks: {validation['page_chunks']}")
                print(f"    - PDF chunks: {validation['pdf_chunks']}")
                print(f"    - With content: {validation['chunks_with_content']}")
                print(f"    - Without content: {validation['chunks_without_content']}")
                print(f"    - Avg content length: {validation['avg_content_length']:.0f} chars")
                valid_files += 1
            else:
                error_msg = validation.get('error', 'Unknown error')
                print(f"  ❌ Validation failed: {error_msg}")

        elif 'main_page_items' in filepath.name:
            validation = validate_json_file(filepath)
            if validation['valid']:
                print(f"  📊 {validation['count']} main page items")
                valid_files += 1
            else:
                error_msg = validation.get('error', 'Unknown error')
                print(f"  ❌ Validation failed: {error_msg}")

        else:
            # Generic file
            print(f"  📊 {basic_validation.get('count', 'Unknown')} items")
            valid_files += 1

        print()

    print("=" * 50)
    print(f"📊 Results: {valid_files}/{total_files} files valid")

    if valid_files == total_files:
        print("🎉 All data files are valid!")
        return 0
    else:
        print("⚠️  Some files have issues. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
