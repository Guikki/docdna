from __future__ import annotations

from app.domain.models.cross_validation_execution import (
    CrossValidationExecution,
)
from app.domain.models.cross_validation_execution_metrics import (
    CrossValidationExecutionMetrics,
)
from app.domain.models.cross_validation_result import (
    CrossValidationResult,
)


def test_should_create_cross_validation_execution() -> None:
    result = CrossValidationResult(
        findings=[],
    )

    metrics = CrossValidationExecutionMetrics(
        documents_processed=2,
        comparators_executed=3,
        findings_generated=0,
        execution_time_ms=10.5,
    )

    execution = CrossValidationExecution(
        result=result,
        metrics=metrics,
    )

    assert execution.result is result
    assert execution.metrics is metrics