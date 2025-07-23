"""
Functional smoke tests for the RAG Scraping pipeline.
Tests basic functionality of the new functional architecture.
"""

import pytest
import asyncio
import subprocess
import sys
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

from src.rag_scraping.config import load_config, load_config_with_paths
from src.rag_scraping.scraping import scrape_main_page, scrape_item_details
from src.rag_scraping.pipeline import scrape_main_page_only, scrape_detailed_items
from src.rag_scraping.models import MainPageItem, KnowledgeBaseItem


@pytest.mark.asyncio
async def test_config_loading():
    """Smoke test: can we load configuration?"""
    config = load_config("config.yaml")
    assert "scraping" in config
    assert "output" in config
    assert "rag" in config
    assert "logging" in config


@pytest.mark.asyncio
async def test_config_with_paths():
    """Smoke test: can we load config with paths?"""
    config = load_config_with_paths("config.yaml", "demo")
    assert "output_paths" in config
    assert config["output_paths"]["run_type"] == "demo"


@pytest.mark.asyncio
async def test_main_page_scraping():
    """Smoke test: can we scrape the main page with new functional interface?"""
    config = load_config("config.yaml")

    items = await scrape_main_page(config)

    # Basic checks
    assert len(items) > 0, "Should find at least some items"
    assert all(isinstance(item, MainPageItem) for item in items), "All items should be MainPageItem"

    # Check structure
    for item in items[:3]:  # Check first 3 items
        assert item.title, "Title should not be empty"
        assert item.url, "URL should not be empty"
        assert item.url.startswith('http'), "URL should be valid"
        assert item.item_type, "Item type should not be empty"


@pytest.mark.asyncio
async def test_pipeline_main_page_only():
    """Smoke test: can we run the main page pipeline?"""
    config = load_config_with_paths("config.yaml", "demo")

    items = await scrape_main_page_only(config)

    assert len(items) > 0, "Should find at least some items"
    assert all(isinstance(item, MainPageItem) for item in items), "All items should be MainPageItem"


@pytest.mark.asyncio
async def test_single_item_scraping():
    """Smoke test: can we scrape a single detailed item?"""
    config = load_config("config.yaml")

    # Create a test main page item
    test_item = MainPageItem(
        title="Test Item",
        url="https://www.versnellingsplan.nl/Kennisbank/vier-jaar-versnellen/",
        item_type="Publicatie"
    )

    detailed_item = await scrape_item_details(test_item, config)

    # Basic checks
    assert isinstance(detailed_item, KnowledgeBaseItem)
    assert detailed_item.title == test_item.title
    assert detailed_item.url == test_item.url
    assert detailed_item.main_content, "Should have main content"


@pytest.mark.asyncio
async def test_pipeline_detailed_items():
    """Smoke test: can we run the detailed scraping pipeline with limits?"""
    config = load_config_with_paths("config.yaml", "demo")

    items = await scrape_detailed_items(config, max_items=3)

    assert len(items) <= 3, "Should respect max_items limit"
    assert all(isinstance(item, KnowledgeBaseItem) for item in items), "All items should be KnowledgeBaseItem"

    # Check that items have content
    for item in items:
        assert item.title, "Item should have title"
        assert item.url, "Item should have URL"
        # Note: main_content might be empty if scraping fails, so we don't assert it


def test_cli_help():
    """Smoke test: does the CLI help work?"""
    result = subprocess.run(
        [sys.executable, "-m", "src.rag_scraping", "--help"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, "CLI help should work"
    assert "Versnellingsplan RAG Scraper" in result.stdout
    assert "--demo" in result.stdout
    assert "--production" in result.stdout


def test_output_files_exist():
    """Smoke test: do recent output files exist and have content?"""
    output_dir = Path("output/demo")

    if not output_dir.exists():
        pytest.skip("No output directory found - run a pipeline first")

    # Check for recent files (any type)
    json_files = list(output_dir.glob("*.json"))
    if not json_files:
        pytest.skip("No JSON files found - run a pipeline first")

    # Check that at least one file has reasonable content
    latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
    assert latest_file.stat().st_size > 100, f"File {latest_file.name} should have content"


if __name__ == "__main__":
    print("🧪 Running functional smoke tests...")

    # Test config loading
    try:
        config = load_config("config.yaml")
        print("✅ Config loading: PASS")
    except Exception as e:
        print(f"❌ Config loading: FAIL - {e}")

    # Test CLI help
    try:
        result = subprocess.run(
            [sys.executable, "-m", "src.rag_scraping", "--help"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ CLI help: PASS")
        else:
            print(f"❌ CLI help: FAIL - {result.stderr}")
    except Exception as e:
        print(f"❌ CLI help: FAIL - {e}")

    print("🎉 Smoke test summary complete!")
