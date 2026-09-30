from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.models.forensic_data_layer import (
    ForensicDataLayer,
)


@dataclass(frozen=True, slots=True)
class ForensicProvenance:
    document_id: UUID
    layer: ForensicDataLayer
    producer: str
    producer_version: str
    page_number: int | None = None
    parent_element_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.document_id, UUID):
            raise TypeError(
                "ForensicProvenance document_id must be a UUID."
            )

        if not isinstance(self.layer, ForensicDataLayer):
            raise TypeError(
                "ForensicProvenance layer must be a ForensicDataLayer."
            )

        producer = self._normalize_required_text(
            self.producer,
            field_name="producer",
        )

        producer_version = self._normalize_required_text(
            self.producer_version,
            field_name="producer_version",
        )

        if (
            self.page_number is not None
            and (
                not isinstance(self.page_number, int)
                or isinstance(self.page_number, bool)
                or self.page_number < 1
            )
        ):
            raise ValueError(
                "ForensicProvenance page_number must be "
                "greater than or equal to 1."
            )

        if (
            self.parent_element_id is not None
            and not isinstance(self.parent_element_id, UUID)
        ):
            raise TypeError(
                "ForensicProvenance parent_element_id "
                "must be a UUID or None."
            )

        object.__setattr__(
            self,
            "producer",
            producer,
        )

        object.__setattr__(
            self,
            "producer_version",
            producer_version,
        )

    @staticmethod
    def _normalize_required_text(
        value: str,
        *,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"ForensicProvenance {field_name} must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"ForensicProvenance {field_name} must not be empty."
            )

        return normalized