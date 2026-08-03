from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """
    Representa uma confiança normalizada.

    Valor entre 0.0 e 1.0.
    """

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(
                "confidence must be between 0.0 and 1.0"
            )

    @property
    def percentage(self) -> float:
        return self.value * 100

    @property
    def is_high(self) -> bool:
        return self.value >= 0.90

    @property
    def is_medium(self) -> bool:
        return 0.70 <= self.value < 0.90

    @property
    def is_low(self) -> bool:
        return self.value < 0.70