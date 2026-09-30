from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.models.barcode_numeric_line_candidate import (
    BarcodeNumericLineCandidateGroup,
    BarcodeNumericLineDocumentCandidate,
)
from app.domain.models.forensic_element_type import (
    ForensicElementType,
)
from app.domain.services.exact_candidate_selection_engine import (
    ExactCandidateSelectionResult,
)
from app.domain.services.forensic_canonicalizers import (
    canonicalize_digits,
)
from app.domain.services.forensic_element_catalog import (
    ForensicElementCatalog,
)


@dataclass(
    frozen=True,
    slots=True,
)
class BarcodeNumericLineCandidateSelectionStats:
    """
    Resume a seleção relacional entre códigos de barras repetidos
    e linhas numéricas encontradas nos documentos relacionados.
    """

    source_groups_considered: int
    candidate_groups: int
    candidate_documents: int
    barcode_elements: int
    numeric_line_elements: int


@dataclass(
    frozen=True,
    slots=True,
)
class BarcodeNumericLineCandidateSelectionResult:
    """
    Resultado imutável da seleção de candidatos.
    """

    groups: tuple[
        BarcodeNumericLineCandidateGroup,
        ...
    ]
    stats: (
        BarcodeNumericLineCandidateSelectionStats
    )


class BarcodeNumericLineCandidateSelector:
    """
    Seleciona grupos em que documentos compartilham um código
    de barras exato, mas possuem conjuntos diferentes de linhas
    numéricas normalizadas.

    Nenhum par entre documentos é criado.

    A seleção trabalha sobre grupos previamente produzidos pelos
    índices de equivalência exata.
    """

    NORMALIZED_LINE_SUBTYPE = (
        "normalized_numeric_line"
    )

    def select(
        self,
        *,
        catalog: ForensicElementCatalog,
        exact_candidates: (
            ExactCandidateSelectionResult
        ),
        source_indexes: list[str]
        | tuple[str, ...],
    ) -> (
        BarcodeNumericLineCandidateSelectionResult
    ):
        if not isinstance(
            catalog,
            ForensicElementCatalog,
        ):
            raise TypeError(
                "catalog deve ser um "
                "ForensicElementCatalog."
            )

        if not isinstance(
            exact_candidates,
            ExactCandidateSelectionResult,
        ):
            raise TypeError(
                "exact_candidates deve ser um "
                "ExactCandidateSelectionResult."
            )

        normalized_sources = (
            self._normalize_source_indexes(
                source_indexes
            )
        )

        groups: list[
            BarcodeNumericLineCandidateGroup
        ] = []

        source_groups_considered = 0

        for exact_group in (
            exact_candidates.groups
        ):
            if (
                exact_group
                .source_index
                .casefold()
                not in normalized_sources
            ):
                continue

            source_groups_considered += 1

            document_candidates = (
                self._build_document_candidates(
                    catalog=catalog,
                    exact_group=exact_group,
                )
            )

            if not self._has_divergence(
                document_candidates
            ):
                continue

            groups.append(
                BarcodeNumericLineCandidateGroup(
                    source_index=(
                        exact_group.source_index
                    ),
                    barcode_key=(
                        exact_group.key_value
                    ),
                    documents=(
                        document_candidates
                    ),
                    represented_barcode_relations=(
                        exact_group
                        .represented_cross_document_relations
                    ),
                )
            )

        groups_tuple = tuple(
            groups
        )

        return (
            BarcodeNumericLineCandidateSelectionResult(
                groups=groups_tuple,
                stats=self._build_stats(
                    groups=groups_tuple,
                    source_groups_considered=(
                        source_groups_considered
                    ),
                ),
            )
        )

    def _build_document_candidates(
        self,
        *,
        catalog: ForensicElementCatalog,
        exact_group,
    ) -> tuple[
        BarcodeNumericLineDocumentCandidate,
        ...
    ]:
        barcode_ids_by_document: dict[
            UUID,
            list[UUID],
        ] = {}

        document_order: list[
            UUID
        ] = []

        for (
            element_id,
            document_id,
        ) in zip(
            exact_group.element_ids,
            exact_group.document_ids,
        ):
            if (
                document_id
                not in barcode_ids_by_document
            ):
                barcode_ids_by_document[
                    document_id
                ] = []

                document_order.append(
                    document_id
                )

            barcode_ids_by_document[
                document_id
            ].append(
                element_id
            )

        candidates: list[
            BarcodeNumericLineDocumentCandidate
        ] = []

        for document_id in (
            document_order
        ):
            (
                numeric_line_element_ids,
                numeric_line_values,
            ) = self._numeric_lines_for_document(
                catalog=catalog,
                document_id=document_id,
            )

            candidates.append(
                BarcodeNumericLineDocumentCandidate(
                    document_id=document_id,
                    barcode_element_ids=tuple(
                        barcode_ids_by_document[
                            document_id
                        ]
                    ),
                    numeric_line_element_ids=(
                        numeric_line_element_ids
                    ),
                    numeric_line_values=(
                        numeric_line_values
                    ),
                )
            )

        return tuple(
            candidates
        )

    def _numeric_lines_for_document(
        self,
        *,
        catalog: ForensicElementCatalog,
        document_id: UUID,
    ) -> tuple[
        tuple[UUID, ...],
        tuple[str, ...],
    ]:
        element_ids: list[
            UUID
        ] = []

        values: list[
            str
        ] = []

        seen_values: set[
            str
        ] = set()

        for element in (
            catalog.by_document(
                document_id
            )
        ):
            if (
                element.element_type
                is not
                ForensicElementType.NUMERIC_LINE
            ):
                continue

            if (
                element.subtype
                != self.NORMALIZED_LINE_SUBTYPE
            ):
                continue

            if (
                not isinstance(
                    element.value,
                    str,
                )
                or not element.value.strip()
            ):
                continue

            canonical_value = (
                canonicalize_digits(
                    element.value
                )
            )

            element_ids.append(
                element.element_id
            )

            if (
                canonical_value
                in seen_values
            ):
                continue

            seen_values.add(
                canonical_value
            )

            values.append(
                canonical_value
            )

        return (
            tuple(
                element_ids
            ),
            tuple(
                values
            ),
        )

    @staticmethod
    def _has_divergence(
        documents: tuple[
            BarcodeNumericLineDocumentCandidate,
            ...
        ],
    ) -> bool:
        signatures = {
            document.numeric_line_values
            for document
            in documents
            if document.has_numeric_lines
        }

        return (
            len(signatures) >= 2
        )

    @staticmethod
    def _normalize_source_indexes(
        source_indexes: list[str]
        | tuple[str, ...],
    ) -> set[str]:
        if not isinstance(
            source_indexes,
            (list, tuple),
        ):
            raise TypeError(
                "source_indexes deve ser uma "
                "lista ou tupla."
            )

        normalized: set[
            str
        ] = set()

        for source_index in (
            source_indexes
        ):
            if not isinstance(
                source_index,
                str,
            ):
                raise TypeError(
                    "Cada source_index deve "
                    "ser uma string."
                )

            value = (
                source_index.strip()
            )

            if not value:
                raise ValueError(
                    "source_index não pode "
                    "ser vazio."
                )

            normalized.add(
                value.casefold()
            )

        return normalized

    @staticmethod
    def _build_stats(
        *,
        groups: tuple[
            BarcodeNumericLineCandidateGroup,
            ...
        ],
        source_groups_considered: int,
    ) -> (
        BarcodeNumericLineCandidateSelectionStats
    ):
        document_ids = {
            document.document_id
            for group in groups
            for document
            in group.documents
        }

        barcode_element_ids = {
            element_id
            for group in groups
            for element_id
            in group.barcode_element_ids
        }

        numeric_line_element_ids = {
            element_id
            for group in groups
            for element_id
            in group.numeric_line_element_ids
        }

        return (
            BarcodeNumericLineCandidateSelectionStats(
                source_groups_considered=(
                    source_groups_considered
                ),
                candidate_groups=len(
                    groups
                ),
                candidate_documents=len(
                    document_ids
                ),
                barcode_elements=len(
                    barcode_element_ids
                ),
                numeric_line_elements=len(
                    numeric_line_element_ids
                ),
            )
        )