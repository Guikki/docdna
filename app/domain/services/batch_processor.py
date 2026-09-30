from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import UploadFile

from app.domain.factories.batch_factory import BatchFactory
from app.domain.models.batch import Batch
from app.domain.services.batch_state_service import BatchStateService
from app.domain.use_cases.upload_document_use_case import UploadDocumentUseCase
from app.infrastructure.repositories.analysis_memory_repository import AnalysisMemoryRepository
from app.infrastructure.repositories.batch_memory_repository import BatchMemoryRepository
from app.observability.performance_timer import PerformanceTimer


class BatchProcessor:

    def __init__(self) -> None:
        self._factory = BatchFactory()
        self._batch_repository = BatchMemoryRepository()
        self._analysis_repository = AnalysisMemoryRepository()
        self._state_service = BatchStateService()
        self._upload_use_case = UploadDocumentUseCase()
        self._performance_report: dict[str, Any] | None = None

    @property
    def performance_report(self) -> dict[str, Any] | None:
        return self._performance_report

    def process(self, files: list[UploadFile]) -> Batch:
        timer = PerformanceTimer()
        self._performance_report = None

        filenames = [
            file.filename or f"documento_{index + 1}.pdf"
            for index, file in enumerate(files)
        ]

        with timer.measure("batch_factory"):
            batch = self._factory.create(filenames)

        with timer.measure("batch_repository_save"):
            self._batch_repository.save(batch)

        with timer.measure("batch_state_update"):
            batch = self._state_service.mark_batch_as_processing(batch)

        with timer.measure("batch_repository_save"):
            self._batch_repository.save(batch)

        document_reports: list[dict[str, Any]] = []

        for batch_document, upload_file in zip(batch.documents, files):
            with timer.measure("batch_state_update"):
                batch = self._state_service.mark_document_as_processing(
                    batch=batch,
                    document_id=batch_document.document_id,
                )

            with timer.measure("batch_repository_save"):
                self._batch_repository.save(batch)

            started_at = perf_counter()
            analysis: dict[str, Any] | None = None

            try:
                analysis = self._upload_use_case.execute(upload_file)
                wall_seconds = max(perf_counter() - started_at, 0.0)
                analysis_id = analysis["id"]

                with timer.measure("analysis_repository_save"):
                    self._analysis_repository.save(
                        analysis_id=analysis_id,
                        analysis_data=analysis,
                    )

                with timer.measure("batch_state_update"):
                    batch = self._state_service.mark_document_as_completed(
                        batch=batch,
                        document_id=batch_document.document_id,
                        analysis_id=analysis_id,
                    )

                document_reports.append(
                    self._build_document_report(
                        filename=(
                            upload_file.filename
                            or batch_document.original_filename
                        ),
                        analysis=analysis,
                        wall_seconds=wall_seconds,
                        succeeded=True,
                        error_message=None,
                    )
                )

            except Exception as error:
                wall_seconds = max(perf_counter() - started_at, 0.0)
                error_message = self._build_error_message(error)

                with timer.measure("batch_state_update"):
                    batch = self._state_service.mark_document_as_failed(
                        batch=batch,
                        document_id=batch_document.document_id,
                        error_message=error_message,
                    )

                document_reports.append(
                    self._build_document_report(
                        filename=(
                            upload_file.filename
                            or batch_document.original_filename
                        ),
                        analysis=analysis,
                        wall_seconds=wall_seconds,
                        succeeded=False,
                        error_message=error_message,
                    )
                )

            with timer.measure("batch_repository_save"):
                self._batch_repository.save(batch)

        self._performance_report = self._build_performance_report(
            timer=timer,
            document_reports=document_reports,
        )

        return batch

    def _build_document_report(
        self,
        *,
        filename: str,
        analysis: dict[str, Any] | None,
        wall_seconds: float,
        succeeded: bool,
        error_message: str | None,
    ) -> dict[str, Any]:
        performance = analysis.get("performance", {}) if analysis else {}
        analysis_id = analysis.get("id") if analysis else None

        return {
            "filename": filename,
            "analysis_id": str(analysis_id) if analysis_id is not None else None,
            "succeeded": succeeded,
            "wall_seconds": round(max(wall_seconds, 0.0), 6),
            "analysis_total_seconds": round(
                float(performance.get("total_seconds", 0.0) or 0.0),
                6,
            ),
            "stages": performance.get("stages", {}),
            "error_message": error_message,
        }

    def _build_performance_report(
        self,
        *,
        timer: PerformanceTimer,
        document_reports: list[dict[str, Any]],
    ) -> dict[str, Any]:
        timer_report = timer.to_dict()
        completed = [item for item in document_reports if item["succeeded"]]
        failed = [item for item in document_reports if not item["succeeded"]]

        wall_total = sum(float(item["wall_seconds"]) for item in document_reports)
        analysis_total = sum(
            float(item["analysis_total_seconds"])
            for item in completed
        )

        fastest = (
            min(document_reports, key=lambda item: float(item["wall_seconds"]))
            if document_reports else None
        )
        slowest = (
            max(document_reports, key=lambda item: float(item["wall_seconds"]))
            if document_reports else None
        )

        return {
            "total_seconds": timer_report.get("total_seconds", 0.0),
            "documents_total": len(document_reports),
            "completed_documents": len(completed),
            "failed_documents": len(failed),
            "document_wall_seconds": round(wall_total, 6),
            "document_analysis_seconds": round(analysis_total, 6),
            "average_document_wall_seconds": round(
                wall_total / len(document_reports) if document_reports else 0.0,
                6,
            ),
            "fastest_document": self._document_summary(fastest),
            "slowest_document": self._document_summary(slowest),
            "documents": document_reports,
            "stages": self._aggregate_document_stages(completed),
            "orchestration": timer_report.get("stages", {}),
        }

    def _aggregate_document_stages(
        self,
        document_reports: list[dict[str, Any]],
    ) -> dict[str, Any]:
        aggregated: dict[str, dict[str, float | int]] = {}
        analysis_total = sum(
            float(item["analysis_total_seconds"])
            for item in document_reports
        )

        for report in document_reports:
            for stage_name, stage_data in report.get("stages", {}).items():
                if not isinstance(stage_data, dict):
                    continue

                stage = aggregated.setdefault(
                    stage_name,
                    {"duration_seconds": 0.0, "calls": 0},
                )
                stage["duration_seconds"] = (
                    float(stage["duration_seconds"])
                    + float(stage_data.get("duration_seconds", 0.0) or 0.0)
                )
                stage["calls"] = (
                    int(stage["calls"])
                    + int(stage_data.get("calls", 0) or 0)
                )

        result: dict[str, Any] = {}

        for stage_name, stage in aggregated.items():
            duration = float(stage["duration_seconds"])
            calls = int(stage["calls"])

            result[stage_name] = {
                "duration_seconds": round(duration, 6),
                "calls": calls,
                "average_seconds": round(duration / calls if calls else 0.0, 6),
                "percentage_of_document_analysis": round(
                    duration / analysis_total * 100.0 if analysis_total else 0.0,
                    2,
                ),
            }

        return result

    @staticmethod
    def _document_summary(
        report: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if report is None:
            return None

        return {
            "filename": report.get("filename"),
            "wall_seconds": report.get("wall_seconds"),
            "succeeded": report.get("succeeded"),
        }

    def _build_error_message(self, error: Exception) -> str:
        message = str(error).strip()

        if message:
            return message

        return (
            "O documento não pôde ser processado por um erro "
            "não identificado."
        )
