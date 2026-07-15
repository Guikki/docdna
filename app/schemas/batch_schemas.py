from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BatchDocumentResponse(BaseModel):
    document_id: UUID
    original_filename: str
    status: str
    analysis_id: UUID | None
    error_message: str | None


class BatchResultResponse(BaseModel):
    total_documents: int
    pending_documents: int
    processing_documents: int
    completed_documents: int
    failed_documents: int
    progress_percentage: float


class BatchResponse(BaseModel):
    id: UUID
    created_at: datetime
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    documents: list[BatchDocumentResponse]
    result: BatchResultResponse