from datetime import datetime

from pydantic import BaseModel


class KnowledgeVersionResponse(BaseModel):
    id: str
    version: int
    status: str
    chunk_count: int
    embedding_dimensions: int
    error_message: str | None
    created_at: datetime


class KnowledgeDocumentResponse(BaseModel):
    document_id: str
    title: str
    original_file_name: str
    content_type: str
    source: str
    active: bool
    status: str
    active_version: int
    chunk_count: int
    embedding_dimensions: int
    updated_at: datetime


class KnowledgeDocumentDetailResponse(KnowledgeDocumentResponse):
    versions: list[KnowledgeVersionResponse]


class KnowledgeIngestionResponse(BaseModel):
    ingestion_id: str
    document_id: str
    status: str
    chunk_size: int
    chunk_overlap: int
    embedding_dimensions: int
    chunk_count: int


class KnowledgeStatusUpdate(BaseModel):
    active: bool
