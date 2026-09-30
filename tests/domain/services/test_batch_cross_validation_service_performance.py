from types import SimpleNamespace
from uuid import uuid4

from app.domain.models.cross_validation_result import (
    CrossValidationResult,
)
from app.domain.services.batch_cross_validation_service import (
    BatchCrossValidationService,
)


class _FakeAnalysisRepository:
    def __init__(
        self,
        analyses,
    ) -> None:
        self._analyses = (
            analyses
        )

    def get_by_id(
        self,
        analysis_id,
    ):
        return self._analyses.get(
            analysis_id
        )


class _FakeEngine:
    def execute_with_metrics(
        self,
        *,
        analyses,
    ):
        return SimpleNamespace(
            result=(
                CrossValidationResult(
                    findings=[]
                )
            ),
            metrics=SimpleNamespace(
                documents_processed=(
                    len(analyses)
                ),
                comparators_executed=4,
                findings_generated=0,
                execution_time_ms=12.5,
            ),
        )


class _FakeEvidenceReportBuilder:
    def build(
        self,
        cross_validation_result,
    ):
        return SimpleNamespace(
            evidences=[]
        )


class _FakeImageFingerprintComparator:
    def __init__(
        self,
        *,
        selection_stats=None,
    ) -> None:
        self.selection_stats = (
            selection_stats
        )


def test_should_expose_cross_validation_performance_report(
) -> None:
    first_id = uuid4()
    second_id = uuid4()

    batch = SimpleNamespace(
        documents=[
            SimpleNamespace(
                analysis_id=first_id
            ),
            SimpleNamespace(
                analysis_id=second_id
            ),
        ]
    )

    service = (
        BatchCrossValidationService()
    )

    service._analysis_repository = (
        _FakeAnalysisRepository(
            {
                first_id: {
                    "id": first_id
                },
                second_id: {
                    "id": second_id
                },
            }
        )
    )

    service._engine = (
        _FakeEngine()
    )

    service._evidence_report_builder = (
        _FakeEvidenceReportBuilder()
    )

    (
        result,
        evidence_report,
    ) = service.execute_with_report(
        batch
    )

    assert result.findings == []

    assert (
        evidence_report.evidences
        == []
    )

    report = (
        service.performance_report
    )

    assert report is not None

    assert (
        report["analyses_loaded"]
        == 2
    )

    assert (
        report[
            "engine_metrics"
        ][
            "comparators_executed"
        ]
        == 4
    )

    assert (
        report[
            "engine_metrics"
        ][
            "execution_time_ms"
        ]
        == 12.5
    )

    assert (
        "load_batch_analyses"
        in report["stages"]
    )

    assert (
        "cross_validation_engine"
        in report["stages"]
    )

    assert (
        "evidence_report_builder"
        in report["stages"]
    )

    assert (
        report[
            "image_candidate_selection"
        ]
        is None
    )


def test_should_skip_engine_when_batch_has_less_than_two_analyses(
) -> None:
    analysis_id = uuid4()

    batch = SimpleNamespace(
        documents=[
            SimpleNamespace(
                analysis_id=analysis_id
            )
        ]
    )

    service = (
        BatchCrossValidationService()
    )

    service._analysis_repository = (
        _FakeAnalysisRepository(
            {
                analysis_id: {
                    "id": analysis_id
                }
            }
        )
    )

    result = service.execute(
        batch
    )

    assert result.findings == []

    report = (
        service.performance_report
    )

    assert report is not None

    assert (
        report[
            "engine_metrics"
        ][
            "comparators_executed"
        ]
        == 0
    )

    assert (
        "cross_validation_engine"
        not in report["stages"]
    )

    assert (
        report[
            "image_candidate_selection"
        ]
        is None
    )


def test_should_expose_image_candidate_selection_metrics(
) -> None:
    first_id = uuid4()
    second_id = uuid4()

    batch = SimpleNamespace(
        documents=[
            SimpleNamespace(
                analysis_id=first_id
            ),
            SimpleNamespace(
                analysis_id=second_id
            ),
        ]
    )

    service = (
        BatchCrossValidationService()
    )

    service._analysis_repository = (
        _FakeAnalysisRepository(
            {
                first_id: {
                    "id": first_id
                },
                second_id: {
                    "id": second_id
                },
            }
        )
    )

    service._engine = (
        _FakeEngine()
    )

    service._image_fingerprint_comparator = (
        _FakeImageFingerprintComparator(
            selection_stats=(
                SimpleNamespace(
                    documents_total=2,
                    fingerprints_total=100,
                    potential_cross_document_pairs=2500,
                    candidate_pairs=25,
                    exact_sha256_pairs=10,
                    perceptual_only_pairs=15,
                    reduction_ratio=0.99,
                )
            )
        )
    )

    service.execute(
        batch
    )

    report = (
        service.performance_report
    )

    assert report is not None

    image_metrics = (
        report[
            "image_candidate_selection"
        ]
    )

    assert (
        image_metrics is not None
    )

    assert (
        image_metrics[
            "documents_total"
        ]
        == 2
    )

    assert (
        image_metrics[
            "fingerprints_total"
        ]
        == 100
    )

    assert (
        image_metrics[
            "potential_cross_document_pairs"
        ]
        == 2500
    )

    assert (
        image_metrics[
            "candidate_pairs"
        ]
        == 25
    )

    assert (
        image_metrics[
            "exact_sha256_pairs"
        ]
        == 10
    )

    assert (
        image_metrics[
            "perceptual_only_pairs"
        ]
        == 15
    )

    assert (
        image_metrics[
            "reduction_ratio"
        ]
        == 0.99
    )

    assert (
        image_metrics[
            "reduction_percentage"
        ]
        == 99.0
    )


def test_short_batch_should_not_reuse_previous_image_metrics(
) -> None:
    first_id = uuid4()
    second_id = uuid4()

    service = (
        BatchCrossValidationService()
    )

    service._engine = (
        _FakeEngine()
    )

    service._image_fingerprint_comparator = (
        _FakeImageFingerprintComparator(
            selection_stats=(
                SimpleNamespace(
                    documents_total=2,
                    fingerprints_total=10,
                    potential_cross_document_pairs=25,
                    candidate_pairs=1,
                    exact_sha256_pairs=0,
                    perceptual_only_pairs=1,
                    reduction_ratio=0.96,
                )
            )
        )
    )

    service._analysis_repository = (
        _FakeAnalysisRepository(
            {
                first_id: {
                    "id": first_id
                },
                second_id: {
                    "id": second_id
                },
            }
        )
    )

    first_batch = SimpleNamespace(
        documents=[
            SimpleNamespace(
                analysis_id=first_id
            ),
            SimpleNamespace(
                analysis_id=second_id
            ),
        ]
    )

    service.execute(
        first_batch
    )

    assert (
        service
        .performance_report[
            "image_candidate_selection"
        ]
        is not None
    )

    second_batch = SimpleNamespace(
        documents=[
            SimpleNamespace(
                analysis_id=first_id
            )
        ]
    )

    service.execute(
        second_batch
    )

    assert (
        service
        .performance_report[
            "image_candidate_selection"
        ]
        is None
    )