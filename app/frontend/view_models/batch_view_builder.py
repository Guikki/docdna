from datetime import datetime
from typing import Any

from app.domain.models.batch import Batch


class BatchViewBuilder:

    def build(self, batch: Batch) -> dict[str, Any]:
        return {
            "id": str(batch.id),
            "status": batch.status.value,
            "status_label": self._translate_batch_status(
                batch.status.value
            ),
            "created_at": self._format_datetime(
                batch.created_at
            ),
            "started_at": self._format_optional_datetime(
                batch.started_at
            ),
            "finished_at": self._format_optional_datetime(
                batch.finished_at
            ),
            "documents": [
                {
                    "document_id": str(document.document_id),
                    "original_filename": (
                        document.original_filename
                    ),
                    "status": document.status.value,
                    "status_label":
                        self._translate_document_status(
                            document.status.value
                        ),
                    "analysis_id": (
                        str(document.analysis_id)
                        if document.analysis_id
                        else None
                    ),
                    "analysis_url": (
                        f"/analyses/{document.analysis_id}"
                        if document.analysis_id
                        else None
                    ),
                    "error_message": document.error_message,
                }
                for document in batch.documents
            ],
            "result": {
                "total_documents": (
                    batch.result.total_documents
                ),
                "pending_documents": (
                    batch.result.pending_documents
                ),
                "processing_documents": (
                    batch.result.processing_documents
                ),
                "completed_documents": (
                    batch.result.completed_documents
                ),
                "failed_documents": (
                    batch.result.failed_documents
                ),
                "progress_percentage": (
                    batch.result.progress_percentage
                ),
                "progress_label": (
                    f"{batch.result.progress_percentage:.0f}%"
                ),
            },
        }

    def _format_datetime(
        self,
        value: datetime,
    ) -> str:
        return value.strftime("%d/%m/%Y às %H:%M:%S")

    def _format_optional_datetime(
        self,
        value: datetime | None,
    ) -> str:
        if value is None:
            return "Não informada"

        return self._format_datetime(value)

    def _translate_batch_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "pending": "Aguardando processamento",
            "processing": "Em processamento",
            "completed": "Concluído",
            "completed_with_errors": (
                "Concluído com ocorrências"
            ),
            "failed": "Falhou",
        }

        return labels.get(status, status)

    def _translate_document_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "pending": "Aguardando",
            "processing": "Processando",
            "completed": "Concluído",
            "failed": "Falhou",
        }

        return labels.get(status, status)