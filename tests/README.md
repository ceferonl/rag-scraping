# Test Strategy for RAG Scraping

## Overview

This is a **pragmatic test suite** designed for a **one-time scraping tool** for a static website. We focus on practical tests that actually help during development and maintenance.

## Test Categories

### 1. Smoke Tests (`test_smoke.py`)
**Purpose**: "Does it still work?"
- Tests that the scraper can still connect and scrape
- Verifies basic functionality without mocking
- Quick feedback if something breaks

**When to run**: Before making changes, after deployments

### 2. Data Validation Tests (`test_data_validation.py`)
**Purpose**: "Is the output correct?"
- Validates structure and quality of output files
- Checks data types, required fields, content quality
- Ensures RAG-ready format is correct

**When to run**: After scraping new data, when modifying output format

### 3. Regression Tests (`test_regression.py`)
**Purpose**: "Did I break anything?"
- Tests that core functionality remains stable
- Checks configuration values, data structures
- Detects unexpected changes

**When to run**: After code changes, before commits

## Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_smoke.py
pytest tests/test_data_validation.py
pytest tests/test_regression.py

# Run with verbose output
pytest -v

# Run only tests that don't require internet
pytest tests/test_regression.py tests/test_data_validation.py
```

## Test Philosophy

### What We Test
- ✅ **Real functionality** - actual scraping, not mocks
- ✅ **Output quality** - data structure and content
- ✅ **Configuration stability** - prevent accidental changes
- ✅ **File existence** - ensure outputs are created

### What We Don't Test
- ❌ **Mock-based unit tests** - overkill for scraping
- ❌ **Complex integration tests** - not needed for static site
- ❌ **Edge cases** - focus on happy path
- ❌ **Performance benchmarks** - not critical for one-time tool

## Adding New Tests

When adding new functionality:

1. **Smoke test**: Can the new feature be used?
2. **Data validation**: Does it produce correct output?
3. **Regression test**: Does it maintain existing behavior?

Example:
```python
# test_smoke.py
async def test_new_feature():
    """Smoke test: does the new feature work?"""
    # Test actual functionality

# test_data_validation.py
def test_new_feature_output():
    """Test: is the new feature output correct?"""
    # Validate output structure

# test_regression.py
def test_new_feature_doesnt_break_old():
    """Test: new feature doesn't break existing functionality"""
    # Ensure backward compatibility
```

## Maintenance

- **Keep tests simple** - they should be easy to understand and maintain
- **Focus on practical value** - test what actually matters
- **Skip when appropriate** - use `pytest.skip()` for optional tests
- **Update when needed** - tests should evolve with the codebase
