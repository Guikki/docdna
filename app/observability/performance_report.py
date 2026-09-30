from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class PerformanceStageReport:
    """
    Resultado imutável da medição de uma etapa
    da pipeline.
    """

    name: str
    duration_seconds: float
    calls: int

    @property
    def average_seconds(
        self,
    ) -> float:
        if self.calls <= 0:
            return 0.0

        return (
            self.duration_seconds
            / self.calls
        )

    def percentage_of(
        self,
        total_seconds: float,
    ) -> float:
        if total_seconds <= 0:
            return 0.0

        return (
            self.duration_seconds
            / total_seconds
            * 100.0
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PerformanceReport:
    """
    Snapshot imutável das medições realizadas
    por um PerformanceTimer.
    """

    total_seconds: float

    stages: tuple[
        PerformanceStageReport,
        ...,
    ]

    def get_stage(
        self,
        name: str,
    ) -> PerformanceStageReport | None:
        normalized_name = (
            str(name or "")
            .strip()
        )

        for stage in self.stages:
            if (
                stage.name
                == normalized_name
            ):
                return stage

        return None

    def to_dict(
        self,
    ) -> dict:
        return {
            "total_seconds": round(
                self.total_seconds,
                6,
            ),
            "stages": {
                stage.name: {
                    "duration_seconds": round(
                        stage.duration_seconds,
                        6,
                    ),
                    "calls": stage.calls,
                    "average_seconds": round(
                        stage.average_seconds,
                        6,
                    ),
                    "percentage_of_total": round(
                        stage.percentage_of(
                            self.total_seconds
                        ),
                        2,
                    ),
                }
                for stage
                in self.stages
            },
        }