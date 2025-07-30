import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import re
import unicodedata
from openai import OpenAI
from openai import AzureOpenAI

# Load environment variables from .env
load_dotenv()

# Import config loader and AzureVectorDB
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'src'))
from rag_scraping.config import load_config
from vector_db.azure import AzureVectorDB

def normalize_id(s):
    # Unicode normalize (NFKD), remove accents
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    # Replace forbidden chars with _
    s = re.sub(r'[^a-zA-Z0-9_\-=]', '_', s)
    # Collapse multiple underscores
    s = re.sub(r'_+', '_', s)
    # Strip leading/trailing underscores
    s = s.strip('_')
    return s

def fix_ids(docs):
    forbidden = re.compile(r"[^a-zA-Z0-9_\-=]")
    fixed = 0
    for doc in docs:
        idval = doc.get('id', '')
        if forbidden.search(idval):
            print(f"[FIX] Normalizing id: {idval}")
            new_id = normalize_id(idval)
            doc['id'] = new_id
            fixed += 1
    print(f"Fixed {fixed} IDs to be Azure-compliant.")

def fix_dates(docs):
    fixed = 0
    for doc in docs:
        date = doc.get('date')
        if isinstance(date, str) and date:
            # If it doesn't end with 'Z' or a timezone offset
            if not (date.endswith('Z') or '+' in date or '-' in date[10:]):
                doc['date'] = date + 'Z'
                fixed += 1
    return fixed

def check_ids(docs):
    forbidden = re.compile(r"[^a-zA-Z0-9_\-=]")
    bad = 0
    for doc in docs:
        idval = doc.get('id', '')
        if forbidden.search(idval):
            print(f"[WARN] Forbidden chars in id: {idval}")
            bad += 1
    print(f"Checked {len(docs)} IDs, found {bad} with forbidden characters.")

def to_azure_doc(d, embed_fn, config):
    return {
        **d,
        "contentVector": embed_fn(d.get("content", "") or "", config)
    }

def embed_text(text: str, config: dict) -> list[float]:
    """Generate embeddings using Azure OpenAI"""
    AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
    AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]

    # Get model and API version from config
    embeddings_cfg = config.get('embeddings', {})
    AZURE_OPENAI_API_VERSION = embeddings_cfg.get('api_version', '2024-08-01-preview')
    EMBED_MODEL = embeddings_cfg.get('model', 'text-embedding-3-small')

    client = AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
    )

    text = (text or "")
    response = client.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding

def main():
    # Config
    config = load_config(str(Path(__file__).resolve().parent.parent.parent / 'config.yaml'))
    vector_db_cfg = config.get('vector_db', {})
    endpoint = os.environ.get('AZURE_SEARCH_ENDPOINT')
    index_name = vector_db_cfg.get('index_name')
    api_key = os.environ.get('AZURE_SEARCH_API_KEY')
    if not (endpoint and index_name and api_key):
        print(f"Missing Azure config: endpoint={endpoint}, index_name={index_name}, api_key={'set' if api_key else 'MISSING'}")
        sys.exit(1)

    # File to upload
    json_path = Path(__file__).resolve().parent.parent.parent / 'output' / 'demo' / 'rag_ready_complete_20250718_212226.json'
    if not json_path.exists():
        print(f"File not found: {json_path}")
        sys.exit(1)

    # Load data
    with open(json_path, 'r', encoding='utf-8') as f:
        docs = json.load(f)
    print(f"Loaded {len(docs)} documents from {json_path}")

    # Fix date fields
    n_fixed = fix_dates(docs)
    print(f"Fixed {n_fixed} date fields to add 'Z' for Azure compatibility.")

    # Fix IDs for Azure compliance
    fix_ids(docs)

    # Check IDs for forbidden chars
    check_ids(docs)

    # Init AzureVectorDB
    db = AzureVectorDB(endpoint=endpoint, api_key=api_key, index_name=index_name)

    # Create index (safe to call, will replace if exists)
    print(f"Creating index '{index_name}' on Azure...")
    db.create_index()
    print("Index ready.")

    # Embed documents
    print(f"Embedding {len(docs)} documents...")
    docs = [to_azure_doc(d, embed_text, config) for d in docs]
    print("Embedding complete.")

    # Upload documents in batches
    print(f"Uploading {len(docs)} documents in batches...")
    db.upload_documents(docs)
    print("Upload complete.")

if __name__ == "__main__":
    main()
