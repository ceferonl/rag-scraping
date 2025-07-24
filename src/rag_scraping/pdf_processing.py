"""
PDF processing functions for RAG Scraping.

This module provides functional approaches to PDF processing,
replacing the class-based approach with pure functions.
"""

import json
import logging
import os
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse, unquote
import re
from collections import defaultdict
import base64

from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Text, Title, NarrativeText, ListItem, Table
from unstructured.chunking.title import chunk_by_title
from unstructured.chunking.basic import chunk_elements

from .models import KnowledgeBaseItem
from .utils import clean_text_for_rag, format_date, create_chunk_id


logger = logging.getLogger(__name__)


def process_pdfs_from_items(
    items: List[KnowledgeBaseItem],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Process PDFs from knowledge base items and create RAG chunks.

    Args:
        items: List of knowledge base items
        config: Configuration dictionary

    Returns:
        List of PDF RAG chunks
    """
    logger.info(f"Processing PDFs from {len(items)} items...")

    output_paths = config['output_paths']
    timestamp = config['timestamp']

    all_pdf_chunks = []
    processed_pdfs = []

    for i, item in enumerate(items, 1):
        logger.info(f"Processing PDFs for item {i}/{len(items)}: {item.title}")

        for j, pdf_url in enumerate(item.pdfs, 1):
            if not pdf_url:
                continue

            logger.info(f"  Processing PDF {j}/{len(item.pdfs)}: {os.path.basename(pdf_url)}")

            try:
                pdf_chunks = process_single_pdf(
                    pdf_url, item, output_paths, config
                )

                if pdf_chunks:
                    all_pdf_chunks.extend(pdf_chunks)
                    processed_pdfs.append({
                        'url': pdf_url,
                        'title': item.title,
                        'chunks': len(pdf_chunks)
                    })
                    logger.info(f"    ✓ Created {len(pdf_chunks)} chunks")
                else:
                    logger.warning(f"    ✗ No chunks created")

            except Exception as e:
                logger.error(f"    ✗ Error processing PDF: {e}")
                continue

    # Save PDF chunks
    pdf_chunks_file = output_paths['base_dir'] / f"pdf_items_rag_ready_{timestamp}.json"
    with open(pdf_chunks_file, 'w', encoding='utf-8') as f:
        json.dump(all_pdf_chunks, f, indent=2, ensure_ascii=False)

    logger.info(f"PDF processing complete! Created {len(all_pdf_chunks)} chunks from {len(processed_pdfs)} PDFs")
    logger.info(f"PDF chunks saved to: {pdf_chunks_file}")

    return all_pdf_chunks


def process_single_pdf(
    pdf_url: str,
    item: KnowledgeBaseItem,
    output_paths: Dict[str, Path],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Process a single PDF and create RAG chunks.

    Args:
        pdf_url: URL of the PDF
        item: Knowledge base item
        output_paths: Output path configuration
        config: Configuration dictionary

    Returns:
        List of PDF RAG chunks
    """
    # Download PDF
    pdf_filepath = download_pdf(pdf_url, output_paths['pdfs_dir'], config)
    if not pdf_filepath:
        return []

    # Extract content
    raw_content = extract_pdf_content(pdf_filepath, output_paths['images_dir'])
    if not raw_content:
        return []

    # Create RAG chunks
    chunks = create_pdf_chunks(item, pdf_url, raw_content, config)

    return chunks


def download_pdf(
    pdf_url: str,
    output_dir: Path,
    config: Dict[str, Any]
) -> Optional[str]:
    """
    Download a PDF from URL or use local file if it exists.

    Args:
        pdf_url: URL or local path of the PDF
        output_dir: Directory to save PDF
        config: Configuration dictionary

    Returns:
        Path to downloaded PDF or None if failed
    """
    # If it's a local file and exists, just return it
    if not (pdf_url.startswith('http://') or pdf_url.startswith('https://')):
        if os.path.exists(pdf_url):
            return pdf_url
        else:
            logger.error(f"Local PDF file not found: {pdf_url}")
            return None
    try:
        # Extract filename from URL
        parsed_url = urlparse(pdf_url)
        filename = unquote(os.path.basename(parsed_url.path))

        if not filename.endswith('.pdf'):
            filename += '.pdf'

        # Create safe filename
        safe_filename = re.sub(r'[^\w\-_.]', '_', filename)
        filepath = output_dir / safe_filename

        # Download if not already exists
        if not filepath.exists():
            logger.info(f"Downloading PDF: {pdf_url}")

            headers = {'User-Agent': config['pdf']['user_agent']}
            response = requests.get(
                pdf_url,
                headers=headers,
                timeout=config['pdf']['download_timeout']
            )
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded PDF to: {filepath}")
        else:
            logger.info(f"PDF already exists: {filepath}")

        return str(filepath)

    except Exception as e:
        logger.error(f"Failed to download PDF {pdf_url}: {e}")
        return None


def extract_pdf_content(pdf_filepath: str, images_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Extract content from PDF using unstructured.

    Args:
        pdf_filepath: Path to PDF file
        images_dir: Directory to save extracted images

    Returns:
        Dictionary with extracted content or None if failed
    """
    try:
        logger.info(f"Extracting content from: {pdf_filepath}")

        # Extract PDF content
        elements = partition_pdf(
            pdf_filepath,
            include_images=True,
            include_page_breaks=True
        )

        # Process elements
        processed_elements = []
        for i, element in enumerate(elements):
            # Handle metadata properly
            page_number = 1
            if hasattr(element, 'metadata') and element.metadata:
                if hasattr(element.metadata, 'page_number'):
                    page_number = element.metadata.page_number
                elif hasattr(element.metadata, 'get'):
                    page_number = element.metadata.get('page_number', 1)

            element_data = {
                'text': str(element),
                'type': element.__class__.__name__,
                'page_number': page_number
            }
            processed_elements.append(element_data)

        return {
            'elements': processed_elements,
            'total_elements': len(processed_elements)
        }

    except Exception as e:
        logger.error(f"Failed to extract PDF content from {pdf_filepath}: {e}")
        return None


def create_pdf_chunks(
    item: KnowledgeBaseItem,
    pdf_url: str,
    raw_content: Dict[str, Any],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Create RAG chunks from PDF content.

    Args:
        item: Knowledge base item
        pdf_url: URL of the PDF
        raw_content: Raw extracted content
        config: Configuration dictionary

    Returns:
        List of PDF RAG chunks
    """
    chunks = []
    chunk_id = 1

    # Group elements by page
    pages = defaultdict(list)
    for element in raw_content.get('elements', []):
        page_num = element.get('page_number', 1)
        pages[page_num].append(element)

    # Process each page
    for page_num in sorted(pages.keys()):
        page_elements = pages[page_num]

        # Convert to unstructured elements for chunking
        unstructured_elements = []
        for element in page_elements:
            element_type = element.get('type', 'Text')
            element_text = element.get('text', '')

            # Clean text
            cleaned_text = clean_text_for_rag(element_text)
            if not cleaned_text.strip():
                continue

            # Create appropriate unstructured element
            if element_type == 'Title':
                unstructured_elements.append(Title(cleaned_text))
            elif element_type == 'ListItem':
                unstructured_elements.append(ListItem(cleaned_text))
            elif element_type == 'Table':
                unstructured_elements.append(Table(cleaned_text))
            elif element_type == 'NarrativeText':
                unstructured_elements.append(NarrativeText(cleaned_text))
            else:
                unstructured_elements.append(Text(cleaned_text))

        if not unstructured_elements:
            continue

        # Apply chunking
        try:
            chunked_elements = chunk_by_title(unstructured_elements)
        except Exception:
            chunked_elements = chunk_elements(unstructured_elements, max_characters=1000, overlap=200)

        # Create chunk dictionaries
        for chunk in chunked_elements:
            chunk_text = chunk.text if hasattr(chunk, 'text') else str(chunk)
            chunk_text = clean_text_for_rag(chunk_text)

            if len(chunk_text.strip()) >= config['rag']['min_chunk_size']:
                chunk_dict = {
                    'id': create_chunk_id(f"{item.title}_pdf", chunk_id),
                    'title': f"{item.title} (PDF)",
                    'content': chunk_text,
                    'source_type': 'pdf',
                    'sourcepage': item.url,
                    'sourcefile': pdf_url,
                    'page_number': page_num,
                    'date': format_date(item.date),
                    'zones': item.zones or [],
                    'type_innovatie': item.type_innovatie or [],
                    'pdfs': [pdf_url],
                    'videos': item.videos or [],
                    'pictures': item.pictures or [],
                    'chunk_number': chunk_id,
                    'content_length': len(chunk_text)
                }
                chunks.append(chunk_dict)
                chunk_id += 1

    return chunks


def clean_text_for_rag(text: str) -> str:
    if not text:
        return ""
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    text = text.replace('\\', '/')
    text = text.replace('\t', ' ')
    text = text.replace('\\"', '"')
    text = text.replace("\\'", "'")
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\n', ' ')
    text = re.sub(r' +', ' ', text)
    text = text.strip()
    return text


def process_all_pdfs(items, config):
    output_paths = config['output_paths']
    timestamp = config['timestamp']
    raw_items = []
    cleaned_items = []
    rag_ready_items = []
    for item in items:
        for pdf_url in item.pdfs:
            if not pdf_url:
                continue
            pdf_filepath = download_pdf(pdf_url, output_paths['pdfs_dir'], config)
            if not pdf_filepath:
                continue
            raw_content = extract_pdf_content_with_images(pdf_filepath, output_paths['images_dir'])
            if not raw_content:
                continue
            raw_item = create_raw_pdf_item(item, pdf_url, raw_content)
            raw_items.append(raw_item)
            cleaned_item = create_cleaned_pdf_item(item, pdf_url, raw_content)
            cleaned_items.append(cleaned_item)
            rag_chunks = create_pdf_chunks(item, pdf_url, raw_content, config)
            rag_ready_items.extend(rag_chunks)
    # Save outputs
    base_dir = output_paths['base_dir']
    with open(base_dir / f"pdf_items_raw_{timestamp}.json", 'w', encoding='utf-8') as f:
        json.dump(raw_items, f, indent=2, ensure_ascii=False)
    with open(base_dir / f"pdf_items_cleaned_{timestamp}.json", 'w', encoding='utf-8') as f:
        json.dump(cleaned_items, f, indent=2, ensure_ascii=False)
    with open(base_dir / f"pdf_items_rag_ready_{timestamp}.json", 'w', encoding='utf-8') as f:
        json.dump(rag_ready_items, f, indent=2, ensure_ascii=False)
    return raw_items, cleaned_items, rag_ready_items


def extract_pdf_content_with_images(pdf_filepath: str, images_dir: Path) -> Optional[Dict[str, Any]]:
    try:
        elements = partition_pdf(
            pdf_filepath,
            include_images=True,
            include_page_breaks=True
        )
        pages = defaultdict(list)
        elements_data = []
        images = []
        for element in elements:
            page_num = getattr(element.metadata, 'page_number', 1) or 1
            element_data = {
                "type": getattr(element, 'category', element.__class__.__name__),
                "text": getattr(element, 'text', str(element)),
                "page_number": page_num,
                "filename": os.path.splitext(os.path.basename(pdf_filepath))[0]
            }
            if hasattr(element.metadata, 'image_base64') and getattr(element.metadata, 'image_base64', None):
                try:
                    image_filename = f"{os.path.splitext(os.path.basename(pdf_filepath))[0]}_image_{len(images):03d}.png"
                    image_path = images_dir / image_filename
                    image_data = base64.b64decode(element.metadata.image_base64)
                    with open(image_path, 'wb') as img_file:
                        img_file.write(image_data)
                    element_data["image_path"] = f"images/{image_filename}"
                    images.append({
                        "type": element_data["type"],
                        "file_path": f"images/{image_filename}",
                        "page_number": page_num
                    })
                except Exception:
                    pass
            pages[page_num].append(element_data["text"])
            elements_data.append(element_data)
        page_texts = {}
        for page_num in sorted(pages.keys()):
            page_texts[f"page_{page_num}"] = clean_text_for_rag("\n".join(pages[page_num]))
        all_text = "\n\n".join(page_texts.values())
        return {
            "text": all_text,
            "page_texts": page_texts,
            "elements": elements_data,
            "images": images,
            "total_elements": len(elements_data),
            "total_images": len(images),
            "total_pages": len(pages)
        }
    except Exception as e:
        logger.error(f"Failed to extract PDF content from {pdf_filepath}: {e}")
        return None


def create_raw_pdf_item(original_item, pdf_url, raw_content):
    return {
        'title': f"{original_item.title} (PDF)",
        'url': pdf_url,
        'source_item_url': original_item.url,
        'extracted_text': raw_content.get('text', ''),
        'page_texts': raw_content.get('page_texts', {}),
        'elements': raw_content.get('elements', []),
        'images': raw_content.get('images', []),
        'total_elements': raw_content.get('total_elements', 0),
        'total_images': raw_content.get('total_images', 0),
        'total_pages': raw_content.get('total_pages', 0)
    }


def create_cleaned_pdf_item(original_item, pdf_url, raw_content):
    cleaned_page_texts = {}
    for page_key, page_text in raw_content.get('page_texts', {}).items():
        cleaned_page_texts[page_key] = clean_text_for_rag(page_text)
    cleaned_elements = []
    for element in raw_content.get('elements', []):
        cleaned_element = {
            "type": element.get("type", ""),
            "text": clean_text_for_rag(element.get("text", "")),
            "page_number": element.get("page_number", 1),
            "filename": element.get("filename", "")
        }
        if "image_path" in element:
            cleaned_element["image_path"] = element["image_path"]
        cleaned_elements.append(cleaned_element)
    for page_key, page_text in cleaned_page_texts.items():
        page_num = 1
        if page_key.startswith("page_"):
            try:
                page_num = int(page_key.replace("page_", ""))
            except ValueError:
                page_num = 1
        if page_text.strip():
            cleaned_elements.append({
                "type": "text",
                "text": page_text,
                "page_number": page_num,
                "filename": original_item.title
            })
    return {
        'title': f"{original_item.title} (PDF)",
        'url': pdf_url,
        'source_item_url': original_item.url,
        'elements': cleaned_elements,
        'images': raw_content.get('images', []),
        'total_elements': len(cleaned_elements),
        'total_images': raw_content.get('total_images', 0),
        'total_pages': raw_content.get('total_pages', 0)
    }
