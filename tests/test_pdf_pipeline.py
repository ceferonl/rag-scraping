import os
import glob
import json
from pathlib import Path
import pytest
from src.rag_scraping.pdf_processing import process_all_pdfs
from src.rag_scraping.models import KnowledgeBaseItem

def test_pdf_pipeline(tmp_path):
    # Use a sample PDF from the demo output dir
    pdf_dir = Path('output/demo/pdfs')
    pdf_files = list(pdf_dir.glob('*.pdf'))
    assert pdf_files, 'No sample PDFs found for test.'
    sample_pdf = str(pdf_files[0])

    # Create a fake KnowledgeBaseItem
    item = KnowledgeBaseItem(
        title='Test PDF',
        url='https://example.com',
        date=None,
        zones=[],
        type_innovatie=[],
        pdfs=[sample_pdf],
        videos=[],
        pictures=[],
        main_content='Test content',
        item_type='Test'
    )
    config = {
        'output_paths': {
            'base_dir': tmp_path,
            'pdfs_dir': tmp_path / 'pdfs',
            'images_dir': tmp_path / 'pdfs' / 'images',
        },
        'timestamp': 'pytest',
        'rag': {'min_chunk_size': 10}
    }
    os.makedirs(config['output_paths']['pdfs_dir'], exist_ok=True)
    os.makedirs(config['output_paths']['images_dir'], exist_ok=True)

    raw, cleaned, rag = process_all_pdfs([item], config)

    # Check output files
    for suffix in ['raw', 'cleaned', 'rag_ready']:
        files = list(tmp_path.glob(f'pdf_items_{suffix}_pytest.json'))
        assert files, f'No output file for {suffix}'
        with open(files[0]) as f:
            data = json.load(f)
            assert data, f'Output file {files[0]} is empty'

    # Check page_number and cleaning in cleaned output
    cleaned_file = tmp_path / 'pdf_items_cleaned_pytest.json'
    with open(cleaned_file) as f:
        cleaned_data = json.load(f)
        for item in cleaned_data:
            for el in item['elements']:
                assert isinstance(el['page_number'], int)
                assert el['page_number'] is not None
                # Check cleaning: no newlines, no double spaces
                assert '\n' not in el['text']
                assert '  ' not in el['text']
