from __future__ import annotations

from typing import Any

from app.domain.builders.evidence_report_builder import (
    EvidenceReportBuilder,
)
from app.domain.comparators.cross_validation_engine import (
    CrossValidationEngine,
)
from app.domain.comparators.duplicate_itf_comparator import (
    DuplicateItfComparator,
)
from app.domain.comparators.duplicate_itf_different_numeric_line_comparator import (
    DuplicateItfDifferentNumericLineComparator,
)
from app.domain.comparators.image_fingerprint_cross_comparator import (
    ImageFingerprintCrossComparator,
)
from app.domain.comparators.qrcode_fingerprint_cross_comparator import (
    QRCodeFingerprintCrossComparator,
)
from app.domain.models.batch import Batch
from app.domain.models.cross_validation_result import (
    CrossValidationResult,
)
from app.domain.models.evidence_report import (
    EvidenceReport,
)
from app.infrastructure.repositories.analysis_memory_repository import (
    AnalysisMemoryRepository,
)
from app.observability.performance_timer import (
    PerformanceTimer,
)


class BatchCrossValidationService:

    def __init__(self) -> None:
        self._analysis_repository = (
            AnalysisMemoryRepository()
        )

        self._image_fingerprint_comparator = (
            ImageFingerprintCrossComparator()
        )

        self._engine = CrossValidationEngine(
            comparators=[
                DuplicateItfComparator(),
                DuplicateItfDifferentNumericLineComparator(),
                self._image_fingerprint_comparator,
                QRCodeFingerprintCrossComparator(),
            ]
        )

        self._evidence_report_builder = (
            EvidenceReportBuilder()
        )

        self._performance_report: (
            dict[str, Any]
            | None
        ) = None

    @property
    def performance_report(
        self,
    ) -> dict[str, Any] | None:
        return self._performance_report

    def execute(
        self,
        batch: Batch,
    ) -> CrossValidationResult:
        (
            result,
            timer,
            metrics,
            analyses_loaded,
            image_candidate_selection,
        ) = self._execute_core(
            batch
        )

        self._performance_report = (
            self._build_performance_report(
                timer=timer,
                engine_metrics=metrics,
                analyses_loaded=(
                    analyses_loaded
                ),
                image_candidate_selection=(
                    image_candidate_selection
                ),
            )
        )

        return result

    def build_evidence_report(
        self,
        batch: Batch,
    ) -> EvidenceReport:
        (
            result,
            timer,
            metrics,
            analyses_loaded,
            image_candidate_selection,
        ) = self._execute_core(
            batch
        )

        with timer.measure(
            "evidence_report_builder"
        ):
            evidence_report = (
                self._evidence_report_builder
                .build(
                    result
                )
            )

        self._performance_report = (
            self._build_performance_report(
                timer=timer,
                engine_metrics=metrics,
                analyses_loaded=(
                    analyses_loaded
                ),
                image_candidate_selection=(
                    image_candidate_selection
                ),
            )
        )

        return evidence_report

    def execute_with_report(
        self,
        batch: Batch,
    ) -> tuple[
        CrossValidationResult,
        EvidenceReport,
    ]:
        (
            result,
            timer,
            metrics,
            analyses_loaded,
            image_candidate_selection,
        ) = self._execute_core(
            batch
        )

        with timer.measure(
            "evidence_report_builder"
        ):
            evidence_report = (
                self._evidence_report_builder
                .build(
                    result
                )
            )

        self._performance_report = (
            self._build_performance_report(
                timer=timer,
                engine_metrics=metrics,
                analyses_loaded=(
                    analyses_loaded
                ),
                image_candidate_selection=(
                    image_candidate_selection
                ),
            )
        )

        return (
            result,
            evidence_report,
        )

    def _execute_core(
        self,
        batch: Batch,
    ) -> tuple[
        CrossValidationResult,
        PerformanceTimer,
        dict[str, Any],
        int,
        dict[str, Any] | None,
    ]:
        timer = PerformanceTimer()

        self._performance_report = None

        with timer.measure(
            "load_batch_analyses"
        ):
            analyses = (
                self._load_batch_analyses(
                    batch
                )
            )

        analyses_loaded = len(
            analyses
        )

        if analyses_loaded < 2:
            return (
                CrossValidationResult(
                    findings=[]
                ),
                timer,
                {
                    "documents_processed": (
                        analyses_loaded
                    ),
                    "comparators_executed": 0,
                    "findings_generated": 0,
                    "execution_time_ms": 0.0,
                },
                analyses_loaded,
                None,
            )

        with timer.measure(
            "cross_validation_engine"
        ):
            execution = (
                self._engine
                .execute_with_metrics(
                    analyses=analyses
                )
            )

        metrics = execution.metrics

        image_candidate_selection = (
            self._build_image_candidate_selection_report()
        )

        return (
            execution.result,
            timer,
            {
                "documents_processed": (
                    metrics.documents_processed
                ),
                "comparators_executed": (
                    metrics.comparators_executed
                ),
                "findings_generated": (
                    metrics.findings_generated
                ),
                "execution_time_ms": round(
                    metrics.execution_time_ms,
                    6,
                ),
            },
            analyses_loaded,
            image_candidate_selection,
        )

    def _build_performance_report(
        self,
        *,
        timer: PerformanceTimer,
        engine_metrics: dict[
            str,
            Any,
        ],
        analyses_loaded: int,
        image_candidate_selection: (
            dict[str, Any]
            | None
        ),
    ) -> dict[str, Any]:
        report = timer.to_dict()

        return {
            "total_seconds": (
                report.get(
                    "total_seconds",
                    0.0,
                )
            ),
            "analyses_loaded": (
                analyses_loaded
            ),
            "stages": report.get(
                "stages",
                {},
            ),
            "engine_metrics": (
                engine_metrics
            ),
            "image_candidate_selection": (
                image_candidate_selection
            ),
        }

    def _build_image_candidate_selection_report(
        self,
    ) -> dict[str, Any] | None:
        """
        Converte as métricas internas da seleção visual em dados
        simples para observabilidade e profiling.

        Nenhum fingerprint ou par é duplicado nesta etapa.
        """
        stats = (
            self
            ._image_fingerprint_comparator
            .selection_stats
        )

        if stats is None:
            return None

        return {
            "documents_total": (
                stats.documents_total
            ),
            "fingerprints_total": (
                stats.fingerprints_total
            ),
            "potential_cross_document_pairs": (
                stats
                .potential_cross_document_pairs
            ),
            "candidate_pairs": (
                stats.candidate_pairs
            ),
            "exact_sha256_pairs": (
                stats.exact_sha256_pairs
            ),
            "perceptual_only_pairs": (
                stats.perceptual_only_pairs
            ),
            "reduction_ratio": (
                stats.reduction_ratio
            ),
            "reduction_percentage": round(
                stats.reduction_ratio
                * 100.0,
                6,
            ),
        }

    def _load_batch_analyses(
        self,
        batch: Batch,
    ) -> list[
        dict[str, Any]
    ]:
        analyses: list[
            dict[str, Any]
        ] = []

        for batch_document in (
            batch.documents
        ):
            analysis_id = (
                batch_document.analysis_id
            )

            if analysis_id is None:
                continue

            analysis = (
                self._analysis_repository
                .get_by_id(
                    analysis_id
                )
            )

            if analysis is None:
                continue

            analyses.append(
                analysis
            )

        return analyses