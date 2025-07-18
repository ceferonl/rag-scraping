# RAG Scraping Development Guide

## Project Structure
- Python package using `uv` for dependency management
- Async web scraping with `crawl4ai`
- Pydantic models for data validation
- CLI interface with configurable scope limiting

## Development Commands
- **Install dependencies**: `uv sync`
- **Run tests**: `python -m pytest`
- **Lint code**: `ruff check .`
- **Format code**: `ruff format .`
- **Run scraper**: `python -m rag_scraping.pages --output-dir output --max-items 10`

## Code Style
- Use 4-space indentation
- Follow PEP 8 naming conventions (snake_case for functions/variables)
- Type hints for all function parameters and return values
- Use async/await for I/O operations
- Docstrings for all public functions (Google style)
- Import organization: stdlib, third-party, local imports

## CLI Design Philosophy
- Use CLI arguments to limit execution scope (--max-items, --max-details)
- Provide granular control over processing steps
- Enable iterative development and testing
- Support different output formats and validation levels

## Error Handling
- Use appropriate exception types
- Provide meaningful error messages
- Handle network failures gracefully
- Validate data with Pydantic models
- Log important events and errors

## Testing Strategy
- Unit tests for individual components
- Use CLI arguments to test limited scopes
- Mock external dependencies in tests
- Test data validation thoroughly
- Use pytest fixtures for common test data

## Data Models
- Use Pydantic for data validation and serialization
- Define clear models for scraped content
- Handle optional fields appropriately
- Support multiple export formats (JSON, CSV, Markdown)

## Workflow Development
- Use Quarto files for iterative workflow testing
- Prototype in notebooks before implementing in modules
- Use CLI arguments to test specific workflow steps
- Document workflow decisions in Dutch explanations

## Dependencies
- Prefer well-maintained packages
- Use `crawl4ai` for web scraping
- Use `pydantic` for data validation
- Use `click` or `argparse` for CLI interfaces
- Add new dependencies via `uv add package_name`

## Git Workflow
- Use conventional commits (fix:, feat:, docs:, chore:)
- Example: `git commit -m "feat: add PDF content extraction"`
- Always test CLI functionality before committing
- Update documentation when adding new CLI options