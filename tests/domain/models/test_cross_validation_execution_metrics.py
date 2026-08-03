from __future__ import annotations

import pytest

from app.domain.models.cross_validation_execution_metrics import (
    CrossValidationExecutionMetrics,
)


def create_metrics(
    *,
    documents_processed: int = 10,
    comparators_executed: int = 3,
    findings_generated: int = 5,
    execution_time_ms: float = 125.5,
) -> CrossValidationExecutionMetrics:
    return CrossValidationExecutionMetrics(
        documents_processed=documents_processed,
        comparators_executed=comparators_executed,
        findings_generated=findings_generated,
        execution_time_ms=execution_time_ms,
    )


def test_should_create_execution_metrics() -> None:
    metrics = create_metrics()

    assert metrics.documents_processed == 10
    assert metrics.comparators_executed == 3
    assert metrics.findings_generated == 5
    assert metrics.execution_time_ms == 125.5


def test_should_accept_zero_values() -> None:
    metrics = create_metrics(
        documents_processed=0,
        comparators_executed=0,
        findings_generated=0,
        execution_time_ms=0.0,
    )

    assert metrics.documents_processed == 0
    assert metrics.comparators_executed == 0
    assert metrics.findings_generated == 0
    assert metrics.execution_time_ms == 0.0


@pytest.mark.parametrize(
    ("field_name", "error_message"),
    [
        (
            "documents_processed",
            "documents_processed cannot be negative.",
        ),
        (
            "comparators_executed",
            "comparators_executed cannot be negative.",
        ),
        (
            "findings_generated",
            "findings_generated cannot be negative.",
        ),
        (
            "execution_time_ms",
            "execution_time_ms cannot be negative.",
        ),
    ],
)
def test_should_reject_negative_values(
    field_name: str,
    error_message: str,
) -> None:
    values = {
        "documents_processed": 10,
        "comparators_executed": 3,
        "findings_generated": 5,
        "execution_time_ms": 125.5,
    }

    values[field_name] = -1

    with pytest.raises(
        ValueError,
        match=error_message,
    ):
        CrossValidationExecutionMetrics(
            **values,
        )


def test_should_indicate_when_documents_exist() -> None:
    metrics = create_metrics(
        documents_processed=1,
    )

    assert metrics.has_documents is True


def test_should_indicate_when_documents_do_not_exist() -> None:
    metrics = create_metrics(
        documents_processed=0,
    )

    assert metrics.has_documents is False


def test_should_indicate_when_findings_exist() -> None:
    metrics = create_metrics(
        findings_generated=1,
    )

    assert metrics.has_findings is True


def test_should_indicate_when_findings_do_not_exist() -> None:
    metrics = create_metrics(
        findings_generated=0,
    )

    assert metrics.has_findings is False


def test_should_calculate_findings_per_document() -> None:
    metrics = create_metrics(
        documents_processed=4,
        findings_generated=10,
    )

    assert metrics.findings_per_document == 2.5


def test_should_return_zero_findings_per_document_when_no_documents_exist(
) -> None:
    metrics = create_metrics(
        documents_processed=0,
        findings_generated=0,
    )

    assert metrics.findings_per_document == 0.0
