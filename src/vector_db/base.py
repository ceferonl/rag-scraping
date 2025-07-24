from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional

class BaseVectorDB(ABC):
    # Canonical set of allowed/documented fields for RAG documents
    RAG_FIELDS = [
        "id",
        "title",
        "content",
        "source_type",
        "sourcepage",
        "sourcefile",
        "page_number",
        "date",
        "zones",
        "type_innovatie",
        "pdfs",
        "videos",
        "pictures",
        "image_urls",
        "image_paths",
        "images",
        "chunk_number",
        "content_length",
        "main_content",
        "url",
        "item_type",
        "other_files",
        "elements",
        "extracted_text",
        "page_texts",
        "source_item_url",
        "total_elements",
        "total_images",
        "total_pages",
        "extraction_metadata"
    ]

    def __init__(self, endpoint: Optional[str] = None, index_name: Optional[str] = None, api_key: Optional[str] = None):
        """
        Base class for vector database integrations.
        Args:
            endpoint: The endpoint URL for the vector DB service.
            index_name: The name of the index/collection.
            api_key: The API key or secret (if needed).
        """
        self.endpoint = endpoint
        self.index_name = index_name
        self.api_key = api_key

    @abstractmethod
    def create_index(self, fields: List[Dict[str, Any]], **kwargs) -> None:
        """Create a new index or collection in the vector database."""
        pass

    @abstractmethod
    def upload_documents(self, documents: List[Dict[str, Any]], batch_size: int = 1000, **kwargs) -> None:
        """Upload a batch of documents to the vector database."""
        pass

    @abstractmethod
    def search(self, query: str, **kwargs) -> Any:
        """Search for documents in the vector database."""
        pass
