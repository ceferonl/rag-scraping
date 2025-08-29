# Versnellingslan Vectorization

A Python-based web scraping tool designed to extract and process content from the Versnellingsplan knowledge base. This tool is part of a larger RAG (Retrieval-Augmented Generation) system, specifically handling the data collection and preprocessing phase.

## Features

- Asynchronous web scraping using `crawl4ai`
- Structured data extraction from Versnellingsplan knowledge base
- Support for extracting:
  - Main content
  - Publication dates
  - Zones
  - Item types
  - Associated files (PDFs, videos, pictures)
- Command-line interface with configurable options
- Data validation using Pydantic models
- PDF content extraction and processing
- Multiple export formats (JSON, CSV, Markdown)
- Comprehensive test suite with unit and integration tests

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rag-scraping.git
cd rag-scraping
```

2. Install dependencies:
```bash
uv sync
```

3. Install additional dependencies for PDF processing (optional):
```bash
uv add unstructured
```

## Usage

### Basic Usage

```python
from rag_scraping.pages import VersnellingsplanScraper

# Initialize the scraper
scraper = VersnellingsplanScraper()

# Scrape the knowledge base
items = await scraper.scrape()

# Process the results
for item in items:
    print(f"Title: {item.title}")
    print(f"URL: {item.url}")
    print(f"Content: {item.main_content[:200]}...")
```

### CLI Usage

The project includes a command-line interface for easy usage:

```bash
# Scrape main page items only
python -m rag_scraping.pages --output-dir output/main --max-items 10

# Scrape main page + detailed items with validation
python -m rag_scraping.pages --output-dir output/detailed --max-items 5 --max-details 3 --validate

# Process PDFs from detailed items
python -m rag_scraping.pdfs --input-file output/detailed/detailed_items.json --output-dir output/pdfs

# Export to different formats
python -m rag_scraping.pages --output-dir output --export csv,markdown
```

### Saving Results

```python
# Save results to a JSON file
scraper.save_results("output.json")
```

## Testing

The project includes a limited test suite for the scraping (including pdf extraction and chunking) part.

Run tests using pytest:

```bash
# Run all tests
python -m pytest

# Run specific test files
python -m pytest tests/test_scraper.py
python -m pytest tests/test_integration_main_page.py
```

There are no tests for the vectorization and uploading yet.


## Project Structure

```
rag-scraping/
├── src/
│   └── rag_scraping/
│       ├── __init__.py
│       ├── pages.py                 # Main scraper implementation
│       ├── pdfs.py                  # PDF processing module
│       └── knowledge_base_item.py   # Data model for scraped items
├── tests/
│   ├── conftest.py                  # Shared test fixtures
│   ├── test_scraper.py             # Unit tests for scraper
│   ├── test_knowledge_base_item.py # Tests for data model
│   └── test_integration_*.py       # Integration tests
└── requirements.txt
```

## Development

### Code Quality

The project uses `ruff` for linting and code quality checks. Run the linter:

```bash
ruff check .
```

### Adding New Features

1. Create a new branch for your feature
2. Add tests for new functionality
3. Implement the feature
4. Run tests and linting
5. Submit a pull request

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Potential TODO's
- [ ] Add evaluation module
- [ ] Split rag_scraping into scrapin and transformation (embedding could be part of transforamtion instead of vector_db)
- [ ] Rename vector_db to publishing
- [ ] Enable different vector db publishers next to Azure AI Search


