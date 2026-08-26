from datetime import datetime
from typing import Any

from app.domain.models.batch import Batch
from app.domain.models.batch_finding_summary import (
    BatchFindingSummary,
)
from app.frontend.investigations.models.investigation_status import (
    InvestigationStatus,
)
from app.frontend.investigations.services.investigation_status_resolver import (
    InvestigationStatusResolver,
)


class BatchViewBuilder:

    def __init__(self) -> None:
        self._status_resolver = (
            InvestigationStatusResolver()
        )

    def build(
        self,
        batch: Batch,
        finding_summaries: list[
            BatchFindingSummary
        ] | None = None,
        document_analytical_statuses: dict[
            str,
            InvestigationStatus,
        ] | None = None,
    ) -> dict[str, Any]:
        normalized_finding_summaries = (
            finding_summaries or []
        )

        normalized_document_statuses = (
            document_analytical_statuses
            or {}
        )

        documents = self._build_documents(
            batch=batch,
            document_analytical_statuses=(
                normalized_document_statuses
            ),
        )

        analytical_summary = (
            self._build_analytical_summary(
                documents
            )
        )

        return {
            "id": str(batch.id),

            "status": (
                batch.status.value
            ),

            "status_label": (
                self._translate_batch_status(
                    batch.status.value
                )
            ),

            "analytical_status": (
                analytical_summary[
                    "status"
                ]
            ),

            "analytical_status_label": (
                analytical_summary[
                    "status_label"
                ]
            ),

            "analytical_summary": (
                analytical_summary
            ),

            "created_at": (
                self._format_datetime(
                    batch.created_at
                )
            ),

            "started_at": (
                self._format_optional_datetime(
                    batch.started_at
                )
            ),

            "finished_at": (
                self._format_optional_datetime(
                    batch.finished_at
                )
            ),

            "documents": documents,

            "result": {
                "total_documents": (
                    batch.result
                    .total_documents
                ),

                "pending_documents": (
                    batch.result
                    .pending_documents
                ),

                "processing_documents": (
                    batch.result
                    .processing_documents
                ),

                "completed_documents": (
                    batch.result
                    .completed_documents
                ),

                "failed_documents": (
                    batch.result
                    .failed_documents
                ),

                "progress_percentage": (
                    batch.result
                    .progress_percentage
                ),

                "progress_label": (
                    f"{batch.result.progress_percentage:.0f}%"
                ),
            },

            "individual_findings": (
                self._build_finding_summaries(
                    normalized_finding_summaries
                )
            ),

            "individual_finding_type_count": (
                len(
                    normalized_finding_summaries
                )
            ),

            "has_individual_findings": (
                bool(
                    normalized_finding_summaries
                )
            ),
        }

    def _build_documents(
        self,
        *,
        batch: Batch,
        document_analytical_statuses: dict[
            str,
            InvestigationStatus,
        ],
    ) -> list[dict[str, Any]]:
        documents: list[
            dict[str, Any]
        ] = []

        for document in batch.documents:
            analysis_id = (
                str(document.analysis_id)
                if document.analysis_id
                else None
            )

            analytical_status = (
                self._document_analytical_status(
                    analysis_id=analysis_id,
                    statuses=(
                        document_analytical_statuses
                    ),
                )
            )

            documents.append(
                {
                    "document_id": str(
                        document.document_id
                    ),

                    "original_filename": (
                        document.original_filename
                    ),

                    "status": (
                        document.status.value
                    ),

                    "status_label": (
                        self
                        ._translate_document_status(
                            document.status.value
                        )
                    ),

                    "analysis_id": (
                        analysis_id
                    ),

                    "analysis_url": (
                        f"/analyses/{analysis_id}"
                        if analysis_id
                        else None
                    ),

                    "error_message": (
                        document.error_message
                    ),

                    "analytical_status": (
                        analytical_status.value
                    ),

                    "analytical_status_label": (
                        self._status_resolver.label(
                            analytical_status
                        )
                    ),
                }
            )

        return self._sort_documents(
            documents
        )

    def _document_analytical_status(
        self,
        *,
        analysis_id: str | None,
        statuses: dict[
            str,
            InvestigationStatus,
        ],
    ) -> InvestigationStatus:
        if analysis_id is None:
            return (
                InvestigationStatus
                .NOT_EXECUTED
            )

        status = statuses.get(
            analysis_id,
            (
                InvestigationStatus
                .NOT_EXECUTED
            ),
        )

        if not isinstance(
            status,
            InvestigationStatus,
        ):
            raise TypeError(
                "Document analytical status "
                "must be an InvestigationStatus."
            )

        return status

    def _build_analytical_summary(
        self,
        documents: list[
            dict[str, Any]
        ],
    ) -> dict[str, Any]:
        statuses = [
            InvestigationStatus(
                document[
                    "analytical_status"
                ]
            )
            for document in documents
        ]

        batch_status = (
            self._status_resolver
            .resolve_statuses(
                statuses
            )
        )

        alert_count = sum(
            status
            == InvestigationStatus.ALERT
            for status in statuses
        )

        attention_count = sum(
            status
            == InvestigationStatus.ATTENTION
            for status in statuses
        )

        clear_count = sum(
            status
            == InvestigationStatus.CLEAR
            for status in statuses
        )

        not_executed_count = sum(
            status
            == InvestigationStatus.NOT_EXECUTED
            for status in statuses
        )

        return {
            "status": (
                batch_status.value
            ),

            "status_label": (
                self._status_resolver.label(
                    batch_status
                )
            ),

            "alert_documents": (
                alert_count
            ),

            "attention_documents": (
                attention_count
            ),

            "clear_documents": (
                clear_count
            ),

            "not_executed_documents": (
                not_executed_count
            ),

            "classified_documents": (
                alert_count
                + attention_count
                + clear_count
            ),
        }

    def _sort_documents(
        self,
        documents: list[
            dict[str, Any]
        ],
    ) -> list[dict[str, Any]]:
        priority = {
            InvestigationStatus.ALERT.value: 0,
            InvestigationStatus.ATTENTION.value: 1,
            InvestigationStatus.CLEAR.value: 2,
            InvestigationStatus.NOT_EXECUTED.value: 3,
        }

        return sorted(
            documents,
            key=lambda document: (
                priority.get(
                    document[
                        "analytical_status"
                    ],
                    4,
                ),
                document[
                    "original_filename"
                ].lower(),
            ),
        )

    def _build_finding_summaries(
        self,
        summaries: list[
            BatchFindingSummary
        ],
    ) -> list[dict[str, Any]]:
        return [
            {
                "code": (
                    summary.code
                ),

                "title": (
                    summary.title
                ),

                "affected_documents": (
                    summary
                    .affected_documents
                ),

                "total_documents": (
                    summary
                    .total_documents
                ),

                "occurrence_count": (
                    summary
                    .occurrence_count
                ),

                "prevalence_percentage": (
                    summary
                    .prevalence_percentage
                ),

                "prevalence_label": (
                    self
                    ._format_prevalence_label(
                        summary
                        .prevalence_percentage
                    )
                ),

                "fraction_label": (
                    f"{summary.affected_documents}"
                    f" / "
                    f"{summary.total_documents}"
                ),

                "affected_document_ids": (
                    list(
                        summary
                        .affected_document_ids
                    )
                ),

                "highest_confidence": (
                    summary
                    .highest_confidence
                ),

                "highest_confidence_label": (
                    self._format_confidence(
                        summary
                        .highest_confidence
                    )
                ),
            }
            for summary in summaries
        ]

    def _format_datetime(
        self,
        value: datetime,
    ) -> str:
        return value.strftime(
            "%d/%m/%Y às %H:%M:%S"
        )

    def _format_optional_datetime(
        self,
        value: datetime | None,
    ) -> str:
        if value is None:
            return "Não informada"

        return self._format_datetime(
            value
        )

    def _format_prevalence_label(
        self,
        prevalence_percentage: float,
    ) -> str:
        return (
            f"{prevalence_percentage:.1f}%"
            .replace(".", ",")
        )

    def _format_confidence(
        self,
        confidence: float,
    ) -> str:
        percentage = (
            confidence
            * 100
        )

        return (
            f"{percentage:.0f}%"
        )

    def _translate_batch_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "pending": (
                "Aguardando processamento"
            ),

            "processing": (
                "Em processamento"
            ),

            "completed": (
                "Concluído"
            ),

            "completed_with_errors": (
                "Concluído com ocorrências"
            ),

            "failed": (
                "Falhou"
            ),
        }

        return labels.get(
            status,
            status,
        )

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

        return labels.get(
            status,
            status,
        )