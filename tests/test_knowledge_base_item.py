"""
Tests for the KnowledgeBaseItem class.
"""

from datetime import datetime

from rag_scraping.versnellingsplan import KnowledgeBaseItem


def test_knowledge_base_item_initialization():
    """Test that a KnowledgeBaseItem can be initialized with required fields."""
    item = KnowledgeBaseItem(
        title="Test Item",
        url="https://example.com/test"
    )

    assert item.title == "Test Item"
    assert item.url == "https://example.com/test"
    assert item.date is None
    assert item.item_type is None
    assert item.main_content is None
    assert item.associated_files == []
    assert item.zones == []
    assert item.type_innovatie == []


def test_knowledge_base_item_with_all_fields():
    """Test that a KnowledgeBaseItem can be initialized with all fields."""
    test_date = datetime(2023, 1, 1)
    item = KnowledgeBaseItem(
        title="Test Item",
        url="https://example.com/test",
        date=test_date,
        item_type="Publication",
        main_content="Test content",
        associated_files=["file1.pdf", "file2.pdf"],
        zones=["Zone 1", "Zone 2"],
        type_innovatie=["Type 1", "Type 2"]
    )

    assert item.title == "Test Item"
    assert item.url == "https://example.com/test"
    assert item.date == test_date
    assert item.item_type == "Publication"
    assert item.main_content == "Test content"
    assert item.associated_files == ["file1.pdf", "file2.pdf"]
    assert item.zones == ["Zone 1", "Zone 2"]
    assert item.type_innovatie == ["Type 1", "Type 2"]


def test_knowledge_base_item_to_dict():
    """Test that to_dict method correctly serializes the item."""
    test_date = datetime(2023, 1, 1)
    item = KnowledgeBaseItem(
        title="Test Item",
        url="https://example.com/test",
        date=test_date,
        item_type="Publication",
        main_content="Test content",
        associated_files=["file1.pdf"],
        zones=["Zone 1"],
        type_innovatie=["Type 1"]
    )

    data = item.to_dict()
    assert data["title"] == "Test Item"
    assert data["url"] == "https://example.com/test"
    assert data["date"] == test_date.isoformat()
    assert data["item_type"] == "Publication"
    assert data["main_content"] == "Test content"
    assert data["associated_files"] == ["file1.pdf"]
    assert data["zones"] == ["Zone 1"]
    assert data["type_innovatie"] == ["Type 1"]
