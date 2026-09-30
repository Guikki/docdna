from types import SimpleNamespace
from uuid import uuid4

from app.domain.services.batch_processor import BatchProcessor


class _FakeFactory:
    def create(self, filenames):
        return SimpleNamespace(
            documents=[
                SimpleNamespace(
                    document_id=uuid4(),
                    original_filename=filename,
                )
                for filename in filenames
            ]
        )


class _FakeBatchRepository:
    def save(self, batch) -> None:
        pass


class _FakeAnalysisRepository:
    def save(self, *, analysis_id, analysis_data) -> None:
        pass


class _FakeStateService:
    def mark_batch_as_processing(self, batch):
        return batch

    def mark_document_as_processing(self, *, batch, document_id):
        return batch

    def mark_document_as_completed(self, *, batch, document_id, analysis_id):
        return batch

    def mark_document_as_failed(self, *, batch, document_id, error_message):
        return batch


class _FakeUploadUseCase:
    def __init__(self) -> None:
        self._index = 0

    def execute(self, upload_file):
        self._index += 1
        return {
            "id": uuid4(),
            "performance": {
                "total_seconds": float(self._index),
                "stages": {
                    "ocr": {
                        "duration_seconds": 0.5 * self._index,
                        "calls": 1,
                    }
                },
            },
        }


def _processor_with_fakes(upload_use_case) -> BatchProcessor:
    processor = BatchProcessor()
    processor._factory = _FakeFactory()
    processor._batch_repository = _FakeBatchRepository()
    processor._analysis_repository = _FakeAnalysisRepository()
    processor._state_service = _FakeStateService()
    processor._upload_use_case = upload_use_case
    return processor


def test_should_build_batch_performance_report() -> None:
    processor = _processor_with_fakes(_FakeUploadUseCase())

    processor.process(
        [
            SimpleNamespace(filename="a.pdf"),
            SimpleNamespace(filename="b.pdf"),
        ]
    )

    report = processor.performance_report

    assert report is not None
    assert report["documents_total"] == 2
    assert report["completed_documents"] == 2
    assert report["failed_documents"] == 0
    assert report["document_analysis_seconds"] == 3.0
    assert report["stages"]["ocr"]["calls"] == 2
    assert report["stages"]["ocr"]["duration_seconds"] == 1.5
    assert report["fastest_document"] is not None
    assert report["slowest_document"] is not None


class _FailingUploadUseCase:
    def execute(self, upload_file):
        raise RuntimeError("falha controlada")


def test_should_measure_failed_document_without_breaking_report() -> None:
    processor = _processor_with_fakes(_FailingUploadUseCase())

    processor.process(
        [SimpleNamespace(filename="erro.pdf")]
    )

    report = processor.performance_report

    assert report is not None
    assert report["failed_documents"] == 1
    assert report["completed_documents"] == 0
    assert report["documents"][0]["error_message"] == "falha controlada"
