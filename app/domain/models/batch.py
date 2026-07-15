from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from app.domain.models.batch_document import BatchDocument
from app.domain.models.batch_result import BatchResult


class BatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


@dataclass(frozen=True)
class Batch:
    id: UUID
    created_at: datetime
    status: BatchStatus
    documents: list[BatchDocument]
    result: BatchResult
    started_at: datetime | None = None
    finished_at: datetime | None = None