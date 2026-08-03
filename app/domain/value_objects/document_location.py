from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.bounding_box import BoundingBox


@dataclass(frozen=True, slots=True)
class DocumentLocation:
    """
    Representa a localização de um elemento
    dentro de um documento.
    """

    page_number: int
    bounding_box: BoundingBox

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must be greater than zero")