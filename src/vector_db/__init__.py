from .base import BaseVectorDB
from .azure import AzureVectorDB
from .embeddings import (
    embed_text,
    add_embeddings_to_documents,
    save_embeddings_to_file,
    load_embeddings_from_file,
    create_rag_ready_with_embeddings,
    get_embedding_dimensions,
    add_embeddings  # backward compatibility alias
)
from .upload import upload_documents_to_azure, upload_from_file
from .validation import validate_documents_from_file, validate_and_fix_documents, generate_validation_report
