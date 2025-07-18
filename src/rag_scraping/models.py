"""
Data models for RAG Scraping.

This module contains the data models used throughout the scraping pipeline.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, field_validator, model_validator


@dataclass
class KnowledgeBaseItem:
    """Represents a single item in the knowledge base."""
    title: str
    url: str
    date: Optional[datetime] = None
    item_type: Optional[str] = None
    main_content: Optional[str] = None
    associated_files: List[str] = None
    zones: List[str] = None
    type_innovatie: List[str] = None
    pdfs: List[str] = None
    videos: List[str] = None
    pictures: List[str] = None

    def __post_init__(self):
        if self.associated_files is None:
            self.associated_files = []
        if self.zones is None:
            self.zones = []
        if self.type_innovatie is None:
            self.type_innovatie = []
        if self.pdfs is None:
            self.pdfs = []
        if self.videos is None:
            self.videos = []
        if self.pictures is None:
            self.pictures = []

    def to_dict(self):
        """Convert the item to a dictionary for JSON serialization."""
        data = asdict(self)
        if self.date:
            data['date'] = self.date.isoformat()
        # Remove associated_files from output since it's split into specific categories
        data.pop('associated_files', None)
        return data


class MainPageItem(BaseModel):
    """Represents a main page item with basic information."""
    title: str
    url: str
    item_type: str


class KnowledgeBaseItemValidation(BaseModel):
    """Pydantic model for validating knowledge base items."""
    title: str
    url: str
    main_content: str
    pdfs: list
    videos: list
    pictures: list

    @field_validator('main_content')
    @classmethod
    def main_content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('main_content must not be empty')
        return v

    @model_validator(mode="after")
    def no_overlap_in_files(self):
        pdfs = set(self.pdfs)
        videos = set(self.videos)
        pictures = set(self.pictures)
        overlap = (pdfs | videos) & pictures
        if overlap:
            raise ValueError(f'pictures overlaps with pdfs/videos: {overlap}')
        return self
