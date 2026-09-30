from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import (
    Callable,
    Iterator,
)

from app.observability.performance_report import (
    PerformanceReport,
    PerformanceStageReport,
)


@dataclass(
    slots=True,
)
class _StageAccumulator:
    duration_seconds: float = 0.0
    calls: int = 0


class PerformanceTimer:
    """
    Cronômetro reutilizável para instrumentação
    da pipeline do DocDNA.

    Utiliza perf_counter por padrão, apropriado
    para medição de duração.
    """

    def __init__(
        self,
        *,
        clock: Callable[
            [],
            float,
        ] | None = None,
    ) -> None:
        self._clock = (
            clock
            or perf_counter
        )

        self._started_at = (
            self._clock()
        )

        self._stages: dict[
            str,
            _StageAccumulator,
        ] = {}

    @contextmanager
    def measure(
        self,
        stage_name: str,
    ) -> Iterator[None]:
        """
        Mede uma etapa.

        A medição é registrada inclusive quando
        a operação interna lança uma exceção.
        """

        normalized_name = (
            self._normalize_stage_name(
                stage_name
            )
        )

        started_at = (
            self._clock()
        )

        try:
            yield

        finally:
            finished_at = (
                self._clock()
            )

            elapsed = max(
                finished_at
                - started_at,
                0.0,
            )

            accumulator = (
                self._stages.get(
                    normalized_name
                )
            )

            if accumulator is None:
                accumulator = (
                    _StageAccumulator()
                )

                self._stages[
                    normalized_name
                ] = accumulator

            accumulator.duration_seconds += (
                elapsed
            )

            accumulator.calls += 1

    def report(
        self,
    ) -> PerformanceReport:
        """
        Retorna um snapshot imutável do estado
        atual do cronômetro.
        """

        total_seconds = max(
            self._clock()
            - self._started_at,
            0.0,
        )

        stages = tuple(
            PerformanceStageReport(
                name=name,
                duration_seconds=(
                    accumulator
                    .duration_seconds
                ),
                calls=(
                    accumulator.calls
                ),
            )
            for (
                name,
                accumulator,
            )
            in self._stages.items()
        )

        return PerformanceReport(
            total_seconds=total_seconds,
            stages=stages,
        )

    def to_dict(
        self,
    ) -> dict:
        return (
            self.report()
            .to_dict()
        )

    @staticmethod
    def _normalize_stage_name(
        stage_name: str,
    ) -> str:
        normalized_name = (
            str(
                stage_name
                or ""
            )
            .strip()
        )

        if not normalized_name:
            raise ValueError(
                "stage_name cannot be empty."
            )

        return normalized_name