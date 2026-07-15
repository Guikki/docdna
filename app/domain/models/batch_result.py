from dataclasses import dataclass


@dataclass(frozen=True)
class BatchResult:
    total_documents: int
    pending_documents: int
    processing_documents: int
    completed_documents: int
    failed_documents: int
    progress_percentage: float