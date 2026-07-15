from typing import Any

from app.domain.comparators.base_comparator import BaseComparator
from app.domain.models.cross_validation_result import (
    CrossValidationResult,
)


class CrossValidationEngine:

    def __init__(
        self,
        comparators: list[BaseComparator],
    ) -> None:
        self._comparators = comparators

    def execute(
        self,
        analyses: list[dict[str, Any]],
    ) -> CrossValidationResult:
        findings = []

        for comparator in self._comparators:
            comparator_findings = comparator.compare(
                analyses
            )

            findings.extend(comparator_findings)

        return CrossValidationResult(
            findings=findings
        )