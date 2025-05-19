# RAG Scraping

A Python-based web scraping tool designed to extract and process content from the Versnellingsplan knowledge base. This tool is part of a larger RAG (Retrieval-Augmented Generation) system, specifically handling the data collection and preprocessing phase.

## Features

- Asynchronous web scraping using `aiohttp`
- Structured data extraction from Versnellingsplan knowledge base
- Support for extracting:
  - Main content
  - Publication dates
  - Zones
  - Item types
  - Associated files
- Comprehensive test suite with unit and integration tests
- Configurable output formats

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rag-scraping.git
cd rag-scraping
```

2. Install dependencies:
```bash
uv pip install .
```

## Usage

### Basic Usage

```python
from rag_scraping.versnellingsplan import VersnellingsplanScraper

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

### Saving Results

```python
# Save results to a JSON file
scraper.save_results("output.json")
```

## Testing

The project includes a comprehensive test suite. Run tests using pytest:

```bash
# Run all tests
python -m pytest

# Run specific test files
python -m pytest tests/test_scraper.py
python -m pytest tests/test_integration_main_page.py
```

## Project Structure

```
rag-scraping/
├── src/
│   └── rag_scraping/
│       ├── __init__.py
│       ├── versnellingsplan.py      # Main scraper implementation
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
