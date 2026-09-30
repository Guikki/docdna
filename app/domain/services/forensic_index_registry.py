from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Protocol
from uuid import UUID

from app.domain.models.forensic_element import (
    ForensicElement,
)
from app.domain.models.forensic_element_type import (
    ForensicElementType,
)
from app.domain.services.forensic_element_catalog import (
    ForensicElementCatalog,
)


class ForensicElementIndex(Protocol):
    """
    Contrato mínimo de um índice de elementos forenses.

    O Registry não precisa conhecer a implementação concreta
    do índice. Ele precisa apenas ser capaz de enviar um
    ForensicElement para indexação.
    """

    def add(
        self,
        element: ForensicElement,
    ) -> bool:
        ...


@dataclass(frozen=True, slots=True)
class ForensicIndexRegistration:
    name: str
    element_type: ForensicElementType
    subtype: str
    index: ForensicElementIndex

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError(
                "ForensicIndexRegistration name must be a string."
            )

        normalized_name = self.name.strip()

        if not normalized_name:
            raise ValueError(
                "ForensicIndexRegistration name must not be empty."
            )

        if not isinstance(
            self.element_type,
            ForensicElementType,
        ):
            raise TypeError(
                "ForensicIndexRegistration element_type must be "
                "a ForensicElementType."
            )

        if not isinstance(self.subtype, str):
            raise TypeError(
                "ForensicIndexRegistration subtype must be a string."
            )

        normalized_subtype = self.subtype.strip()

        if not normalized_subtype:
            raise ValueError(
                "ForensicIndexRegistration subtype must not be empty."
            )

        add_method = getattr(
            self.index,
            "add",
            None,
        )

        if not callable(add_method):
            raise TypeError(
                "Registered forensic index must expose "
                "an add(element) method."
            )

        object.__setattr__(
            self,
            "name",
            normalized_name,
        )

        object.__setattr__(
            self,
            "subtype",
            normalized_subtype,
        )

    @property
    def subtype_key(self) -> str:
        return self.subtype.casefold()


@dataclass(frozen=True, slots=True)
class ForensicIndexingResult:
    element_id: UUID
    matched_indexes: tuple[str, ...]
    newly_indexed_indexes: tuple[str, ...]

    @property
    def matched_count(self) -> int:
        return len(self.matched_indexes)

    @property
    def newly_indexed_count(self) -> int:
        return len(
            self.newly_indexed_indexes
        )

    @property
    def was_indexed(self) -> bool:
        return bool(
            self.matched_indexes
        )


@dataclass(frozen=True, slots=True)
class ForensicIndexRegistryStats:
    registered_indexes: int
    indexed_elements: int
    index_memberships: int
    by_index: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "by_index",
            MappingProxyType(
                dict(self.by_index)
            ),
        )


class ForensicIndexRegistry:
    """
    Coordena índices especializados de elementos forenses.

    Responsabilidades:

    - registrar índices;
    - descobrir quais índices aceitam determinado elemento;
    - permitir que um mesmo elemento participe de vários índices;
    - manter rastreabilidade das associações elemento -> índice;
    - indexar um catálogo inteiro sem alterar seus dados.

    O Registry não:

    - remove elementos;
    - modifica valores;
    - compara elementos;
    - produz findings;
    - decide fraude.
    """

    def __init__(self) -> None:
        self._registrations: dict[
            str,
            ForensicIndexRegistration,
        ] = {}

        self._memberships: dict[
            UUID,
            list[str],
        ] = {}

    def register(
        self,
        *,
        name: str,
        element_type: ForensicElementType,
        subtype: str,
        index: ForensicElementIndex,
    ) -> None:
        registration = ForensicIndexRegistration(
            name=name,
            element_type=element_type,
            subtype=subtype,
            index=index,
        )

        registration_key = (
            self._registration_key(
                registration.name
            )
        )

        if (
            registration_key
            in self._registrations
        ):
            raise ValueError(
                "A forensic index with this name "
                "is already registered."
            )

        self._registrations[
            registration_key
        ] = registration

    def get_index(
        self,
        name: str,
    ) -> ForensicElementIndex | None:
        registration = (
            self._get_registration(name)
        )

        if registration is None:
            return None

        return registration.index

    def index_names(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            registration.name
            for registration
            in self._registrations.values()
        )

    def index_element(
        self,
        element: ForensicElement,
    ) -> ForensicIndexingResult:
        if not isinstance(
            element,
            ForensicElement,
        ):
            raise TypeError(
                "element must be a ForensicElement."
            )

        matched_indexes: list[str] = []
        newly_indexed_indexes: list[str] = []

        for registration in (
            self._registrations.values()
        ):
            if not self._matches(
                registration=registration,
                element=element,
            ):
                continue

            matched_indexes.append(
                registration.name
            )

            added = registration.index.add(
                element
            )

            if not isinstance(
                added,
                bool,
            ):
                raise TypeError(
                    "Forensic index add(element) "
                    "must return bool."
                )

            self._register_membership(
                element_id=element.element_id,
                index_name=registration.name,
            )

            if added:
                newly_indexed_indexes.append(
                    registration.name
                )

        return ForensicIndexingResult(
            element_id=element.element_id,
            matched_indexes=tuple(
                matched_indexes
            ),
            newly_indexed_indexes=tuple(
                newly_indexed_indexes
            ),
        )

    def index_many(
        self,
        elements: list[ForensicElement]
        | tuple[ForensicElement, ...],
    ) -> tuple[
        ForensicIndexingResult,
        ...
    ]:
        if not isinstance(
            elements,
            (list, tuple),
        ):
            raise TypeError(
                "elements must be a list or tuple."
            )

        return tuple(
            self.index_element(element)
            for element in elements
        )

    def index_catalog(
        self,
        catalog: ForensicElementCatalog,
    ) -> tuple[
        ForensicIndexingResult,
        ...
    ]:
        if not isinstance(
            catalog,
            ForensicElementCatalog,
        ):
            raise TypeError(
                "catalog must be a "
                "ForensicElementCatalog."
            )

        return self.index_many(
            catalog.all()
        )

    def memberships(
        self,
        element_id: UUID,
    ) -> tuple[str, ...]:
        if not isinstance(
            element_id,
            UUID,
        ):
            raise TypeError(
                "element_id must be a UUID."
            )

        return tuple(
            self._memberships.get(
                element_id,
                [],
            )
        )

    def stats(
        self,
    ) -> ForensicIndexRegistryStats:
        by_index = {
            registration.name: 0
            for registration
            in self._registrations.values()
        }

        index_memberships = 0

        for memberships in (
            self._memberships.values()
        ):
            for index_name in memberships:
                by_index[index_name] += 1
                index_memberships += 1

        return ForensicIndexRegistryStats(
            registered_indexes=len(
                self._registrations
            ),
            indexed_elements=len(
                self._memberships
            ),
            index_memberships=(
                index_memberships
            ),
            by_index=by_index,
        )

    def __len__(self) -> int:
        return len(
            self._registrations
        )

    def _matches(
        self,
        *,
        registration: ForensicIndexRegistration,
        element: ForensicElement,
    ) -> bool:
        if (
            element.element_type
            is not registration.element_type
        ):
            return False

        element_subtype = (
            element.subtype or ""
        ).strip().casefold()

        return (
            element_subtype
            == registration.subtype_key
        )

    def _register_membership(
        self,
        *,
        element_id: UUID,
        index_name: str,
    ) -> None:
        memberships = (
            self._memberships.setdefault(
                element_id,
                [],
            )
        )

        if index_name not in memberships:
            memberships.append(
                index_name
            )

    def _get_registration(
        self,
        name: str,
    ) -> ForensicIndexRegistration | None:
        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "name must be a string."
            )

        normalized = name.strip()

        if not normalized:
            raise ValueError(
                "name must not be empty."
            )

        return self._registrations.get(
            self._registration_key(
                normalized
            )
        )

    @staticmethod
    def _registration_key(
        name: str,
    ) -> str:
        return name.strip().casefold()