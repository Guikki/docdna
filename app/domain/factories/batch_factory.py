from datetime import datetime
from uuid import uuid4

from app.domain.models.batch import Batch, BatchStatus
from app.domain.models.batch_document import (
    BatchDocument,
    BatchDocumentStatus,
)
from app.domain.models.batch_result import BatchResult


class BatchFactory:

    def create(
        self,
        filenames: list[str],
    ) -> Batch:
        documents = [
            BatchDocument(
                document_id=uuid4(),
                original_filename=filename,
                status=BatchDocumentStatus.PENDING,
            )
            for filename in filenames
        ]

        result = BatchResult(
            total_documents=len(documents),
            pending_documents=len(documents),
            processing_documents=0,
            completed_documents=0,
            failed_documents=0,
            progress_percentage=0.0,
        )

        return Batch(
            id=uuid4(),
            created_at=datetime.now(),
            status=BatchStatus.PENDING,
            documents=documents,
            result=result,
        )