"""
PDF Processor for Versnellingsplan Knowledge Base

This module processes PDFs found in detailed items, downloads them,
extracts content using unstructured, and creates new JSON entries.
"""

import json
import os
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from urllib.parse import urlparse, unquote
import re
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Text, Title, NarrativeText, ListItem, Table
from unstructured.chunking.title import chunk_by_title
from unstructured.chunking.basic import chunk_elements
from .pages import KnowledgeBaseItem
from collections import defaultdict
import base64

logger = logging.getLogger("rag_scraping.pdfs")


class PDFConfig:
    """Configuration for PDF processing."""
    DOWNLOAD_TIMEOUT = 30
    MAX_RETRIES = 3
    USER_AGENT = "RAG-Scraper/1.0"
    OUTPUT_DIR = "output/demo/pdfs"


class PDFProcessor:
    """Process PDFs from detailed items and extract content using unstructured."""

    def __init__(self, output_dir: str = PDFConfig.OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = PDFConfig

    def _clean_text_for_rag(self, text: str) -> str:
        """
        Clean text specifically for RAG applications.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text optimized for RAG
        """
        if not text:
            return ""

        import re

        # Normalize quotes and problematic characters
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('\\', '/')
        text = text.replace('\t', ' ')

        # Remove escaped quotes (both single and double)
        text = text.replace('\\"', '"')
        text = text.replace("\\'", "'")

        # Normalize newlines
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Replace all newlines with spaces (for RAG, we want continuous text)
        text = text.replace('\n', ' ')

        # Remove excessive whitespace
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single

        # Clean up and strip
        text = text.strip()

        return text

    def _create_rag_ready_chunks(self, original_item: Dict[str, Any], pdf_url: str, raw_content: dict) -> List[Dict[str, Any]]:
        """
        Create RAG-ready chunks using Unstructured's chunking logic.

        Args:
            original_item: Original detailed item
            pdf_url: URL of the PDF
            raw_content: Raw extracted content

        Returns:
            List of RAG-ready chunk dictionaries
        """
        chunks = []
        chunk_id = 1

        # Group elements by page for per-page chunking
        pages = defaultdict(list)
        for element in raw_content.get('elements', []):
            page_num = element.get('page_number', 1)
            pages[page_num].append(element)

        # Process each page separately
        for page_num in sorted(pages.keys()):
            page_elements = pages[page_num]

                        # Convert to Unstructured elements for chunking
            unstructured_elements = []
            element_image_mapping = []  # Track which images belong to which elements

            for element in page_elements:
                element_type = element.get('type', 'Text')
                element_text = element.get('text', '')

                # Clean text for RAG
                cleaned_text = self._clean_text_for_rag(element_text)
                if not cleaned_text.strip():
                    continue

                # Create appropriate Unstructured element
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

                # Track image paths for this element
                element_images = []
                if 'image_path' in element:
                    element_images.append(element['image_path'])
                element_image_mapping.append(element_images)

            if not unstructured_elements:
                continue

                        # Apply chunking strategy
            try:
                # First try title-based chunking
                chunked_elements = chunk_by_title(unstructured_elements)
            except Exception:
                # Fallback to basic chunking
                chunked_elements = chunk_elements(unstructured_elements, max_characters=1000, overlap=200)

            # Process chunks and apply size constraints
            final_chunks = []

            for chunk in chunked_elements:
                chunk_text = chunk.text if hasattr(chunk, 'text') else str(chunk)
                chunk_text = self._clean_text_for_rag(chunk_text)

                # Find which original elements contributed to this chunk
                chunk_images = []
                for i, element in enumerate(unstructured_elements):
                    element_text = element.text if hasattr(element, 'text') else str(element)
                    element_text = self._clean_text_for_rag(element_text)

                    # If this element's text is contained in the chunk, include its images
                    if element_text in chunk_text or chunk_text in element_text:
                        chunk_images.extend(element_image_mapping[i])

                # If chunk is too large, split it
                if len(chunk_text) > 2000:
                    # Split by sentences or paragraphs
                    sentences = re.split(r'[.!?]+', chunk_text)
                    current_sentence_group = ""

                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence:
                            continue

                        if len(current_sentence_group + sentence) > 1500:
                            if current_sentence_group:
                                final_chunks.append({
                                    'text': current_sentence_group.strip(),
                                    'images': chunk_images.copy()
                                })
                                current_sentence_group = sentence
                            else:
                                # Single sentence is too long, split by words
                                words = sentence.split()
                                current_word_group = ""
                                for word in words:
                                    if len(current_word_group + " " + word) > 1500:
                                        if current_word_group:
                                            final_chunks.append({
                                                'text': current_word_group.strip(),
                                                'images': chunk_images.copy()
                                            })
                                        current_word_group = word
                                    else:
                                        current_word_group += " " + word if current_word_group else word

                                if current_word_group:
                                    final_chunks.append({
                                        'text': current_word_group.strip(),
                                        'images': chunk_images.copy()
                                    })
                        else:
                            current_sentence_group += " " + sentence if current_sentence_group else sentence

                    if current_sentence_group:
                        final_chunks.append({
                            'text': current_sentence_group.strip(),
                            'images': chunk_images.copy()
                        })
                else:
                    final_chunks.append({
                        'text': chunk_text,
                        'images': chunk_images.copy()
                    })

            # Merge small chunks on the same page
            merged_chunks = []
            current_merged = ""
            current_merged_images = []

            for chunk in final_chunks:
                chunk_text = chunk['text']
                chunk_images = chunk.get('images', [])

                # If current chunk is small and adding this chunk won't make it too large
                if len(current_merged) < 500 and len(current_merged + " " + chunk_text) < 1500:
                    current_merged += " " + chunk_text if current_merged else chunk_text
                    current_merged_images.extend(chunk_images)
                else:
                    # Save current merged chunk if it exists
                    if current_merged:
                        merged_chunks.append({
                            'text': current_merged.strip(),
                            'images': list(set(current_merged_images))  # Remove duplicates
                        })

                    # Start new merged chunk
                    current_merged = chunk_text
                    current_merged_images = chunk_images

            # Add final merged chunk
            if current_merged:
                merged_chunks.append({
                    'text': current_merged.strip(),
                    'images': list(set(current_merged_images))  # Remove duplicates
                })

            # Create RAG-ready items for this page
            for chunk_data in merged_chunks:
                chunk_text = chunk_data['text']
                chunk_images = chunk_data['images']

                # Skip empty chunks
                if not chunk_text.strip():
                    continue

                # Skip chunks smaller than 50 characters
                if len(chunk_text.strip()) < 50:
                    continue

                # Create chunk item
                chunk_item = {
                    'id': f"{original_item.get('title', 'Unknown').replace(' ', '_').replace('(', '').replace(')', '')}_chunk_{chunk_id:02d}",
                    'title': original_item.get('title', 'Unknown'),
                    'content': chunk_text,
                    'source_type': 'pdf',
                    'sourcepage': original_item.get('url', ''),
                    'sourcefile': pdf_url,
                    'page_number': page_num,
                    'date': original_item.get('date'),
                    'zones': original_item.get('zones', []),
                    'type_innovatie': original_item.get('type_innovatie', []),
                    'pdfs': [],
                    'videos': original_item.get('videos', []),
                    'pictures': chunk_images
                }

                chunks.append(chunk_item)
                chunk_id += 1

        return chunks

    def _extract_raw_pdf_content(self, pdf_filepath: str, images_dir: str) -> dict:
        """
        Extract raw content from PDF using unstructured library.

        Args:
            pdf_filepath: Path to PDF file
            images_dir: Directory to save extracted images

        Returns:
            Dictionary with extracted content
        """
        try:
            logger.info(f"Reading PDF for file: {pdf_filepath} ...")

            # Extract content with image extraction enabled
            elements = partition_pdf(
                pdf_filepath,
                strategy="hi_res",
                extract_image_block_types=["Image", "Table"],
                extract_image_block_to_payload=True
            )

            # Process elements and organize by page
            pages = defaultdict(list)
            elements_data = []
            images = []

            for element in elements:
                # Get page number (handle None case)
                page_num = getattr(element.metadata, 'page_number', 1) or 1

                # Create element data
                element_data = {
                    "type": element.category,
                    "text": element.text or "",
                    "page_number": page_num,
                    "filename": os.path.splitext(os.path.basename(pdf_filepath))[0]
                }

                # Handle image extraction
                if hasattr(element.metadata, 'image_base64') and element.metadata.image_base64:
                    try:
                        # Generate unique filename
                        image_filename = f"{os.path.splitext(os.path.basename(pdf_filepath))[0]}_image_{len(images):03d}.png"
                        image_path = os.path.join(images_dir, image_filename)

                        # Decode and save image
                        image_data = base64.b64decode(element.metadata.image_base64)
                        with open(image_path, 'wb') as img_file:
                            img_file.write(image_data)

                        # Add relative path to element
                        element_data["image_path"] = f"images/{image_filename}"

                        # Add to images list
                        images.append({
                            "type": element.category,
                            "file_path": f"images/{image_filename}",
                            "page_number": page_num
                        })

                        # Remove base64 data from metadata to keep JSON clean
                        if hasattr(element.metadata, '__dict__'):
                            element.metadata.__dict__.pop('image_base64', None)
                        elif isinstance(element.metadata, dict):
                            element.metadata.pop('image_base64', None)

                    except Exception as e:
                        logger.warning(f"Failed to save image {image_filename}: {e}")

                # Add to page content
                pages[page_num].append(element_data["text"])
                elements_data.append(element_data)

            # Create page-organized text
            page_texts = {}
            for page_num in sorted(pages.keys()):
                page_texts[f"page_{page_num}"] = "\n".join(pages[page_num])

            # Combine all text
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
            logger.error(f"Failed to extract content from PDF {pdf_filepath}: {e}")
            return {
                "text": "",
                "page_texts": {},
                "elements": [],
                "images": [],
                "total_elements": 0,
                "total_images": 0,
                "total_pages": 0,
                "error": str(e)
            }

    def _create_raw_pdf_item(self, original_item: Dict[str, Any], pdf_url: str, raw_content: dict) -> Dict[str, Any]:
        """
        Create a raw PDF item with minimal processing.

        Args:
            original_item: Original detailed item
            pdf_url: URL of the PDF
            raw_content: Raw extracted content

        Returns:
            Raw PDF item dictionary
        """
        return {
            'title': f"{original_item.get('title', 'Unknown')} (PDF)",
            'url': pdf_url,
            'source_item_url': original_item.get('url', ''),
            'extracted_text': raw_content.get('text', ''),
            'page_texts': raw_content.get('page_texts', {}),
            'elements': raw_content.get('elements', []),
            'images': raw_content.get('images', []),
            'total_elements': raw_content.get('total_elements', 0),
            'total_images': raw_content.get('total_images', 0),
            'total_pages': raw_content.get('total_pages', 0),
            'extraction_metadata': {
                'strategy': 'hi_res',
                'extract_image_block_types': ['Image', 'Table'],
                'extract_image_block_to_payload': True
            }
        }

    def _process_single_pdf(self, pdf_url: str, pdfs_dir: str, images_dir: str) -> Optional[dict]:
        """
        Process a single PDF: download and extract content.

        Args:
            pdf_url: URL of the PDF to process
            pdfs_dir: Directory to save PDF files
            images_dir: Directory to save extracted images

        Returns:
            Raw content dictionary or None if failed
        """
        try:
            # Download PDF
            pdf_filename = self._download_pdf(pdf_url, pdfs_dir)
            if not pdf_filename:
                return None

            # Extract raw content
            return self._extract_raw_pdf_content(pdf_filename, images_dir)

        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_url}: {e}")
            return None

    def _download_pdf(self, pdf_url: str, output_dir: str) -> Optional[str]:
        """
        Download PDF from URL and save to local directory.

        Args:
            pdf_url: URL of the PDF to download
            output_dir: Directory to save the PDF

        Returns:
            Local filepath if successful, None otherwise
        """
        try:
            # Extract filename from URL
            parsed_url = urlparse(pdf_url)
            filename = unquote(os.path.basename(parsed_url.path))

            # Clean filename
            filename = re.sub(r'[^\w\-_\.]', '_', filename)
            if not filename.endswith('.pdf'):
                filename += '.pdf'

            filepath = os.path.join(output_dir, filename)

            # Download file
            headers = {'User-Agent': self.config.USER_AGENT}
            response = requests.get(pdf_url, headers=headers, timeout=self.config.DOWNLOAD_TIMEOUT)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded PDF: {filename}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to download PDF {pdf_url}: {e}")
            return None

    def _create_cleaned_pdf_item(self, original_item: Dict[str, Any], pdf_url: str, raw_content: dict) -> Dict[str, Any]:
        """
        Create a cleaned PDF item optimized for RAG.

        Args:
            original_item: Original detailed item
            pdf_url: URL of the PDF
            raw_content: Raw extracted content

        Returns:
            Cleaned PDF item dictionary
        """
        # Clean page texts
        cleaned_page_texts = {}
        for page_key, page_text in raw_content.get('page_texts', {}).items():
            cleaned_page_texts[page_key] = self._clean_text_for_rag(page_text)

        # Create minimal elements list (only essential fields)
        cleaned_elements = []

        # Add original elements
        for element in raw_content.get('elements', []):
            cleaned_element = {
                "type": element.get("type", ""),
                "text": self._clean_text_for_rag(element.get("text", "")),
                "page_number": element.get("page_number", 1),
                "filename": element.get("filename", "")
            }

            # Add image path if present
            if "image_path" in element:
                cleaned_element["image_path"] = element["image_path"]

            cleaned_elements.append(cleaned_element)

        # Add page texts as elements with type "text"
        for page_key, page_text in cleaned_page_texts.items():
            # Extract page number from page_key (e.g., "page_1" -> 1)
            page_num = 1
            if page_key.startswith("page_"):
                try:
                    page_num = int(page_key.replace("page_", ""))
                except ValueError:
                    page_num = 1

            # Only add if page text is not empty
            if page_text.strip():
                cleaned_elements.append({
                    "type": "text",
                    "text": page_text,
                    "page_number": page_num,
                    "filename": original_item.get('title', 'Unknown').replace(' (PDF)', '')
                })

        return {
            'title': f"{original_item.get('title', 'Unknown')} (PDF)",
            'url': pdf_url,
            'source_item_url': original_item.get('url', ''),
            'elements': cleaned_elements,
            'images': raw_content.get('images', []),
            'total_elements': len(cleaned_elements),
            'total_images': raw_content.get('total_images', 0),
            'total_pages': raw_content.get('total_pages', 0)
        }

    def process_pdfs(self, input_file: str, output_dir: str = "output/demo") -> None:
        """
        Process PDFs from detailed items and save results.

        Args:
            input_file: Path to detailed items JSON file
            output_dir: Output directory for results
        """
        # Create output directories
        pdfs_dir = os.path.join(output_dir, "pdfs")
        images_dir = os.path.join(pdfs_dir, "images")
        os.makedirs(pdfs_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)

        print(f"[PDF] Loading detailed items from: {input_file}")
        print(f"[PDF] Output structure:")
        print(f"  PDFs: {pdfs_dir}/")
        print(f"  Images: {images_dir}/")
        print(f"  JSON: {output_dir}/pdf_items_*_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        print(f"    - pdf_items_raw_*.json (raw extracted content)")
        print(f"    - pdf_items_cleaned_*.json (cleaned content)")
        print(f"    - pdf_items_rag_ready_*.json (RAG-ready chunks)")

        # Load detailed items
        with open(input_file, 'r', encoding='utf-8') as f:
            detailed_items = json.load(f)

        print(f"[PDF] Starting PDF processing...")

        # Process each detailed item
        raw_items = []
        cleaned_items = []
        rag_ready_items = []

        for i, item in enumerate(detailed_items, 1):
            print(f"[PDF] Item {i}/{len(detailed_items)}: '{item.get('title', 'Unknown')}' has {len(item.get('pdfs', []))} PDF(s)")

            for j, pdf_url in enumerate(item.get('pdfs', []), 1):
                if not pdf_url:
                    continue

                print(f"[PDF]   Processing PDF {j}/{len(item.get('pdfs', []))}: {os.path.basename(pdf_url)}")

                try:
                    # Process PDF
                    raw_content = self._process_single_pdf(pdf_url, pdfs_dir, images_dir)

                    if raw_content:
                        # Create raw item
                        raw_item = self._create_raw_pdf_item(item, pdf_url, raw_content)
                        raw_items.append(raw_item)

                        # Create cleaned item
                        cleaned_item = self._create_cleaned_pdf_item(item, pdf_url, raw_content)
                        cleaned_items.append(cleaned_item)

                        # Create RAG-ready chunks
                        rag_chunks = self._create_rag_ready_chunks(item, pdf_url, raw_content)
                        rag_ready_items.extend(rag_chunks)

                        print(f"[PDF]   ✓ Successfully processed PDF ({len(rag_chunks)} RAG chunks created)")
                    else:
                        print(f"[PDF]   ✗ Failed to process PDF")

                except Exception as e:
                    print(f"[PDF]   ✗ Error processing PDF: {e}")
                    continue

        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save raw items
        raw_output_file = os.path.join(output_dir, f"pdf_items_raw_{timestamp}.json")
        with open(raw_output_file, 'w', encoding='utf-8') as f:
            json.dump(raw_items, f, indent=2, ensure_ascii=False)
        print(f"[PDF] Saved raw items to: {raw_output_file}")

        # Save cleaned items
        cleaned_output_file = os.path.join(output_dir, f"pdf_items_cleaned_{timestamp}.json")
        with open(cleaned_output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_items, f, indent=2, ensure_ascii=False)
        print(f"[PDF] Saved cleaned items to: {cleaned_output_file}")

        # Save RAG-ready items
        rag_ready_output_file = os.path.join(output_dir, f"pdf_items_rag_ready_{timestamp}.json")
        with open(rag_ready_output_file, 'w', encoding='utf-8') as f:
            json.dump(rag_ready_items, f, indent=2, ensure_ascii=False)
        print(f"[PDF] Saved RAG-ready items to: {rag_ready_output_file}")

        print(f"[PDF] Completed processing. Successfully processed {len(raw_items)}/{len(detailed_items)} PDF items")
        print(f"[PDF] Created {len(rag_ready_items)} RAG-ready chunks")

        # Also save to the original pdfs directory for backward compatibility
        pdfs_raw_file = os.path.join(pdfs_dir, f"pdf_items_raw_{timestamp}.json")
        pdfs_cleaned_file = os.path.join(pdfs_dir, f"pdf_items_cleaned_{timestamp}.json")
        pdfs_rag_ready_file = os.path.join(pdfs_dir, f"pdf_items_rag_ready_{timestamp}.json")

        with open(pdfs_raw_file, 'w', encoding='utf-8') as f:
            json.dump(raw_items, f, indent=2, ensure_ascii=False)

        with open(pdfs_cleaned_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_items, f, indent=2, ensure_ascii=False)

        with open(pdfs_rag_ready_file, 'w', encoding='utf-8') as f:
            json.dump(rag_ready_items, f, indent=2, ensure_ascii=False)

        print(f"[PDF] Processed {len(raw_items)} PDF(s).")
        print(f"[PDF] Raw data saved to: {pdfs_raw_file}")
        print(f"[PDF] Cleaned data saved to: {pdfs_cleaned_file}")
        print(f"[PDF] RAG-ready data saved to: {pdfs_rag_ready_file}")

        return rag_ready_items


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Process PDFs from detailed items JSON.")
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to detailed_items JSON file (with PDFs to process)",
    )
    parser.add_argument(
        "--output-dir",
        default="output/demo",
        help="Directory to save extracted PDF JSON files (default: output/demo)",
    )
    args = parser.parse_args()

    # Setup logging to console
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    processor = PDFProcessor()
    processor.process_pdfs(args.input_file, args.output_dir)
