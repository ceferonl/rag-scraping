#!/usr/bin/env python3
"""
Quick architecture smoke test.

Run this to verify the new functional architecture works without running the full pipeline.
"""

import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("🔍 Testing imports...")

    try:
        from rag_scraping.config import load_config, get_output_paths
        print("  ✅ config module")
    except Exception as e:
        print(f"  ❌ config module: {e}")
        return False

    try:
        from rag_scraping.models import KnowledgeBaseItem, MainPageItem
        print("  ✅ models module")
    except Exception as e:
        print(f"  ❌ models module: {e}")
        return False

    try:
        from rag_scraping.utils import clean_text_for_rag, format_date
        print("  ✅ utils module")
    except Exception as e:
        print(f"  ❌ utils module: {e}")
        return False

    try:
        from rag_scraping.rag_chunking import create_rag_chunks
        print("  ✅ rag_chunking module")
    except Exception as e:
        print(f"  ❌ rag_chunking module: {e}")
        return False

    try:
        from rag_scraping.scraping import extract_main_content
        print("  ✅ scraping module")
    except Exception as e:
        print(f"  ❌ scraping module: {e}")
        return False

    try:
        from rag_scraping.pdf_processing import process_pdfs_from_items
        print("  ✅ pdf_processing module")
    except Exception as e:
        print(f"  ❌ pdf_processing module: {e}")
        return False

    try:
        from rag_scraping.pipeline import run_demo_pipeline
        print("  ✅ pipeline module")
    except Exception as e:
        print(f"  ❌ pipeline module: {e}")
        return False

    return True


def test_config():
    """Test configuration loading."""
    print("\n🔧 Testing configuration...")

    try:
        from rag_scraping.config import load_config, get_output_paths, validate_config

        # Test config loading
        config = load_config("config.yaml")
        print("  ✅ Config file loaded")

        # Test validation
        validate_config(config)
        print("  ✅ Config validation passed")

        # Test demo paths
        demo_paths = get_output_paths(config, "demo")
        assert "demo" in str(demo_paths["base_dir"])
        print("  ✅ Demo paths generated")

        # Test main paths
        main_paths = get_output_paths(config, "main")
        assert "main" in str(main_paths["base_dir"])
        print("  ✅ Main paths generated")

        return True

    except Exception as e:
        print(f"  ❌ Config test failed: {e}")
        return False


def test_models():
    """Test data models."""
    print("\n📊 Testing data models...")

    try:
        from rag_scraping.models import KnowledgeBaseItem, MainPageItem
        from datetime import datetime

        # Test KnowledgeBaseItem
        item = KnowledgeBaseItem(
            title="Test Item",
            url="https://example.com",
            date=datetime.now(),
            zones=["Zone1"],
            type_innovatie=["Type1"],
            main_content="Test content"
        )

        assert item.title == "Test Item"
        assert item.url == "https://example.com"
        assert item.zones == ["Zone1"]
        print("  ✅ KnowledgeBaseItem creation")

        # Test serialization
        data = item.to_dict()
        assert data["title"] == "Test Item"
        assert "associated_files" not in data
        print("  ✅ KnowledgeBaseItem serialization")

        # Test MainPageItem
        main_item = MainPageItem(
            title="Main Item",
            url="https://example.com",
            item_type="Publicatie"
        )

        assert main_item.title == "Main Item"
        assert main_item.item_type == "Publicatie"
        print("  ✅ MainPageItem creation")

        return True

    except Exception as e:
        print(f"  ❌ Models test failed: {e}")
        return False


def test_utils():
    """Test utility functions."""
    print("\n🛠️  Testing utility functions...")

    try:
        from rag_scraping.utils import clean_text_for_rag, format_date, create_chunk_id, split_text_into_chunks
        from datetime import datetime

                # Test text cleaning
        dirty_text = 'This has "quotes" and \n\n\nnewlines\t\tand   spaces'
        cleaned = clean_text_for_rag(dirty_text)

        # The cleaning should remove problematic characters but keep quotes
        assert '\n' not in cleaned
        assert '\t' not in cleaned
        assert '   ' not in cleaned  # Multiple spaces should be single
        print("  ✅ Text cleaning")

        # Test date formatting
        dt = datetime(2023, 1, 1, 12, 0, 0)
        formatted = format_date(dt)
        assert "2023-01-01" in formatted
        print("  ✅ Date formatting")

        # Test chunk ID creation
        chunk_id = create_chunk_id("Test Title (with parentheses)", 1)
        assert "Test_Title_with_parentheses" in chunk_id
        assert "chunk_01" in chunk_id
        print("  ✅ Chunk ID creation")

        # Test text chunking
        long_text = "This is a long text. " * 50
        chunks = split_text_into_chunks(long_text, max_chunk_size=200, min_chunk_size=50)
        assert len(chunks) > 1
        print("  ✅ Text chunking")

        return True

    except Exception as e:
        print(f"  ❌ Utils test failed: {e}")
        return False


def test_rag_chunking():
    """Test RAG chunking functionality."""
    print("\n📝 Testing RAG chunking...")

    try:
        from rag_scraping.rag_chunking import create_rag_chunks, create_chunk_dict
        from rag_scraping.models import KnowledgeBaseItem

        # Test chunk dictionary creation
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
        print("  ✅ Chunk dictionary creation")

        # Test RAG chunk creation
        items = [
            KnowledgeBaseItem(
                title="Item 1",
                url="https://example1.com",
                main_content="This is content for item 1. " * 30
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
        assert len(chunks) > 0
        assert chunks[0]["source_type"] == "page"
        print("  ✅ RAG chunk creation")

        return True

    except Exception as e:
        print(f"  ❌ RAG chunking test failed: {e}")
        return False


def test_cli():
    """Test CLI functionality."""
    print("\n💻 Testing CLI...")

    try:
        # Test help command
        result = subprocess.run(
            [sys.executable, "-m", "rag_scraping", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            assert "Versnellingsplan RAG Scraper" in result.stdout
            assert "--demo" in result.stdout
            assert "--production" in result.stdout
            print("  ✅ CLI help command")
        else:
            print(f"  ❌ CLI help command failed: {result.stderr}")
            return False

        return True

    except subprocess.TimeoutExpired:
        print("  ❌ CLI test timed out")
        return False
    except Exception as e:
        print(f"  ❌ CLI test failed: {e}")
        return False


def test_integration():
    """Test integration between components."""
    print("\n🔗 Testing integration...")

    try:
        from rag_scraping.config import load_config, get_output_paths
        from rag_scraping.models import KnowledgeBaseItem
        from rag_scraping.rag_chunking import create_rag_chunks

        # Test config to pipeline flow
        config = load_config("config.yaml")
        paths = get_output_paths(config, "demo")

        assert paths["run_type"] == "demo"
        assert paths["base_dir"].name == "demo"
        print("  ✅ Config to pipeline flow")

        # Test model to chunk flow
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
        print("  ✅ Model to chunk flow")

        return True

    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        return False


def main():
    """Run all smoke tests."""
    print("🧪 RAG Scraping Architecture Smoke Tests")
    print("=" * 50)

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Data Models", test_models),
        ("Utility Functions", test_utils),
        ("RAG Chunking", test_rag_chunking),
        ("CLI", test_cli),
        ("Integration", test_integration)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")

    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Architecture is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
