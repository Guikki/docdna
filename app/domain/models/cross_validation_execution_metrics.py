from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CrossValidationExecutionMetrics:
    """
    Representa métricas gerais de uma execução
    da validação cruzada.

    Este modelo apenas armazena dados observáveis.
    Ele não executa comparadores e não calcula findings.
    """

    documents_processed: int

    comparators_executed: int

    findings_generated: int

    execution_time_ms: float

    def __post_init__(self) -> None:
        if self.documents_processed < 0:
            raise ValueError(
                "documents_processed cannot be negative."
            )

        if self.comparators_executed < 0:
            raise ValueError(
                "comparators_executed cannot be negative."
            )

        if self.findings_generated < 0:
            raise ValueError(
                "findings_generated cannot be negative."
            )

        if self.execution_time_ms < 0:
            raise ValueError(
                "execution_time_ms cannot be negative."
            )

    @property
    def has_documents(self) -> bool:
        return self.documents_processed > 0

    @property
    def has_findings(self) -> bool:
        return self.findings_generated > 0

    @property
    def findings_per_document(self) -> float:
        if self.documents_processed == 0:
            return 0.0

        return (
            self.findings_generated
            / self.documents_processed
        )