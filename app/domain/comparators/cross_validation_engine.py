from time import perf_counter
from typing import Any

from app.domain.comparators.base_comparator import (
    BaseComparator,
)
from app.domain.models.cross_validation_execution import (
    CrossValidationExecution,
)
from app.domain.models.cross_validation_execution_metrics import (
    CrossValidationExecutionMetrics,
)
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
        """
        Executa todos os comparadores registrados e retorna
        somente o resultado funcional da validação cruzada.

        Este método preserva o contrato original do engine.
        """
        execution = self.execute_with_metrics(
            analyses=analyses
        )

        return execution.result

    def execute_with_metrics(
        self,
        analyses: list[dict[str, Any]],
    ) -> CrossValidationExecution:
        """
        Executa todos os comparadores registrados e retorna
        o resultado funcional acompanhado das métricas gerais
        da execução.
        """
        started_at = perf_counter()

        findings = []

        for comparator in self._comparators:
            comparator_findings = comparator.compare(
                analyses
            )

            findings.extend(
                comparator_findings
            )

        result = CrossValidationResult(
            findings=findings
        )

        finished_at = perf_counter()

        execution_time_ms = (
            finished_at - started_at
        ) * 1000

        metrics = CrossValidationExecutionMetrics(
            documents_processed=len(analyses),
            comparators_executed=len(
                self._comparators
            ),
            findings_generated=len(findings),
            execution_time_ms=execution_time_ms,
        )

        return CrossValidationExecution(
            result=result,
            metrics=metrics,
        )