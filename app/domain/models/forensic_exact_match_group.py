from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import comb
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ForensicExactMatchGroup:
    """
    Representa um grupo de elementos que compartilham
    uma mesma chave determinística.

    Um grupo substitui a necessidade de materializar
    todos os pares possíveis entre seus membros.
    """

    key_type: str
    key_value: str
    element_ids: tuple[UUID, ...]
    document_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        key_type = self._normalize_required_text(
            self.key_type,
            field_name="key_type",
        )

        key_value = self._normalize_required_text(
            self.key_value,
            field_name="key_value",
        )

        if len(self.element_ids) < 2:
            raise ValueError(
                "ForensicExactMatchGroup must contain "
                "at least two elements."
            )

        if len(self.element_ids) != len(self.document_ids):
            raise ValueError(
                "element_ids and document_ids must have "
                "the same length."
            )

        if len(set(self.element_ids)) != len(self.element_ids):
            raise ValueError(
                "ForensicExactMatchGroup element_ids "
                "must be unique."
            )

        if not all(
            isinstance(element_id, UUID)
            for element_id in self.element_ids
        ):
            raise TypeError(
                "element_ids must contain only UUID values."
            )

        if not all(
            isinstance(document_id, UUID)
            for document_id in self.document_ids
        ):
            raise TypeError(
                "document_ids must contain only UUID values."
            )

        object.__setattr__(
            self,
            "key_type",
            key_type,
        )

        object.__setattr__(
            self,
            "key_value",
            key_value,
        )

    @property
    def element_count(self) -> int:
        return len(self.element_ids)

    @property
    def document_count(self) -> int:
        return len(set(self.document_ids))

    @property
    def is_cross_document(self) -> bool:
        return self.document_count >= 2

    @property
    def pairwise_relations(self) -> int:
        """
        Quantos pares seriam necessários caso este grupo
        fosse materializado de maneira tradicional.
        """
        return comb(
            self.element_count,
            2,
        )

    @property
    def cross_document_pairwise_relations(self) -> int:
        """
        Quantos dos pares possíveis ligariam documentos
        diferentes.

        Pares internos ao mesmo documento não entram.
        """
        total = self.pairwise_relations

        counts_by_document = Counter(
            self.document_ids
        )

        same_document_pairs = sum(
            comb(count, 2)
            for count in counts_by_document.values()
            if count >= 2
        )

        return total - same_document_pairs

    @staticmethod
    def _normalize_required_text(
        value: str,
        *,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty."
            )

        return normalized