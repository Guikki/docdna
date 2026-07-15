from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class BatchDocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class BatchDocument:
    document_id: UUID
    original_filename: str
    status: BatchDocumentStatus
    analysis_id: UUID | None = None
    error_message: str | None = None