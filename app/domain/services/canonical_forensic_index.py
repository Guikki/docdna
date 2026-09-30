from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from app.domain.models.forensic_element import (
    ForensicElement,
)
from app.domain.models.forensic_element_type import (
    ForensicElementType,
)
from app.domain.models.forensic_exact_match_group import (
    ForensicExactMatchGroup,
)


Canonicalizer = Callable[
    [str],
    str,
]


@dataclass(frozen=True, slots=True)
class CanonicalForensicIndexStats:
    key_type: str
    element_type: ForensicElementType
    subtype: str

    indexed_elements: int
    unique_keys: int

    duplicate_groups: int
    cross_document_groups: int

    elements_in_duplicate_groups: int
    elements_in_cross_document_groups: int

    represented_pairwise_relations: int
    represented_cross_document_pairwise_relations: int


class CanonicalForensicIndex:
    """
    Índice determinístico baseado em valores canônicos.

    O índice não altera o dado original.

    O valor armazenado no ForensicElement permanece
    intacto, enquanto uma representação canônica é
    utilizada exclusivamente como chave de indexação.

    Exemplos possíveis:

    CPF:
        "123.456.789-00"
        -> "12345678900"

    nome:
        "BANCO PAN"
        -> "banco pan"

    barcode:
        valor bruto
        -> representação canônica definida pelo domínio

    O índice não materializa pares.
    """

    def __init__(
        self,
        *,
        key_type: str,
        element_type: ForensicElementType,
        subtype: str,
        canonicalizer: Canonicalizer,
    ) -> None:
        self._key_type = (
            self._normalize_required_text(
                key_type,
                field_name="key_type",
            )
        )

        if not isinstance(
            element_type,
            ForensicElementType,
        ):
            raise TypeError(
                "element_type must be a "
                "ForensicElementType."
            )

        self._element_type = element_type

        self._subtype = (
            self._normalize_required_text(
                subtype,
                field_name="subtype",
            )
        )

        self._subtype_key = (
            self._subtype.casefold()
        )

        if not callable(canonicalizer):
            raise TypeError(
                "canonicalizer must be callable."
            )

        self._canonicalizer = canonicalizer

        self._elements: dict[
            UUID,
            ForensicElement,
        ] = {}

        self._canonical_by_element_id: dict[
            UUID,
            str,
        ] = {}

        self._buckets: dict[
            str,
            list[UUID],
        ] = {}

    @property
    def key_type(self) -> str:
        return self._key_type

    @property
    def element_type(
        self,
    ) -> ForensicElementType:
        return self._element_type

    @property
    def subtype(self) -> str:
        return self._subtype

    def add(
        self,
        element: ForensicElement,
    ) -> bool:
        if not isinstance(
            element,
            ForensicElement,
        ):
            raise TypeError(
                "element must be a ForensicElement."
            )

        self._validate_element(
            element
        )

        existing = self._elements.get(
            element.element_id
        )

        if existing is not None:
            if existing == element:
                return False

            raise ValueError(
                "A different ForensicElement already exists "
                f"with element_id {element.element_id}."
            )

        canonical_value = (
            self._canonicalize(
                element.value
            )
        )

        self._elements[
            element.element_id
        ] = element

        self._canonical_by_element_id[
            element.element_id
        ] = canonical_value

        self._buckets.setdefault(
            canonical_value,
            [],
        ).append(
            element.element_id
        )

        return True

    def add_many(
        self,
        elements: list[ForensicElement]
        | tuple[ForensicElement, ...],
    ) -> int:
        if not isinstance(
            elements,
            (list, tuple),
        ):
            raise TypeError(
                "elements must be a list or tuple."
            )

        added = 0

        for element in elements:
            if self.add(element):
                added += 1

        return added

    def lookup(
        self,
        value: str,
    ) -> tuple[ForensicElement, ...]:
        canonical_value = (
            self._canonicalize(value)
        )

        element_ids = (
            self._buckets.get(
                canonical_value,
                [],
            )
        )

        return tuple(
            self._elements[element_id]
            for element_id in element_ids
        )

    def canonical_value_of(
        self,
        element_id: UUID,
    ) -> str | None:
        if not isinstance(
            element_id,
            UUID,
        ):
            raise TypeError(
                "element_id must be a UUID."
            )

        return (
            self._canonical_by_element_id.get(
                element_id
            )
        )

    def duplicate_groups(
        self,
        *,
        cross_document_only: bool = False,
    ) -> tuple[
        ForensicExactMatchGroup,
        ...
    ]:
        groups: list[
            ForensicExactMatchGroup
        ] = []

        for (
            canonical_value,
            element_ids,
        ) in self._buckets.items():
            if len(element_ids) < 2:
                continue

            group = self._build_group(
                canonical_value=canonical_value,
                element_ids=element_ids,
            )

            if (
                cross_document_only
                and not group.is_cross_document
            ):
                continue

            groups.append(group)

        return tuple(groups)

    def stats(
        self,
    ) -> CanonicalForensicIndexStats:
        duplicate_groups = (
            self.duplicate_groups()
        )

        cross_document_groups = (
            self.duplicate_groups(
                cross_document_only=True,
            )
        )

        return CanonicalForensicIndexStats(
            key_type=self._key_type,
            element_type=self._element_type,
            subtype=self._subtype,
            indexed_elements=len(
                self._elements
            ),
            unique_keys=len(
                self._buckets
            ),
            duplicate_groups=len(
                duplicate_groups
            ),
            cross_document_groups=len(
                cross_document_groups
            ),
            elements_in_duplicate_groups=sum(
                group.element_count
                for group in duplicate_groups
            ),
            elements_in_cross_document_groups=sum(
                group.element_count
                for group in cross_document_groups
            ),
            represented_pairwise_relations=sum(
                group.pairwise_relations
                for group in duplicate_groups
            ),
            represented_cross_document_pairwise_relations=sum(
                group.cross_document_pairwise_relations
                for group in cross_document_groups
            ),
        )

    def __len__(self) -> int:
        return len(
            self._elements
        )

    def _validate_element(
        self,
        element: ForensicElement,
    ) -> None:
        if (
            element.element_type
            is not self._element_type
        ):
            raise ValueError(
                "CanonicalForensicIndex received "
                "an incompatible element_type."
            )

        element_subtype = (
            element.subtype or ""
        ).strip().casefold()

        if (
            element_subtype
            != self._subtype_key
        ):
            raise ValueError(
                "CanonicalForensicIndex received "
                "an incompatible subtype."
            )

        self._canonicalize(
            element.value
        )

    def _canonicalize(
        self,
        value: str | None,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "Indexed element value "
                "must be a string."
            )

        canonical_value = (
            self._canonicalizer(value)
        )

        if not isinstance(
            canonical_value,
            str,
        ):
            raise TypeError(
                "canonicalizer must return a string."
            )

        if not canonical_value.strip():
            raise ValueError(
                "canonicalizer must return "
                "a non-empty string."
            )

        return canonical_value

    def _build_group(
        self,
        *,
        canonical_value: str,
        element_ids: list[UUID],
    ) -> ForensicExactMatchGroup:
        elements = tuple(
            self._elements[element_id]
            for element_id in element_ids
        )

        return ForensicExactMatchGroup(
            key_type=self._key_type,
            key_value=canonical_value,
            element_ids=tuple(
                element.element_id
                for element in elements
            ),
            document_ids=tuple(
                element.document_id
                for element in elements
            ),
        )

    @staticmethod
    def _normalize_required_text(
        value: str,
        *,
        field_name: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string."
            )

        normalized = (
            value.strip()
        )

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty."
            )

        return normalized