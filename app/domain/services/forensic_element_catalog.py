from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from app.domain.models.forensic_data_layer import (
    ForensicDataLayer,
)
from app.domain.models.forensic_element import (
    ForensicElement,
)
from app.domain.models.forensic_element_type import (
    ForensicElementType,
)


@dataclass(frozen=True, slots=True)
class ForensicElementCatalogStats:
    total_elements: int
    document_count: int

    by_type: Mapping[ForensicElementType, int]
    by_subtype: Mapping[str, int]
    by_layer: Mapping[ForensicDataLayer, int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "by_type",
            MappingProxyType(dict(self.by_type)),
        )

        object.__setattr__(
            self,
            "by_subtype",
            MappingProxyType(dict(self.by_subtype)),
        )

        object.__setattr__(
            self,
            "by_layer",
            MappingProxyType(dict(self.by_layer)),
        )


class ForensicElementCatalog:
    """
    Catálogo em memória dos elementos forenses conhecidos.

    Responsabilidades:

    - preservar cada ForensicElement pelo seu element_id;
    - permitir acesso eficiente por documento;
    - permitir acesso eficiente por tipo;
    - permitir acesso eficiente por subtipo;
    - permitir acesso eficiente por camada de dados;
    - preservar relações de proveniência pai -> filhos;
    - impedir colisões silenciosas de IDs.

    O catálogo não executa comparação nem classificação.
    Ele também não representa persistência definitiva.
    """

    def __init__(self) -> None:
        self._elements: dict[UUID, ForensicElement] = {}

        self._by_document: dict[
            UUID,
            list[UUID],
        ] = defaultdict(list)

        self._by_type: dict[
            ForensicElementType,
            list[UUID],
        ] = defaultdict(list)

        self._by_subtype: dict[
            str,
            list[UUID],
        ] = defaultdict(list)

        self._by_layer: dict[
            ForensicDataLayer,
            list[UUID],
        ] = defaultdict(list)

        self._by_parent: dict[
            UUID,
            list[UUID],
        ] = defaultdict(list)

    def add(
        self,
        element: ForensicElement,
    ) -> bool:
        """
        Registra um elemento.

        Retorna True quando o elemento é novo.

        Se o mesmo element_id já existir com exatamente o mesmo
        conteúdo, a operação é idempotente e retorna False.

        Se o mesmo ID estiver associado a outro conteúdo, uma
        exceção é lançada para impedir corrupção silenciosa.
        """
        if not isinstance(element, ForensicElement):
            raise TypeError(
                "element must be a ForensicElement."
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

        self._validate_lineage(element)

        self._elements[element.element_id] = element

        self._by_document[
            element.document_id
        ].append(
            element.element_id
        )

        self._by_type[
            element.element_type
        ].append(
            element.element_id
        )

        if element.subtype is not None:
            self._by_subtype[
                element.subtype
            ].append(
                element.element_id
            )

        self._by_layer[
            element.provenance.layer
        ].append(
            element.element_id
        )

        if element.parent_element_id is not None:
            self._by_parent[
                element.parent_element_id
            ].append(
                element.element_id
            )

        return True

    def add_many(
        self,
        elements: list[ForensicElement]
        | tuple[ForensicElement, ...],
    ) -> int:
        if not isinstance(elements, (list, tuple)):
            raise TypeError(
                "elements must be a list or tuple."
            )

        added = 0

        for element in elements:
            if self.add(element):
                added += 1

        return added

    def get(
        self,
        element_id: UUID,
    ) -> ForensicElement | None:
        if not isinstance(element_id, UUID):
            raise TypeError(
                "element_id must be a UUID."
            )

        return self._elements.get(element_id)

    def all(
        self,
    ) -> tuple[ForensicElement, ...]:
        return tuple(
            self._elements.values()
        )

    def by_document(
        self,
        document_id: UUID,
    ) -> tuple[ForensicElement, ...]:
        if not isinstance(document_id, UUID):
            raise TypeError(
                "document_id must be a UUID."
            )

        return self._resolve(
            self._by_document.get(
                document_id,
                [],
            )
        )

    def by_type(
        self,
        element_type: ForensicElementType,
    ) -> tuple[ForensicElement, ...]:
        if not isinstance(
            element_type,
            ForensicElementType,
        ):
            raise TypeError(
                "element_type must be a "
                "ForensicElementType."
            )

        return self._resolve(
            self._by_type.get(
                element_type,
                [],
            )
        )

    def by_subtype(
        self,
        subtype: str,
    ) -> tuple[ForensicElement, ...]:
        if not isinstance(subtype, str):
            raise TypeError(
                "subtype must be a string."
            )

        normalized = subtype.strip()

        if not normalized:
            raise ValueError(
                "subtype must not be empty."
            )

        return self._resolve(
            self._by_subtype.get(
                normalized,
                [],
            )
        )

    def by_layer(
        self,
        layer: ForensicDataLayer,
    ) -> tuple[ForensicElement, ...]:
        if not isinstance(
            layer,
            ForensicDataLayer,
        ):
            raise TypeError(
                "layer must be a ForensicDataLayer."
            )

        return self._resolve(
            self._by_layer.get(
                layer,
                [],
            )
        )

    def children_of(
        self,
        parent_element_id: UUID,
    ) -> tuple[ForensicElement, ...]:
        if not isinstance(
            parent_element_id,
            UUID,
        ):
            raise TypeError(
                "parent_element_id must be a UUID."
            )

        return self._resolve(
            self._by_parent.get(
                parent_element_id,
                [],
            )
        )

    def stats(
        self,
    ) -> ForensicElementCatalogStats:
        by_type = {
            element_type: len(element_ids)
            for element_type, element_ids
            in self._by_type.items()
        }

        by_subtype = {
            subtype: len(element_ids)
            for subtype, element_ids
            in self._by_subtype.items()
        }

        by_layer = {
            layer: len(element_ids)
            for layer, element_ids
            in self._by_layer.items()
        }

        return ForensicElementCatalogStats(
            total_elements=len(self._elements),
            document_count=len(self._by_document),
            by_type=by_type,
            by_subtype=by_subtype,
            by_layer=by_layer,
        )

    def __len__(self) -> int:
        return len(self._elements)

    def _resolve(
        self,
        element_ids: list[UUID],
    ) -> tuple[ForensicElement, ...]:
        return tuple(
            self._elements[element_id]
            for element_id in element_ids
        )

    def _validate_lineage(
        self,
        element: ForensicElement,
    ) -> None:
        parent_id = element.parent_element_id

        if parent_id is not None:
            parent = self._elements.get(parent_id)

            if (
                parent is not None
                and parent.document_id
                != element.document_id
            ):
                raise ValueError(
                    "Parent and child ForensicElements "
                    "must belong to the same document."
                )

        existing_children = self._by_parent.get(
            element.element_id,
            [],
        )

        for child_id in existing_children:
            child = self._elements[child_id]

            if child.document_id != element.document_id:
                raise ValueError(
                    "Parent and child ForensicElements "
                    "must belong to the same document."
                )