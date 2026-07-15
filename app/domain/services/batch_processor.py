from fastapi import UploadFile

from app.domain.factories.batch_factory import BatchFactory
from app.domain.models.batch import Batch
from app.domain.services.batch_state_service import BatchStateService
from app.domain.use_cases.upload_document_use_case import (
    UploadDocumentUseCase,
)
from app.infrastructure.repositories.analysis_memory_repository import (
    AnalysisMemoryRepository,
)
from app.infrastructure.repositories.batch_memory_repository import (
    BatchMemoryRepository,
)


class BatchProcessor:

    def __init__(self) -> None:
        self._factory = BatchFactory()
        self._batch_repository = BatchMemoryRepository()
        self._analysis_repository = AnalysisMemoryRepository()
        self._state_service = BatchStateService()
        self._upload_use_case = UploadDocumentUseCase()

    def process(
        self,
        files: list[UploadFile],
    ) -> Batch:
        filenames = [
            file.filename or f"documento_{index + 1}.pdf"
            for index, file in enumerate(files)
        ]

        batch = self._factory.create(filenames)

        self._batch_repository.save(batch)

        batch = self._state_service.mark_batch_as_processing(
            batch
        )

        self._batch_repository.save(batch)

        for batch_document, upload_file in zip(
            batch.documents,
            files,
        ):
            batch = self._state_service.mark_document_as_processing(
                batch=batch,
                document_id=batch_document.document_id,
            )

            self._batch_repository.save(batch)

            try:
                analysis = self._upload_use_case.execute(
                    upload_file
                )

                analysis_id = analysis["id"]

                self._analysis_repository.save(
                    analysis_id=analysis_id,
                    analysis_data=analysis,
                )

                batch = self._state_service.mark_document_as_completed(
                    batch=batch,
                    document_id=batch_document.document_id,
                    analysis_id=analysis_id,
                )

            except Exception as error:
                batch = self._state_service.mark_document_as_failed(
                    batch=batch,
                    document_id=batch_document.document_id,
                    error_message=self._build_error_message(error),
                )

            self._batch_repository.save(batch)

        return batch

    def _build_error_message(
        self,
        error: Exception,
    ) -> str:
        message = str(error).strip()

        if message:
            return message

        return (
            "O documento não pôde ser processado por um erro "
            "não identificado."
        )