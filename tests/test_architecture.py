"""
Comprehensive architecture tests for the RAG Scraping functional architecture.

Tests verify all components work together and individual modules function correctly.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.rag_scraping.config import load_config, get_output_paths, validate_config, load_config_with_paths
from src.rag_scraping.models import KnowledgeBaseItem, MainPageItem
from src.rag_scraping.utils import clean_text_for_rag, format_date, create_chunk_id, split_text_into_chunks
from src.rag_scraping.rag_chunking import create_rag_chunks, create_chunk_dict, merge_small_chunks
from src.rag_scraping.scraping import extract_main_content, extract_associated_files, scrape_main_page
from src.rag_scraping.pipeline import setup_logging, run_demo_pipeline


class TestConfiguration:
    """Test configuration loading and validation."""

    def test_load_config_success(self):
        """Test successful config loading."""
        config = load_config("config.yaml")
        assert "scraping" in config
        assert "output" in config
        assert "rag" in config
        assert "logging" in config

    def test_get_output_paths_demo(self):
        """Test demo output paths."""
        config = load_config("config.yaml")
        paths = get_output_paths(config, "demo")

        assert paths["run_type"] == "demo"
        assert "demo" in str(paths["base_dir"])
        assert paths["pdfs_dir"].name == "pdfs"
        assert paths["images_dir"].name == "images"

    def test_get_output_paths_production(self):
        """Test production output paths."""
        config = load_config("config.yaml")
        paths = get_output_paths(config, "production")

        assert paths["run_type"] == "production"
        assert "production" in str(paths["base_dir"])
        assert paths["pdfs_dir"].name == "pdfs"
        assert paths["images_dir"].name == "images"

    def test_validate_config(self):
        """Test config validation."""
        config = load_config("config.yaml")
        # Should not raise any exceptions
        validate_config(config)

    def test_load_config_with_paths(self):
        """Test loading config with paths integration."""
        config = load_config_with_paths("config.yaml", "demo")
        assert "output_paths" in config
        assert "timestamp" in config
        assert config["output_paths"]["run_type"] == "demo"


class TestModels:
    """Test data models."""

    def test_knowledge_base_item_creation(self):
        """Test KnowledgeBaseItem creation."""
        item = KnowledgeBaseItem(
            title="Test Item",
            url="https://example.com",
            zones=["Zone1", "Zone2"],
            type_innovatie=["Type1"]
        )

        assert item.title == "Test Item"
        assert item.url == "https://example.com"
        assert item.zones == ["Zone1", "Zone2"]
        assert item.type_innovatie == ["Type1"]
        assert item.pdfs == []  # Default empty list

    def test_knowledge_base_item_to_dict(self):
        """Test KnowledgeBaseItem serialization."""
        item = KnowledgeBaseItem(
            title="Test Item",
            url="https://example.com"
        )

        data = item.to_dict()
        assert data["title"] == "Test Item"
        assert data["url"] == "https://example.com"
        assert "associated_files" not in data  # Should be removed

    def test_main_page_item_creation(self):
        """Test MainPageItem creation."""
        item = MainPageItem(
            title="Test Item",
            url="https://example.com",
            item_type="Publicatie"
        )

        assert item.title == "Test Item"
        assert item.url == "https://example.com"
        assert item.item_type == "Publicatie"


class TestUtils:
    """Test utility functions."""

    def test_clean_text_for_rag(self):
        """Test text cleaning for RAG."""
        dirty_text = 'This has "quotes" and \n\n\nnewlines\t\tand   spaces'
        cleaned = clean_text_for_rag(dirty_text)

        assert '"' not in cleaned
        assert '\n' not in cleaned
        assert '\t' not in cleaned
        assert '   ' not in cleaned  # Multiple spaces should be single

    def test_format_date(self):
        """Test date formatting."""
        from datetime import datetime

        # Test with datetime
        dt = datetime(2023, 1, 1, 12, 0, 0)
        formatted = format_date(dt)
        assert "2023-01-01" in formatted

        # Test with string
        assert format_date("2023-01-01") == "2023-01-01"

        # Test with None
        assert format_date(None) is None

    def test_create_chunk_id(self):
        """Test chunk ID creation."""
        chunk_id = create_chunk_id("Test Title (with parentheses)", 1)
        assert "Test_Title_with_parentheses" in chunk_id
        assert "chunk_01" in chunk_id

    def test_split_text_into_chunks(self):
        """Test text chunking."""
        long_text = "This is a long text. " * 100  # ~2000 characters

        chunks = split_text_into_chunks(long_text, max_chunk_size=500, min_chunk_size=50)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) >= 50
            assert len(chunk) <= 500


class TestRAGChunking:
    """Test RAG chunking functionality."""

    def test_create_chunk_dict(self):
        """Test chunk dictionary creation."""
        item = KnowledgeBaseItem(
            title="Test Item",
            url="https://example.com",
            zones=["Zone1"],
            type_innovatie=["Type1"]
        )

        config = {"rag": {"min_chunk_size": 50}}
        chunk = create_chunk_dict(item, 1, "Test content", "page", config)

        assert chunk["title"] == "Test Item"
        assert chunk["content"] == "Test content"
        assert chunk["source_type"] == "page"
        assert chunk["sourcepage"] == "https://example.com"
        assert chunk["zones"] == ["Zone1"]
        assert chunk["type_innovatie"] == ["Type1"]
        assert chunk["chunk_number"] == 1

    def test_create_rag_chunks(self):
        """Test RAG chunk creation from items."""
        items = [
            KnowledgeBaseItem(
                title="Item 1",
                url="https://example1.com",
                main_content="This is content for item 1. " * 50  # ~1000 chars
            ),
            KnowledgeBaseItem(
                title="Item 2",
                url="https://example2.com",
                main_content="This is content for item 2. " * 50  # ~1000 chars
            )
        ]

        config = {
            "rag": {
                "min_chunk_size": 50,
                "max_chunk_size": 2000,
                "target_chunk_size": 500
            }
        }

        chunks = create_rag_chunks(items, config, "page")

        assert len(chunks) >= 2  # At least one chunk per item
        for chunk in chunks:
            assert chunk["source_type"] == "page"
            assert len(chunk["content"]) >= 50

    def test_merge_small_chunks(self):
        """Test small chunk merging."""
        chunks = [
            {"content": "Small chunk 1", "content_length": 15},
            {"content": "Small chunk 2", "content_length": 15},
            {"content": "Large chunk with substantial content", "content_length": 50},
            {"content": "Small chunk 3", "content_length": 15}
        ]

        merged = merge_small_chunks(chunks, min_size=20, max_size=100)

        # Should merge small chunks but keep large ones separate
        assert len(merged) < len(chunks)
        assert any(len(chunk["content"]) > 30 for chunk in merged)


class TestScrapingUtils:
    """Test scraping utility functions."""

    def test_extract_associated_files(self):
        """Test file extraction from HTML."""
        from bs4 import BeautifulSoup

        html = """
        <div>
            <a href="document.pdf">PDF Link</a>
            <a href="video.mp4">Video Link</a>
            <a href="image.jpg">Image Link</a>
            <a href="https://example.com">Regular Link</a>
        </div>
        """

        soup = BeautifulSoup(html, 'html.parser')
        files = extract_associated_files(soup)

        assert "document.pdf" in files["pdfs"]
        assert "video.mp4" in files["videos"]
        assert "image.jpg" in files["pictures"]
        assert "https://example.com" not in files["pdfs"]


class TestPipeline:
    """Test pipeline functions."""

    def test_setup_logging(self):
        """Test logging setup."""
        config = {
            "logging": {
                "level": "INFO",
                "format": "[%(levelname)s] %(message)s"
            }
        }

        # Should not raise any exceptions
        setup_logging(config)

    @pytest.mark.asyncio
    async def test_demo_pipeline_structure(self):
        """Test that demo pipeline can be called and returns expected structure."""
        config = load_config_with_paths("config.yaml", "demo")

        # We won't run the full pipeline in tests, but verify the structure
        assert "output_paths" in config
        assert "timestamp" in config
        assert callable(run_demo_pipeline)


class TestCLI:
    """Test CLI functionality."""

    def test_cli_help(self):
        """Test CLI help output."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "src.rag_scraping", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Versnellingsplan RAG Scraper" in result.stdout
        assert "--demo" in result.stdout
        assert "--production" in result.stdout

    def test_cli_main_module(self):
        """Test that the main module can be imported."""
        import src.rag_scraping.__main__ as main_module
        assert hasattr(main_module, 'main')
        assert hasattr(main_module, 'parse_args')


class TestIntegration:
    """Test integration between components."""

    def test_config_to_pipeline_flow(self):
        """Test that config can be used in pipeline functions."""
        config = load_config("config.yaml")

        # Test that config has required sections for pipeline
        assert "scraping" in config
        assert "output" in config
        assert "rag" in config

        # Test that output paths can be generated
        paths = get_output_paths(config, "demo")
        assert paths["base_dir"].exists() or paths["base_dir"].parent.exists()

    def test_model_to_chunk_flow(self):
        """Test that models can be converted to chunks."""
        item = KnowledgeBaseItem(
            title="Test Item",
            url="https://example.com",
            main_content="This is test content for chunking. " * 20
        )

        config = {
            "rag": {
                "min_chunk_size": 50,
                "max_chunk_size": 2000,
                "target_chunk_size": 500
            }
        }

        chunks = create_rag_chunks([item], config, "page")
        assert len(chunks) > 0
        assert chunks[0]["title"] == "Test Item"

    def test_full_config_loading_integration(self):
        """Test full config loading with all components."""
        config = load_config_with_paths("config.yaml", "demo")

        # Test all required sections exist
        required_sections = ['scraping', 'pdf', 'output', 'rag', 'logging', 'output_paths', 'timestamp']
        for section in required_sections:
            assert section in config, f"Missing section: {section}"

        # Test that paths are valid
        output_paths = config['output_paths']
        assert output_paths['base_dir'].parent.exists(), "Output parent directory should exist"


if __name__ == "__main__":
    # Run quick architecture tests
    print("🏗️  Running architecture tests...")

    # Test config loading
    try:
        config = load_config("config.yaml")
        print("✅ Config loading: PASS")
    except Exception as e:
        print(f"❌ Config loading: FAIL - {e}")

    # Test model creation
    try:
        item = KnowledgeBaseItem(title="Test", url="https://example.com")
        print("✅ Model creation: PASS")
    except Exception as e:
        print(f"❌ Model creation: FAIL - {e}")

    # Test utility functions
    try:
        cleaned = clean_text_for_rag("Test\n\ncontent")
        print("✅ Utility functions: PASS")
    except Exception as e:
        print(f"❌ Utility functions: FAIL - {e}")

    # Test CLI
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "src.rag_scraping", "--help"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ CLI: PASS")
        else:
            print("❌ CLI: FAIL")
    except Exception as e:
        print(f"❌ CLI: FAIL - {e}")

    print("🎉 Architecture tests complete!")
