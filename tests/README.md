# Test Strategy for RAG Scraping

## Overview

This is a **pragmatic test suite** designed for the **functional RAG scraping architecture**. We focus on practical tests that verify the new functional pipeline works correctly.

## Test Categories

### 1. Functional Smoke Tests (`test_functional_smoke.py`)
**Purpose**: "Does the new functional architecture work?"
- Tests basic functionality of the new functional interface
- Verifies config loading, main page scraping, pipeline functions
- Tests CLI interface and basic integration
- Quick feedback if core functionality breaks

**When to run**: Before making changes, after refactoring

### 2. Architecture Tests (`test_architecture.py`)
**Purpose**: "Do all components work together?"
- Comprehensive tests of all modules and their integration
- Tests configuration, models, utils, chunking, scraping
- Verifies pipeline functions and CLI functionality
- Tests both individual components and their interactions

**When to run**: After architectural changes, before major releases

### 3. Data Validation Tests (`test_data_validation.py`)
**Purpose**: "Is the output correct?"
- Validates structure and quality of output files
- Checks data types, required fields, content quality
- Ensures RAG-ready format is correct
- Independent of architecture changes

**When to run**: After scraping new data, when modifying output format

## Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_functional_smoke.py
pytest tests/test_architecture.py
pytest tests/test_data_validation.py

# Run with verbose output
pytest -v

# Run only tests that don't require internet
pytest tests/test_architecture.py tests/test_data_validation.py

# Run tests with PYTHONPATH (if needed)
PYTHONPATH=/workspace pytest tests/
```

## Test Philosophy

### What We Test
- ✅ **Functional interface** - new functional pipeline architecture
- ✅ **Real functionality** - actual scraping with functional approach
- ✅ **Configuration management** - loading and validation
- ✅ **Component integration** - modules working together
- ✅ **CLI interface** - command-line functionality
- ✅ **Output quality** - data structure and content
- ✅ **Model validation** - data structures and serialization

### What We Don't Test
- ❌ **Old class-based interface** - removed in refactoring
- ❌ **Mock-based unit tests** - focus on integration
- ❌ **Complex edge cases** - focus on happy path
- ❌ **Performance benchmarks** - not critical for tool

## Adding New Tests

When adding new functionality:

1. **Functional smoke test**: Can the new feature be used with the functional interface?
2. **Architecture test**: Does it integrate well with other components?
3. **Data validation**: Does it produce correct output?

Example:
```python
# test_functional_smoke.py
@pytest.mark.asyncio
async def test_new_feature():
    """Smoke test: does the new feature work?"""
    config = load_config_with_paths("config.yaml", "demo")
    result = await new_feature_function(config)
    assert result is not None

# test_architecture.py
def test_new_feature_integration():
    """Test: does the new feature integrate with other components?"""
    # Test integration with config, models, etc.

# test_data_validation.py
def test_new_feature_output():
    """Test: is the new feature output correct?"""
    # Validate output structure and quality
```

## Maintenance

- **Keep tests simple** - they should be easy to understand and maintain
- **Focus on practical value** - test what actually matters
- **Skip when appropriate** - use `pytest.skip()` for optional tests
- **Update when needed** - tests should evolve with the codebase
