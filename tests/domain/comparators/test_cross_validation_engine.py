from __future__ import annotations

from typing import Any

from app.domain.comparators.base_comparator import (
    BaseComparator,
)
from app.domain.comparators.cross_validation_engine import (
    CrossValidationEngine,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
    CrossValidationSeverity,
)
from app.domain.models.cross_validation_result import (
    CrossValidationResult,
)


class FakeComparator(BaseComparator):
    """
    Comparador falso utilizado para testar apenas o comportamento
    do CrossValidationEngine.

    Ele registra as análises recebidas e devolve os findings
    configurados no construtor.
    """

    def __init__(
        self,
        findings: list[CrossValidationFinding] | None = None,
    ) -> None:
        self._findings = findings or []

        self.received_analyses: list[
            list[dict[str, Any]]
        ] = []

    def compare(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[CrossValidationFinding]:
        self.received_analyses.append(
            analyses
        )

        return list(
            self._findings
        )


def create_finding(
    *,
    code: str,
    comparator: str,
    document_ids: list[str] | None = None,
) -> CrossValidationFinding:
    return CrossValidationFinding(
        code=code,
        title=f"Finding {code}",
        description=(
            f"Descrição de teste para o finding {code}."
        ),
        severity=CrossValidationSeverity.INFO,
        confidence=1.0,
        comparator=comparator,
        document_ids=(
            document_ids
            or [
                "document-1",
                "document-2",
            ]
        ),
        metadata={
            "test": True,
        },
    )


def test_should_return_empty_result_when_no_comparators_exist(
) -> None:
    engine = CrossValidationEngine(
        comparators=[],
    )

    result = engine.execute(
        analyses=[],
    )

    assert result.findings == []


def test_should_execute_registered_comparator() -> None:
    analyses = [
        {
            "id": "document-1",
        },
        {
            "id": "document-2",
        },
    ]

    comparator = FakeComparator()

    engine = CrossValidationEngine(
        comparators=[
            comparator,
        ],
    )

    engine.execute(
        analyses
    )

    assert comparator.received_analyses == [
        analyses,
    ]


def test_should_send_same_analyses_to_all_comparators(
) -> None:
    analyses = [
        {
            "id": "document-1",
        },
        {
            "id": "document-2",
        },
    ]

    first_comparator = FakeComparator()
    second_comparator = FakeComparator()
    third_comparator = FakeComparator()

    engine = CrossValidationEngine(
        comparators=[
            first_comparator,
            second_comparator,
            third_comparator,
        ],
    )

    engine.execute(
        analyses
    )

    assert first_comparator.received_analyses == [
        analyses,
    ]

    assert second_comparator.received_analyses == [
        analyses,
    ]

    assert third_comparator.received_analyses == [
        analyses,
    ]


def test_should_return_findings_from_single_comparator(
) -> None:
    first_finding = create_finding(
        code="FIRST_FINDING",
        comparator="FakeComparator",
    )

    second_finding = create_finding(
        code="SECOND_FINDING",
        comparator="FakeComparator",
    )

    comparator = FakeComparator(
        findings=[
            first_finding,
            second_finding,
        ]
    )

    engine = CrossValidationEngine(
        comparators=[
            comparator,
        ],
    )

    result = engine.execute(
        analyses=[],
    )

    assert result.findings == [
        first_finding,
        second_finding,
    ]


def test_should_aggregate_findings_from_multiple_comparators(
) -> None:
    first_finding = create_finding(
        code="FIRST_FINDING",
        comparator="FirstFakeComparator",
    )

    second_finding = create_finding(
        code="SECOND_FINDING",
        comparator="SecondFakeComparator",
    )

    third_finding = create_finding(
        code="THIRD_FINDING",
        comparator="SecondFakeComparator",
    )

    first_comparator = FakeComparator(
        findings=[
            first_finding,
        ]
    )

    second_comparator = FakeComparator(
        findings=[
            second_finding,
            third_finding,
        ]
    )

    engine = CrossValidationEngine(
        comparators=[
            first_comparator,
            second_comparator,
        ],
    )

    result = engine.execute(
        analyses=[],
    )

    assert result.findings == [
        first_finding,
        second_finding,
        third_finding,
    ]


def test_should_preserve_comparator_registration_order(
) -> None:
    first_finding = create_finding(
        code="FIRST",
        comparator="FirstComparator",
    )

    second_finding = create_finding(
        code="SECOND",
        comparator="SecondComparator",
    )

    third_finding = create_finding(
        code="THIRD",
        comparator="ThirdComparator",
    )

    engine = CrossValidationEngine(
        comparators=[
            FakeComparator(
                findings=[
                    first_finding,
                ]
            ),
            FakeComparator(
                findings=[
                    second_finding,
                ]
            ),
            FakeComparator(
                findings=[
                    third_finding,
                ]
            ),
        ],
    )

    result = engine.execute(
        analyses=[],
    )

    assert [
        finding.code
        for finding in result.findings
    ] == [
        "FIRST",
        "SECOND",
        "THIRD",
    ]


def test_should_preserve_finding_order_inside_comparator(
) -> None:
    first_finding = create_finding(
        code="FIRST",
        comparator="FakeComparator",
    )

    second_finding = create_finding(
        code="SECOND",
        comparator="FakeComparator",
    )

    third_finding = create_finding(
        code="THIRD",
        comparator="FakeComparator",
    )

    comparator = FakeComparator(
        findings=[
            first_finding,
            second_finding,
            third_finding,
        ]
    )

    result = CrossValidationEngine(
        comparators=[
            comparator,
        ],
    ).execute(
        analyses=[],
    )

    assert [
        finding.code
        for finding in result.findings
    ] == [
        "FIRST",
        "SECOND",
        "THIRD",
    ]


def test_comparator_without_findings_should_not_affect_other_results(
) -> None:
    finding = create_finding(
        code="VALID_FINDING",
        comparator="FindingComparator",
    )

    empty_comparator = FakeComparator()

    finding_comparator = FakeComparator(
        findings=[
            finding,
        ]
    )

    engine = CrossValidationEngine(
        comparators=[
            empty_comparator,
            finding_comparator,
            FakeComparator(),
        ],
    )

    result = engine.execute(
        analyses=[],
    )

    assert result.findings == [
        finding,
    ]


def test_should_execute_each_comparator_only_once(
) -> None:
    first_comparator = FakeComparator()
    second_comparator = FakeComparator()

    engine = CrossValidationEngine(
        comparators=[
            first_comparator,
            second_comparator,
        ],
    )

    analyses = [
        {
            "id": "document-1",
        },
    ]

    engine.execute(
        analyses
    )

    assert len(
        first_comparator.received_analyses
    ) == 1

    assert len(
        second_comparator.received_analyses
    ) == 1


def test_should_return_execution_with_metrics() -> None:
    finding = create_finding(
        code="TEST_FINDING",
        comparator="FakeComparator",
    )

    engine = CrossValidationEngine(
        comparators=[
            FakeComparator(
                findings=[
                    finding,
                ],
            ),
        ],
    )

    execution = engine.execute_with_metrics(
        analyses=[
            {
                "id": "document-1",
            },
            {
                "id": "document-2",
            },
        ],
    )

    assert execution.result.findings == [
        finding,
    ]

    assert (
        execution.metrics.documents_processed
        == 2
    )

    assert (
        execution.metrics.comparators_executed
        == 1
    )

    assert (
        execution.metrics.findings_generated
        == 1
    )

    assert (
        execution.metrics.execution_time_ms
        >= 0
    )


def test_execute_should_preserve_original_contract(
) -> None:
    finding = create_finding(
        code="TEST",
        comparator="FakeComparator",
    )

    engine = CrossValidationEngine(
        comparators=[
            FakeComparator(
                findings=[
                    finding,
                ],
            ),
        ],
    )

    result = engine.execute(
        analyses=[],
    )

    assert isinstance(
        result,
        CrossValidationResult,
    )

    assert result.findings == [
        finding,
    ]


def test_should_return_zero_metrics_when_no_comparators_exist(
) -> None:
    engine = CrossValidationEngine(
        comparators=[],
    )

    execution = engine.execute_with_metrics(
        analyses=[],
    )

    assert execution.result.findings == []

    assert (
        execution.metrics.documents_processed
        == 0
    )

    assert (
        execution.metrics.comparators_executed
        == 0
    )

    assert (
        execution.metrics.findings_generated
        == 0
    )

    assert (
        execution.metrics.execution_time_ms
        >= 0
    )