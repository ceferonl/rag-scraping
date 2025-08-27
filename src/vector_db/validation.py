"""
Validation functionality for vector database documents.

This module provides standalone validation that can be run independently
from upload processes to verify document quality and compatibility.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from ..rag_scraping.utils import normalize_document_id, format_date

logger = logging.getLogger(__name__)


def validate_document_for_vector_db(doc: Dict[str, Any]) -> List[str]:
    """
    Validate a single document for vector database compatibility.

    Checks for common issues that would cause upload failures:
    - Invalid document ID format
    - Missing required fields
    - Invalid date format
    - Content quality issues

    Args:
        doc: Document dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check document ID
    doc_id = doc.get('id', '')
    if not doc_id:
        errors.append("Missing required field 'id'")
    elif not re.match(r'^[a-zA-Z0-9_\-=]+$', doc_id):
        errors.append(f"Invalid document ID format: '{doc_id}' - must only contain [a-zA-Z0-9_\\-=]")

    # Check required fields
    required_fields = ['title', 'content']
    for field in required_fields:
        if not doc.get(field):
            errors.append(f"Missing or empty required field '{field}'")

    # Check date format if present
    date_val = doc.get('date')
    if date_val:
        if isinstance(date_val, str):
            # Should be ISO8601 with timezone
            if not (date_val.endswith('Z') or '+' in date_val or (date_val.count('-') > 2 and 'T' in date_val)):
                errors.append(f"Invalid date format: '{date_val}' - must be ISO8601 with timezone")
        elif hasattr(date_val, 'isoformat'):
            # It's a datetime object - should be formatted as string
            errors.append(f"Date should be formatted as ISO8601 string, not {type(date_val)}")
        else:
            errors.append(f"Invalid date type: {type(date_val)} - must be ISO8601 string")

    # Check content quality
    content = doc.get('content', '')
    if content:
        if len(content.strip()) < 10:
            errors.append("Content too short (less than 10 characters)")

        # Check for error indicators
        content_lower = content.lower()
        error_indicators = [
            'error 404', '404 not found', 'page not found',
            'access denied', 'forbidden', 'unauthorized',
            'server error', 'internal server error',
            'temporarily unavailable', 'maintenance mode'
        ]
        for indicator in error_indicators:
            if indicator in content_lower:
                errors.append(f"Content appears to contain error message: '{indicator}'")
                break

    return errors


def validate_and_fix_documents(docs: List[Dict[str, Any]], auto_fix: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Validate and optionally fix documents for vector DB compatibility.

    Args:
        docs: List of documents to validate and fix
        auto_fix: Whether to automatically fix common issues

    Returns:
        Tuple of (fixed_documents, stats)
    """
    stats = {
        'input_count': len(docs),
        'fixed_ids': 0,
        'fixed_dates': 0,
        'invalid_removed': 0,
        'output_count': 0,
        'warnings': 0
    }

    fixed_docs = []

    for i, doc in enumerate(docs):
        doc_copy = doc.copy() if auto_fix else doc

        # Fix document ID if needed and auto_fix is enabled
        if auto_fix and 'id' in doc_copy:
            original_id = doc_copy['id']
            normalized_id = normalize_document_id(original_id)
            if normalized_id != original_id:
                doc_copy['id'] = normalized_id
                stats['fixed_ids'] += 1
                logger.debug(f"Fixed ID: {original_id} -> {normalized_id}")

        # Fix date format if needed and auto_fix is enabled
        if auto_fix and 'date' in doc_copy and doc_copy['date']:
            original_date = doc_copy['date']
            if not isinstance(original_date, str):
                # Convert to string with proper formatting
                fixed_date = format_date(original_date)
                if fixed_date != original_date:
                    doc_copy['date'] = fixed_date
                    stats['fixed_dates'] += 1
                    logger.debug(f"Fixed date: {original_date} -> {fixed_date}")
            else:
                # Check if string date needs timezone
                if not (original_date.endswith('Z') or '+' in original_date or (original_date.count('-') > 2 and 'T' in original_date)):
                    fixed_date = format_date(original_date)
                    if fixed_date != original_date:
                        doc_copy['date'] = fixed_date
                        stats['fixed_dates'] += 1
                        logger.debug(f"Fixed date: {original_date} -> {fixed_date}")

        # Validate final document
        errors = validate_document_for_vector_db(doc_copy)

        if errors:
            # Count as warning if not removing
            stats['warnings'] += 1

            # Log the first error for this document
            doc_id = doc_copy.get('id', f'doc_{i}')
            logger.warning(f"Document {doc_id}: {errors[0]}" + (f" (+{len(errors)-1} more)" if len(errors) > 1 else ""))

            # Check if we should remove invalid documents
            critical_errors = [e for e in errors if any(phrase in e.lower() for phrase in ['missing', 'required', 'empty'])]
            if critical_errors and auto_fix:
                logger.warning(f"Removing document {doc_id} due to critical errors")
                stats['invalid_removed'] += 1
                continue

        fixed_docs.append(doc_copy)

    stats['output_count'] = len(fixed_docs)

    return fixed_docs, stats


def validate_documents_from_file(
    file_path: str,
    auto_fix: bool = True,
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate documents from a JSON file.

    Args:
        file_path: Path to JSON file containing documents
        auto_fix: Whether to automatically fix common issues
        output_file: Optional path to save fixed documents

    Returns:
        Validation results dictionary
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info(f"Loading documents from {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        docs = json.load(f)

    logger.info(f"Loaded {len(docs)} documents")

    # Validate and fix
    fixed_docs, stats = validate_and_fix_documents(docs, auto_fix=auto_fix)

    # Save fixed documents if requested
    if output_file and auto_fix and (stats['fixed_ids'] > 0 or stats['fixed_dates'] > 0):
        output_path = Path(output_file)
        logger.info(f"Saving {len(fixed_docs)} fixed documents to {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fixed_docs, f, indent=2, ensure_ascii=False)

    # Create validation report
    results = {
        'file_path': str(file_path),
        'validation_stats': stats,
        'documents': fixed_docs if auto_fix else docs,
        'is_valid': stats['warnings'] == 0 and stats['invalid_removed'] == 0
    }

    # Log summary
    logger.info(f"Validation complete: {stats['input_count']} -> {stats['output_count']} documents")
    if stats['fixed_ids'] > 0 or stats['fixed_dates'] > 0:
        logger.info(f"Auto-fixed: {stats['fixed_ids']} IDs, {stats['fixed_dates']} dates")
    if stats['warnings'] > 0:
        logger.warning(f"Found {stats['warnings']} documents with validation issues")
    if stats['invalid_removed'] > 0:
        logger.warning(f"Removed {stats['invalid_removed']} invalid documents")

    return results


def generate_validation_report(results: Dict[str, Any], output_file: Optional[str] = None) -> str:
    """
    Generate a human-readable validation report.

    Args:
        results: Results from validate_documents_from_file
        output_file: Optional file to save the report

    Returns:
        Report as string
    """
    stats = results['validation_stats']

    report_lines = [
        "# Vector Database Document Validation Report",
        f"**File:** {results['file_path']}",
        f"**Validation Date:** {results.get('timestamp', 'N/A')}",
        "",
        "## Summary",
        f"- Input documents: {stats['input_count']}",
        f"- Output documents: {stats['output_count']}",
        f"- Documents with issues: {stats['warnings']}",
        f"- Documents removed: {stats['invalid_removed']}",
        f"- Overall status: {'✅ VALID' if results['is_valid'] else '⚠️ ISSUES FOUND'}",
        "",
        "## Auto-fixes Applied",
        f"- Document IDs normalized: {stats['fixed_ids']}",
        f"- Date formats fixed: {stats['fixed_dates']}",
        "",
    ]

    if results['is_valid']:
        report_lines.extend([
            "## ✅ All Documents Valid",
            "All documents passed validation and are ready for vector database upload.",
        ])
    else:
        report_lines.extend([
            "## ⚠️ Issues Found",
            f"Found issues in {stats['warnings']} documents.",
            "Review the logs for specific details about validation errors.",
        ])

    report = "\n".join(report_lines)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Validation report saved to {output_file}")

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate RAG documents for vector database compatibility")
    parser.add_argument("json_file", help="Path to JSON file containing documents")
    parser.add_argument("--no-fix", action="store_true", help="Don't automatically fix issues")
    parser.add_argument("--output", help="Path to save fixed documents")
    parser.add_argument("--report", help="Path to save validation report")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        results = validate_documents_from_file(
            args.json_file,
            auto_fix=not args.no_fix,
            output_file=args.output
        )

        # Generate report
        report = generate_validation_report(results, args.report)
        print("\n" + report)

        # Exit with error code if validation failed
        if not results['is_valid']:
            exit(1)

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        exit(1)
