"""
Legacy upload script - now a thin wrapper around src/vector_db/upload.py

This script remains for compatibility but now uses the centralized upload functionality.
"""

import sys
from pathlib import Path

# Add src to path to import the main upload functionality
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'src'))
from vector_db.upload import upload_from_file

def main():
    """Upload documents using the centralized upload functionality."""
    # File to upload - update this path as needed
    json_path = Path(__file__).resolve().parent.parent.parent / 'output' / 'demo' / 'rag_ready_complete_20250718_212226.json'

    # Use the centralized upload function
    try:
        upload_from_file(str(json_path))
        print("Upload completed successfully!")
    except Exception as e:
        print(f"Upload failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
