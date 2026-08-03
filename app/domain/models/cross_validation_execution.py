from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.cross_validation_execution_metrics import (
    CrossValidationExecutionMetrics,
)
from app.domain.models.cross_validation_result import (
    CrossValidationResult,
)


@dataclass(frozen=True, slots=True)
class CrossValidationExecution:
    """
    Representa uma execução completa da validação cruzada.

    Agrupa o resultado funcional da validação
    e suas métricas de execução.
    """

    result: CrossValidationResult

    metrics: CrossValidationExecutionMetrics