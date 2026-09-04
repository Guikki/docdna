from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from app.domain.document.models.color import Color


@dataclass(frozen=True, slots=True)
class BackgroundColorEstimate:
    """
    Estimativa técnica da cor de fundo observada em uma região do PDF.

    O modelo registra apenas o resultado da amostragem visual. Ele não
    classifica contraste, ocultação, fraude ou intenção maliciosa.
    """

    color: Color
    dominance_ratio: float
    sampled_pixel_count: int
    method: str

    def __post_init__(self) -> None:
        if not isinstance(self.color, Color):
            raise TypeError(
                "BackgroundColorEstimate color must be a Color."
            )

        if (
            isinstance(self.dominance_ratio, bool)
            or not isinstance(
                self.dominance_ratio,
                (int, float),
            )
        ):
            raise TypeError(
                "BackgroundColorEstimate dominance_ratio must be numeric."
            )

        normalized_dominance = float(
            self.dominance_ratio
        )

        if not isfinite(normalized_dominance):
            raise ValueError(
                "BackgroundColorEstimate dominance_ratio must be finite."
            )

        if not 0.0 <= normalized_dominance <= 1.0:
            raise ValueError(
                "BackgroundColorEstimate dominance_ratio must be "
                "between 0.0 and 1.0."
            )

        if (
            isinstance(self.sampled_pixel_count, bool)
            or not isinstance(
                self.sampled_pixel_count,
                int,
            )
        ):
            raise TypeError(
                "BackgroundColorEstimate sampled_pixel_count "
                "must be an integer."
            )

        if self.sampled_pixel_count <= 0:
            raise ValueError(
                "BackgroundColorEstimate sampled_pixel_count "
                "must be greater than zero."
            )

        if not isinstance(self.method, str):
            raise TypeError(
                "BackgroundColorEstimate method must be a string."
            )

        normalized_method = self.method.strip()
        if not normalized_method:
            raise ValueError(
                "BackgroundColorEstimate method must not be empty."
            )

        object.__setattr__(
            self,
            "dominance_ratio",
            normalized_dominance,
        )
        object.__setattr__(
            self,
            "method",
            normalized_method,
        )
