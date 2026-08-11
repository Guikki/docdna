from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InvestigationMetric:
    """
    Representa uma métrica resumida exibida em uma investigação.

    Este objeto pertence exclusivamente à camada de apresentação.

    Ele não executa cálculos, não interpreta evidências e não define
    severidade. Apenas transporta um rótulo e um valor já preparados
    para exibição no frontend.
    """

    label: str
    value: str

    def __post_init__(self) -> None:
        normalized_label = self._normalize_text(
            field_name="label",
            value=self.label,
        )

        normalized_value = self._normalize_text(
            field_name="value",
            value=self.value,
        )

        object.__setattr__(
            self,
            "label",
            normalized_label,
        )

        object.__setattr__(
            self,
            "value",
            normalized_value,
        )

    @staticmethod
    def _normalize_text(
        *,
        field_name: str,
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"InvestigationMetric {field_name} "
                "must be a string."
            )

        normalized = " ".join(
            value.split()
        )

        if not normalized:
            raise ValueError(
                f"InvestigationMetric {field_name} "
                "cannot be empty."
            )

        return normalized