# azure.py  (trimmed to match your JSON)
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchFieldDataType, SearchableField, SearchField,
    VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile,
    LexicalAnalyzerName
)
from azure.search.documents import SearchClient
from typing import Any, List, Dict, Optional
from .base import BaseVectorDB

# Only the fields that exist in your JSON
# files are
FIELD_TYPE_MAP = {
    #                 ("type",   key,   filterable, collection)
    "id":             ("string", True,  True,  False),
    "title":          ("string", False, False, False),  # will be SearchableField
    "content":        ("string", False, False, False),  # will be SearchableField
    "source_type":    ("string", False, True,  False),
    "sourcepage":     ("string", False, False, False),
    "sourcefile":     ("string", False, False, False),
    "page_number":    ("int",    False, True,  False),
    "date":           ("date",   False, True,  False),
    "zones":          ("string", False, True,  True),
    "type_innovatie": ("string", False, True,  True),
    "pdfs":           ("string", False, False, True),
    "videos":         ("string", False, False, True),
    "pictures":       ("string", False, False, True),
    "image_paths":    ("string", False, False, True),
    "chunk_number":   ("int",    False, False, False),
    "content_length": ("int",    False, False, False)
}

DEFAULT_VECTOR_DIM = 1536  # change to 3072 if you use text-embedding-3-large, etc.

class AzureVectorDB(BaseVectorDB):
    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None, index_name: Optional[str] = None,
                 vector_dim: int = DEFAULT_VECTOR_DIM, analyzer=LexicalAnalyzerName.NL_MICROSOFT):
        super().__init__(endpoint=endpoint, index_name=index_name, api_key=api_key)
        self.vector_dim = vector_dim
        self.analyzer = analyzer
        if self.endpoint and self.api_key and self.index_name:
            self.credential = AzureKeyCredential(self.api_key)
            self.index_client = SearchIndexClient(endpoint=self.endpoint, credential=self.credential)
            self.search_client = SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential)
        else:
            self.credential = None
            self.index_client = None
            self.search_client = None

    def get_default_fields(self) -> List[Any]:
        """Get default fields for the Azure search index."""
        fields = []

        # Searchable text fields
        for name in ["title", "content"]:
            fields.append(SearchableField(name=name, type=SearchFieldDataType.String))

        # Other fields from RAG_FIELDS based on their types
        for name, (t, key, filterable, collection) in FIELD_TYPE_MAP.items():
            if name in ["title", "content"]:  # Already added as SearchableField
                continue
            if t == "string":
                if collection:
                    f = SimpleField(name=name, type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                                    filterable=filterable)
                else:
                    f = SimpleField(name=name, type=SearchFieldDataType.String,
                                    key=key, filterable=filterable)
            elif t == "int":
                if collection:
                    f = SimpleField(name=name, type=SearchFieldDataType.Collection(SearchFieldDataType.Int32),
                                    filterable=filterable)
                else:
                    f = SimpleField(name=name, type=SearchFieldDataType.Int32,
                                    filterable=True if filterable else False, sortable=True)
            elif t == "date":
                f = SimpleField(name=name, type=SearchFieldDataType.DateTimeOffset,
                                filterable=True, sortable=True, facetable=True)
            else:
                f = SimpleField(name=name, type=SearchFieldDataType.String, key=key, filterable=filterable)
            fields.append(f)

        # Vector field: name this in the extension's "vectors" header
        fields.append(SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=self.vector_dim,
            vector_search_profile_name="vprofile"
        ))
        return fields

    def create_index(self, fields: Optional[List[Any]] = None, **kwargs) -> None:
        """Create a new index in Azure Cognitive Search. Uses default fields if none provided."""
        if not self.index_client:
            raise ValueError("AzureVectorDB is not properly initialized with endpoint, api_key, and index_name.")

        if fields is None:
            fields = self.get_default_fields()

        # Vector search configuration (HNSW + profile)
        vs = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
            profiles=[VectorSearchProfile(name="vprofile", algorithm_configuration_name="hnsw")]
        )

        index = SearchIndex(name=self.index_name, fields=fields, vector_search=vs)

        # Replace existing index
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
        raise NotImplementedError("Search is not implemented yet.")
