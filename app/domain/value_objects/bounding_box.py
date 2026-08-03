from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """
    Representa uma região retangular em uma página.

    Todas as coordenadas são dadas em pontos (pt)
    relativos ao canto superior esquerdo da página.
    """

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be greater than zero")

        if self.height <= 0:
            raise ValueError("height must be greater than zero")

        if self.x < 0:
            raise ValueError("x cannot be negative")

        if self.y < 0:
            raise ValueError("y cannot be negative")

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def area(self) -> float:
        return self.width * self.height

    def intersects(self, other: "BoundingBox") -> bool:
        return not (
            self.right <= other.x
            or other.right <= self.x
            or self.bottom <= other.y
            or other.bottom <= self.y
        )