from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class Sha256ForensicIndexStats:
    indexed_elements: int
    unique_hashes: int

    duplicate_hash_groups: int
    cross_document_groups: int

    elements_in_duplicate_groups: int
    elements_in_cross_document_groups: int

    represented_pairwise_relations: int
    represented_cross_document_pairwise_relations: int


class Sha256ForensicIndex:
    """
    Índice determinístico para elementos forenses SHA-256.

    O índice:

    - não altera o ForensicElement original;
    - não cria pares;
    - agrupa elementos pela chave SHA-256;
    - permite detectar repetições em O(1) médio por consulta;
    - pode representar milhares de relações por um único grupo.
    """

    SUBTYPE = "sha256"
    HASH_LENGTH = 64

    def __init__(self) -> None:
        self._elements: dict[
            UUID,
            ForensicElement,
        ] = {}

        self._hash_by_element_id: dict[
            UUID,
            str,
        ] = {}

        self._buckets: dict[
            str,
            list[UUID],
        ] = {}

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

        self._validate_element(element)

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

        hash_value = self._normalize_hash(
            element.value
        )

        self._elements[
            element.element_id
        ] = element

        self._hash_by_element_id[
            element.element_id
        ] = hash_value

        self._buckets.setdefault(
            hash_value,
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
        hash_value: str,
    ) -> tuple[ForensicElement, ...]:
        normalized = self._normalize_hash(
            hash_value
        )

        element_ids = self._buckets.get(
            normalized,
            [],
        )

        return tuple(
            self._elements[element_id]
            for element_id in element_ids
        )

    def duplicate_groups(
        self,
        *,
        cross_document_only: bool = False,
    ) -> tuple[ForensicExactMatchGroup, ...]:
        groups: list[
            ForensicExactMatchGroup
        ] = []

        for (
            hash_value,
            element_ids,
        ) in self._buckets.items():
            if len(element_ids) < 2:
                continue

            group = self._build_group(
                hash_value=hash_value,
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
    ) -> Sha256ForensicIndexStats:
        duplicate_groups = (
            self.duplicate_groups()
        )

        cross_document_groups = (
            self.duplicate_groups(
                cross_document_only=True,
            )
        )

        elements_in_duplicate_groups = sum(
            group.element_count
            for group in duplicate_groups
        )

        elements_in_cross_document_groups = sum(
            group.element_count
            for group in cross_document_groups
        )

        represented_pairwise_relations = sum(
            group.pairwise_relations
            for group in duplicate_groups
        )

        represented_cross_document_pairwise_relations = sum(
            group.cross_document_pairwise_relations
            for group in cross_document_groups
        )

        return Sha256ForensicIndexStats(
            indexed_elements=len(
                self._elements
            ),
            unique_hashes=len(
                self._buckets
            ),
            duplicate_hash_groups=len(
                duplicate_groups
            ),
            cross_document_groups=len(
                cross_document_groups
            ),
            elements_in_duplicate_groups=(
                elements_in_duplicate_groups
            ),
            elements_in_cross_document_groups=(
                elements_in_cross_document_groups
            ),
            represented_pairwise_relations=(
                represented_pairwise_relations
            ),
            represented_cross_document_pairwise_relations=(
                represented_cross_document_pairwise_relations
            ),
        )

    def __len__(self) -> int:
        return len(self._elements)

    def _build_group(
        self,
        *,
        hash_value: str,
        element_ids: list[UUID],
    ) -> ForensicExactMatchGroup:
        elements = tuple(
            self._elements[element_id]
            for element_id in element_ids
        )

        return ForensicExactMatchGroup(
            key_type=self.SUBTYPE,
            key_value=hash_value,
            element_ids=tuple(
                element.element_id
                for element in elements
            ),
            document_ids=tuple(
                element.document_id
                for element in elements
            ),
        )

    def _validate_element(
        self,
        element: ForensicElement,
    ) -> None:
        if (
            element.element_type
            is not ForensicElementType.HASH
        ):
            raise ValueError(
                "Sha256ForensicIndex accepts only "
                "HASH elements."
            )

        subtype = (
            element.subtype or ""
        ).strip().lower()

        if subtype != self.SUBTYPE:
            raise ValueError(
                "Sha256ForensicIndex accepts only "
                "sha256 elements."
            )

        self._normalize_hash(
            element.value
        )

    @classmethod
    def _normalize_hash(
        cls,
        value: str | None,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                "SHA-256 value must be a string."
            )

        normalized = value.strip().lower()

        if len(normalized) != cls.HASH_LENGTH:
            raise ValueError(
                "SHA-256 value must contain "
                "exactly 64 hexadecimal characters."
            )

        if not all(
            character in "0123456789abcdef"
            for character in normalized
        ):
            raise ValueError(
                "SHA-256 value must contain only "
                "hexadecimal characters."
            )

        return normalized