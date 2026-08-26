from types import SimpleNamespace
from uuid import uuid4

from app.domain.services.batch_finding_aggregation_service import (
    BatchFindingAggregationService,
)


def _analysis(
    *,
    analysis_id=None,
    evidences=None,
    prompt_injection_evidences=None,
    prompt_injection_score=0.0,
    white_text_findings=None,
    tiny_text_evidences=None,
):
    analysis_id = (
        analysis_id
        or uuid4()
    )

    prompt_assessment = None

    if prompt_injection_evidences is not None:
        prompt_assessment = SimpleNamespace(
            score=prompt_injection_score,
            evidences=tuple(
                prompt_injection_evidences
            ),
        )

    concealment_analysis = SimpleNamespace(
        white_text_findings=tuple(
            white_text_findings
            or []
        ),
        tiny_text_evidences=tuple(
            tiny_text_evidences
            or []
        ),
    )

    return {
        "id": analysis_id,
        "evidences": evidences or [],
        "prompt_injection_assessment": (
            prompt_assessment
        ),
        "visual_concealment_analysis": (
            concealment_analysis
        ),
    }


def _finding(
    *,
    code="TEST_FINDING",
    title="Achado de teste",
    confidence=0.8,
):
    return SimpleNamespace(
        code=code,
        title=title,
        confidence=confidence,
    )


def _prompt_evidence(
    *,
    confidence=0.8,
):
    return SimpleNamespace(
        confidence=confidence,
    )


def _concealment_finding(
    *,
    confidence=0.8,
):
    return SimpleNamespace(
        confidence=confidence,
    )


def _summary_by_code(
    summaries,
    code,
):
    return next(
        summary
        for summary in summaries
        if summary.code == code
    )


def test_returns_empty_list_when_there_are_no_analyses():
    service = (
        BatchFindingAggregationService()
    )

    result = service.aggregate([])

    assert result == []


def test_ignores_analysis_without_identifier():
    service = (
        BatchFindingAggregationService()
    )

    analyses = [
        {
            "id": None,
            "evidences": [
                _finding()
            ],
        }
    ]

    result = service.aggregate(
        analyses
    )

    assert result == []


def test_counts_generic_finding_by_affected_document():
    service = (
        BatchFindingAggregationService()
    )

    analyses = [
        _analysis(
            evidences=[
                _finding(
                    code="BARCODE_DIVERGENCE",
                    title="Barcode divergente",
                )
            ]
        ),
        _analysis(
            evidences=[
                _finding(
                    code="BARCODE_DIVERGENCE",
                    title="Barcode divergente",
                )
            ]
        ),
        _analysis(),
    ]

    result = service.aggregate(
        analyses
    )

    summary = _summary_by_code(
        result,
        "BARCODE_DIVERGENCE",
    )

    assert summary.affected_documents == 2
    assert summary.total_documents == 3
    assert summary.occurrence_count == 2

    assert (
        summary.prevalence_percentage
        == 66.67
    )


def test_multiple_occurrences_in_same_document_count_as_one_affected_document():
    service = (
        BatchFindingAggregationService()
    )

    analyses = [
        _analysis(
            evidences=[
                _finding(
                    code="BARCODE_DIVERGENCE",
                    title="Barcode divergente",
                ),
                _finding(
                    code="BARCODE_DIVERGENCE",
                    title="Barcode divergente",
                ),
                _finding(
                    code="BARCODE_DIVERGENCE",
                    title="Barcode divergente",
                ),
            ]
        ),
        _analysis(),
    ]

    result = service.aggregate(
        analyses
    )

    summary = _summary_by_code(
        result,
        "BARCODE_DIVERGENCE",
    )

    assert summary.affected_documents == 1
    assert summary.total_documents == 2

    assert summary.occurrence_count == 3

    assert (
        summary.prevalence_percentage
        == 50.0
    )


def test_aggregates_prompt_injection_by_document():
    service = (
        BatchFindingAggregationService()
    )

    analyses = [
        _analysis(
            prompt_injection_evidences=[
                _prompt_evidence(
                    confidence=0.7
                ),
                _prompt_evidence(
                    confidence=0.9
                ),
            ],
            prompt_injection_score=0.85,
        ),
        _analysis(
            prompt_injection_evidences=[
                _prompt_evidence(
                    confidence=0.6
                )
            ],
            prompt_injection_score=0.65,
        ),
        _analysis(
            prompt_injection_evidences=[],
        ),
    ]

    result = service.aggregate(
        analyses
    )

    summary = _summary_by_code(
        result,
        "PROMPT_INJECTION",
    )

    assert summary.title == (
        "Prompt Injection"
    )

    assert summary.affected_documents == 2
    assert summary.total_documents == 3

    assert summary.occurrence_count == 3

    assert (
        summary.prevalence_percentage
        == 66.67
    )

    assert (
        summary.highest_confidence
        == 0.85
    )


def test_aggregates_visual_concealment_by_document():
    service = (
        BatchFindingAggregationService()
    )

    analyses = [
        _analysis(
            white_text_findings=[
                _concealment_finding(
                    confidence=0.91
                ),
                _concealment_finding(
                    confidence=0.87
                ),
            ]
        ),
        _analysis(
            tiny_text_evidences=[
                _concealment_finding(
                    confidence=0.78
                )
            ]
        ),
        _analysis(),
    ]

    result = service.aggregate(
        analyses
    )

    summary = _summary_by_code(
        result,
        "VISUAL_CONCEALMENT",
    )

    assert summary.title == (
        "Ocultação visual"
    )

    assert summary.affected_documents == 2
    assert summary.total_documents == 3

    assert summary.occurrence_count == 3

    assert (
        summary.prevalence_percentage
        == 66.67
    )

    assert (
        summary.highest_confidence
        == 0.91
    )


def test_calculates_prevalence_for_28_of_30_documents():
    service = (
        BatchFindingAggregationService()
    )

    analyses = []

    for index in range(30):
        if index < 28:
            analyses.append(
                _analysis(
                    white_text_findings=[
                        _concealment_finding()
                    ]
                )
            )
        else:
            analyses.append(
                _analysis()
            )

    result = service.aggregate(
        analyses
    )

    summary = _summary_by_code(
        result,
        "VISUAL_CONCEALMENT",
    )

    assert summary.affected_documents == 28
    assert summary.total_documents == 30

    assert (
        summary.prevalence_percentage
        == 93.33
    )


def test_returns_100_percent_when_all_documents_are_affected():
    service = (
        BatchFindingAggregationService()
    )

    analyses = [
        _analysis(
            white_text_findings=[
                _concealment_finding()
            ]
        )
        for _ in range(10)
    ]

    result = service.aggregate(
        analyses
    )

    summary = _summary_by_code(
        result,
        "VISUAL_CONCEALMENT",
    )

    assert summary.affected_documents == 10
    assert summary.total_documents == 10

    assert (
        summary.prevalence_percentage
        == 100.0
    )


def test_sorting_prioritizes_findings_with_more_affected_documents():
    service = (
        BatchFindingAggregationService()
    )

    analyses = [
        _analysis(
            evidences=[
                _finding(
                    code="COMMON_FINDING",
                    title="Achado comum",
                )
            ],
            prompt_injection_evidences=[
                _prompt_evidence()
            ],
        ),
        _analysis(
            evidences=[
                _finding(
                    code="COMMON_FINDING",
                    title="Achado comum",
                )
            ],
        ),
        _analysis(
            evidences=[
                _finding(
                    code="COMMON_FINDING",
                    title="Achado comum",
                )
            ],
        ),
    ]

    result = service.aggregate(
        analyses
    )

    assert result[0].code == (
        "COMMON_FINDING"
    )

    assert (
        result[0].affected_documents
        == 3
    )

    assert (
        result[1].code
        == "PROMPT_INJECTION"
    )