from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchFieldDataType, SearchableField
)
from azure.search.documents import SearchClient
from .base import BaseVectorDB
from typing import Any, List, Dict, Optional

FIELD_TYPE_MAP = {
    "id": ("string", True, True, False),  # (type, key, filterable, collection)
    "title": ("string", False, False, False),
    "content": ("string", False, False, False),
    "source_type": ("string", False, True, False),
    "sourcepage": ("string", False, False, False),
    "sourcefile": ("string", False, False, False),
    "page_number": ("int", False, True, False),
    "date": ("date", False, True, False),
    "zones": ("string", False, True, True),
    "type_innovatie": ("string", False, True, True),
    "pdfs": ("string", False, False, True),
    "videos": ("string", False, False, True),
    "pictures": ("string", False, False, True),
    "image_urls": ("string", False, False, True),
    "image_paths": ("string", False, False, True),
    "images": ("string", False, False, True),
    "chunk_number": ("int", False, False, False),
    "content_length": ("int", False, False, False),
    "main_content": ("string", False, False, False),
    "url": ("string", False, False, False),
    "item_type": ("string", False, False, False),
    "other_files": ("string", False, False, True),
    "elements": ("string", False, False, True),
    "extracted_text": ("string", False, False, False),
    "page_texts": ("string", False, False, False),
    "source_item_url": ("string", False, False, False),
    "total_elements": ("int", False, False, False),
    "total_images": ("int", False, False, False),
    "total_pages": ("int", False, False, False),
    "extraction_metadata": ("string", False, False, False),
}

class AzureVectorDB(BaseVectorDB):
    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None, index_name: Optional[str] = None):
        super().__init__(endpoint=endpoint, index_name=index_name, api_key=api_key)
        if self.endpoint and self.api_key and self.index_name:
            self.credential = AzureKeyCredential(self.api_key)
            self.index_client = SearchIndexClient(endpoint=self.endpoint, credential=self.credential)
            self.search_client = SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential)
        else:
            self.credential = None
            self.index_client = None
            self.search_client = None

    def get_default_fields(self) -> list:
        fields = []
        for name in self.RAG_FIELDS:
            t, key, filterable, collection = FIELD_TYPE_MAP.get(name, ("string", False, False, False))
            if t == "string":
                if collection:
                    f = SimpleField(name=name, type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=filterable)
                else:
                    # Make title/content searchable, others simple
                    if name in ("title", "content"):
                        f = SearchableField(name=name, type=SearchFieldDataType.String, sortable=(name=="title"))
                    else:
                        f = SimpleField(name=name, type=SearchFieldDataType.String, key=key, filterable=filterable)
            elif t == "int":
                if collection:
                    f = SimpleField(name=name, type=SearchFieldDataType.Collection(SearchFieldDataType.Int32), filterable=filterable)
                else:
                    f = SimpleField(name=name, type=SearchFieldDataType.Int32, filterable=filterable)
            elif t == "date":
                f = SimpleField(name=name, type=SearchFieldDataType.DateTimeOffset, filterable=filterable, sortable=True)
            else:
                # fallback
                f = SimpleField(name=name, type=SearchFieldDataType.String, key=key, filterable=filterable)
            fields.append(f)
        return fields

    def create_index(self, fields: Optional[List[Any]] = None, **kwargs) -> None:
        """Create a new index in Azure Cognitive Search. Uses default fields if none provided."""
        if not self.index_client:
            raise ValueError("AzureVectorDB is not properly initialized with endpoint, api_key, and index_name.")
        if fields is None:
            fields = self.get_default_fields()
        index = SearchIndex(name=self.index_name, fields=fields)
        # Delete existing index if it exists
        if self.index_name in [i.name for i in self.index_client.list_indexes()]:
            self.index_client.delete_index(self.index_name)
        self.index_client.create_index(index)

    def upload_documents(self, documents: List[Dict[str, Any]], batch_size: int = 1000, **kwargs) -> None:
        """Upload documents to the Azure index in batches."""
        if not self.search_client:
            raise ValueError("AzureVectorDB is not properly initialized with endpoint, api_key, and index_name.")
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            result = self.search_client.upload_documents(documents=batch)
            print(f"Uploaded {len(result)} documents")

    def search(self, query: str, **kwargs) -> Any:
        """Search the Azure index. Not implemented yet."""
        raise NotImplementedError("Search is not implemented yet.")
