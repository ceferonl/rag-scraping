# Versnellingsplan RAG Scraping & Vectorization

A comprehensive Python-based RAG (Retrieval-Augmented Generation) pipeline for the Versnellingsplan knowledge base. Features functional architecture, web scraping, PDF processing, embedding generation, and vector database integration.

## Features

### Core Pipeline
- **Functional pipeline architecture** with demo and production modes
- **Asynchronous web scraping** using `crawl4ai` with intelligent delays
- **PDF content extraction** with fallback processing
- **RAG-ready chunking** with configurable size limits
- **YAML-based configuration** with environment-specific settings

### Data Extraction
- Main content, publication dates, zones, item types
- Associated files (PDFs, videos, pictures)
- Content validation and retry logic
- Comprehensive logging and error handling

### Vector Database Integration
- **Azure AI Search** integration with automatic index creation
- **Embedding generation** (Azure OpenAI, OpenAI)
- **Document upload** with validation and batch processing
- **Extensible architecture** for multiple vector database providers

### Quality & Testing
- **Comprehensive test suite** (functional, architectural, data validation)
- **Data validation** with automated reporting
- **Production-ready** with extensive error handling

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

3. Environment setup:
```bash
# Copy example environment file and edit with your credentials
cp .env.example .env
# Edit .env with your actual API keys and endpoints
```

## Usage

### Pipeline Modes

**Demo Pipeline** (5 items, fast testing):
```bash
uv run python -m rag_scraping --demo
```

**Production Pipeline** (full scraping):
```bash
uv run python -m rag_scraping --production
```

### Individual Components

**Scrape main page only**:
```bash
uv run python -m rag_scraping --main-page-only
```

**Scrape detailed items with limits**:
```bash
uv run python -m rag_scraping --detailed --max-items 10 --filter-type "Publicatie"
```

**Process PDFs from existing file**:
```bash
uv run python -m rag_scraping --process-pdfs detailed_items_20250827_145536.json
```

### Vector Database Operations

**Upload to Azure with embeddings**:
```bash
uv run python -m vector_db.upload --file output/production/rag_ready_unified_20250827_154459.json --create-index
```

**Validate documents**:
```bash
uv run python -m vector_db.validation --file output/production/rag_ready_unified_20250827_154459.json
```

### Configuration

Edit `config.yaml` for custom settings:
```yaml
scraping:
  request_delay: 4.0
  max_retries: 3

output:
  default_run_type: "production"  # or "demo"

embeddings:
  provider: "azure_openai"  # or "openai"
  model: "text-embedding-3-small"
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
uv run pytest

# Quick smoke tests
uv run pytest tests/test_functional_smoke.py

# Architecture tests
uv run pytest tests/test_architecture.py

# Data validation tests
uv run pytest tests/test_data_validation.py
```

## Project Structure

```
rag-scraping/
├── src/
│   ├── rag_scraping/                # Main scraping pipeline
│   │   ├── pipeline.py              # Functional pipeline orchestration
│   │   ├── scraping.py              # Web scraping logic
│   │   ├── pdf_processing.py        # PDF extraction & processing
│   │   ├── rag_chunking.py          # RAG-ready chunk creation
│   │   ├── models.py                # Pydantic data models
│   │   ├── config.py                # Configuration management
│   │   ├── utils.py                 # Shared utilities
│   │   └── __main__.py              # CLI entry point
│   └── vector_db/                   # Vector database integration
│       ├── base.py                  # Abstract base classes
│       ├── azure.py                 # Azure AI Search implementation
│       ├── embeddings.py            # Embedding generation
│       ├── upload.py                # Document upload logic
│       └── validation.py            # Data validation & reporting
├── tests/                           # Comprehensive test suite
├── config.yaml                     # Main configuration
├── notebooks/                      # Development & analysis scripts
└── output/                         # Generated data & logs
    ├── demo/                       # Demo pipeline outputs
    └── production/                 # Production pipeline outputs
```

## Development

### Code Quality
```bash
# Linting
uv run ruff check .

# Testing with coverage
uv run pytest --cov=src
```

### Architecture
- **Functional over OOP**: Pure functions, minimal classes
- **Configuration-driven**: YAML config with environment overrides
- **Modular design**: Independent, composable components
- **Error resilience**: Comprehensive retry and fallback logic

## Environment Variables

Required for full functionality (see `.env.example`):
```bash
# Azure OpenAI (embeddings)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key

# Azure AI Search (vector database)
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-search-key

# Alternative: OpenAI (set embeddings.provider: "openai")
OPENAI_API_KEY=your-openai-api-key
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

[Add contribution guidelines here]

## Potential TODOs

- [ ] Add evaluation module
- [ ] Split rag_scraping into scraping and transformation (embedding could be part of transformation instead of vector_db)
- [ ] Rename vector_db to publishing
- [ ] Enable different vector db publishers next to Azure AI Search


