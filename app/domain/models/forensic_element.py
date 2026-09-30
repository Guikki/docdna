from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID, uuid4

from app.domain.models.forensic_element_type import (
    ForensicElementType,
)
from app.domain.models.forensic_provenance import (
    ForensicProvenance,
)


@dataclass(frozen=True, slots=True)
class ForensicElement:
    element_type: ForensicElementType
    provenance: ForensicProvenance

    subtype: str | None = None
    value: str | None = None
    content_ref: str | None = None

    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    element_id: UUID = field(
        default_factory=uuid4
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.element_type,
            ForensicElementType,
        ):
            raise TypeError(
                "ForensicElement element_type must be "
                "a ForensicElementType."
            )

        if not isinstance(
            self.provenance,
            ForensicProvenance,
        ):
            raise TypeError(
                "ForensicElement provenance must be "
                "a ForensicProvenance."
            )

        if not isinstance(self.element_id, UUID):
            raise TypeError(
                "ForensicElement element_id must be a UUID."
            )

        subtype = self._normalize_optional_text(
            self.subtype,
            field_name="subtype",
        )

        value = self._normalize_optional_text(
            self.value,
            field_name="value",
            preserve_whitespace=True,
        )

        content_ref = self._normalize_optional_text(
            self.content_ref,
            field_name="content_ref",
        )

        if not isinstance(self.metadata, Mapping):
            raise TypeError(
                "ForensicElement metadata must be a mapping."
            )

        metadata_copy = dict(self.metadata)

        if (
            value is None
            and content_ref is None
            and not metadata_copy
        ):
            raise ValueError(
                "ForensicElement must contain value, "
                "content_ref or metadata."
            )

        object.__setattr__(
            self,
            "subtype",
            subtype,
        )

        object.__setattr__(
            self,
            "value",
            value,
        )

        object.__setattr__(
            self,
            "content_ref",
            content_ref,
        )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(metadata_copy),
        )

    @property
    def document_id(self) -> UUID:
        return self.provenance.document_id

    @property
    def page_number(self) -> int | None:
        return self.provenance.page_number

    @property
    def parent_element_id(self) -> UUID | None:
        return self.provenance.parent_element_id

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
        *,
        field_name: str,
        preserve_whitespace: bool = False,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                f"ForensicElement {field_name} "
                "must be a string or None."
            )

        if not value.strip():
            return None

        if preserve_whitespace:
            return value

        return value.strip()