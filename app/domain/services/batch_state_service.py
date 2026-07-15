from dataclasses import replace
from datetime import datetime

from app.domain.models.batch import Batch, BatchStatus
from app.domain.models.batch_document import (
    BatchDocument,
    BatchDocumentStatus,
)
from app.domain.models.batch_result import BatchResult


class BatchStateService:

    def mark_batch_as_processing(
        self,
        batch: Batch,
    ) -> Batch:
        return replace(
            batch,
            status=BatchStatus.PROCESSING,
            started_at=batch.started_at or datetime.now(),
        )

    def mark_document_as_processing(
        self,
        batch: Batch,
        document_id,
    ) -> Batch:
        updated_documents = [
            replace(
                document,
                status=BatchDocumentStatus.PROCESSING,
                error_message=None,
            )
            if document.document_id == document_id
            else document
            for document in batch.documents
        ]

        return self._rebuild_batch(
            batch=batch,
            documents=updated_documents,
        )

    def mark_document_as_completed(
        self,
        batch: Batch,
        document_id,
        analysis_id,
    ) -> Batch:
        updated_documents = [
            replace(
                document,
                status=BatchDocumentStatus.COMPLETED,
                analysis_id=analysis_id,
                error_message=None,
            )
            if document.document_id == document_id
            else document
            for document in batch.documents
        ]

        return self._rebuild_batch(
            batch=batch,
            documents=updated_documents,
        )

    def mark_document_as_failed(
        self,
        batch: Batch,
        document_id,
        error_message: str,
    ) -> Batch:
        updated_documents = [
            replace(
                document,
                status=BatchDocumentStatus.FAILED,
                analysis_id=None,
                error_message=error_message,
            )
            if document.document_id == document_id
            else document
            for document in batch.documents
        ]

        return self._rebuild_batch(
            batch=batch,
            documents=updated_documents,
        )

    def _rebuild_batch(
        self,
        batch: Batch,
        documents: list[BatchDocument],
    ) -> Batch:
        result = self._calculate_result(documents)
        status = self._calculate_batch_status(result)

        finished_at = batch.finished_at

        if status in {
            BatchStatus.COMPLETED,
            BatchStatus.COMPLETED_WITH_ERRORS,
            BatchStatus.FAILED,
        }:
            finished_at = finished_at or datetime.now()

        return replace(
            batch,
            documents=documents,
            result=result,
            status=status,
            started_at=batch.started_at or datetime.now(),
            finished_at=finished_at,
        )

    def _calculate_result(
        self,
        documents: list[BatchDocument],
    ) -> BatchResult:
        total_documents = len(documents)

        pending_documents = sum(
            document.status == BatchDocumentStatus.PENDING
            for document in documents
        )

        processing_documents = sum(
            document.status == BatchDocumentStatus.PROCESSING
            for document in documents
        )

        completed_documents = sum(
            document.status == BatchDocumentStatus.COMPLETED
            for document in documents
        )

        failed_documents = sum(
            document.status == BatchDocumentStatus.FAILED
            for document in documents
        )

        finished_documents = (
            completed_documents + failed_documents
        )

        progress_percentage = 0.0

        if total_documents > 0:
            progress_percentage = round(
                finished_documents
                / total_documents
                * 100,
                2,
            )

        return BatchResult(
            total_documents=total_documents,
            pending_documents=pending_documents,
            processing_documents=processing_documents,
            completed_documents=completed_documents,
            failed_documents=failed_documents,
            progress_percentage=progress_percentage,
        )

    def _calculate_batch_status(
        self,
        result: BatchResult,
    ) -> BatchStatus:
        if result.total_documents == 0:
            return BatchStatus.FAILED

        if result.processing_documents > 0:
            return BatchStatus.PROCESSING

        if result.pending_documents > 0:
            return BatchStatus.PROCESSING

        if (
            result.completed_documents
            == result.total_documents
        ):
            return BatchStatus.COMPLETED

        if (
            result.failed_documents
            == result.total_documents
        ):
            return BatchStatus.FAILED

        return BatchStatus.COMPLETED_WITH_ERRORS