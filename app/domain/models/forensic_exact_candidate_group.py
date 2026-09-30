from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.models.forensic_exact_match_group import (
    ForensicExactMatchGroup,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ForensicExactCandidateGroup:
    """
    Representa um grupo de candidatos selecionado a partir de
    uma equivalência exata já conhecida por um índice.

    O grupo não materializa pares entre os elementos.

    Ele mantém a referência ao grupo de equivalência original e
    registra qual índice foi responsável por selecioná-lo.
    """

    source_index: str
    exact_group: ForensicExactMatchGroup

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_index,
            str,
        ):
            raise TypeError(
                "source_index deve ser uma string."
            )

        normalized_source_index = (
            self.source_index.strip()
        )

        if not normalized_source_index:
            raise ValueError(
                "source_index não pode ser vazio."
            )

        if not isinstance(
            self.exact_group,
            ForensicExactMatchGroup,
        ):
            raise TypeError(
                "exact_group deve ser um "
                "ForensicExactMatchGroup."
            )

        object.__setattr__(
            self,
            "source_index",
            normalized_source_index,
        )

    @property
    def key_type(self) -> str:
        return (
            self.exact_group.key_type
        )

    @property
    def key_value(self) -> str:
        return (
            self.exact_group.key_value
        )

    @property
    def element_ids(
        self,
    ) -> tuple[UUID, ...]:
        return (
            self.exact_group.element_ids
        )

    @property
    def document_ids(
        self,
    ) -> tuple[UUID, ...]:
        return (
            self.exact_group.document_ids
        )

    @property
    def element_count(self) -> int:
        return (
            self.exact_group.element_count
        )

    @property
    def document_count(self) -> int:
        return (
            self.exact_group.document_count
        )

    @property
    def represented_pairwise_relations(
        self,
    ) -> int:
        return (
            self.exact_group
            .pairwise_relations
        )

    @property
    def represented_cross_document_relations(
        self,
    ) -> int:
        return (
            self.exact_group
            .cross_document_pairwise_relations
        )