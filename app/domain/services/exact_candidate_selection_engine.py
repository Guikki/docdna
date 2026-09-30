from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.forensic_exact_candidate_group import (
    ForensicExactCandidateGroup,
)
from app.domain.models.forensic_exact_match_group import (
    ForensicExactMatchGroup,
)
from app.domain.services.forensic_index_registry import (
    ForensicIndexRegistry,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ExactCandidateSelectionStats:
    """
    Resume o trabalho realizado pela seleção de candidatos exatos.

    As relações representadas são calculadas matematicamente.
    Nenhum objeto de par precisa ser criado para obter essa métrica.
    """

    sources_used: int
    candidate_groups: int
    unique_elements: int
    unique_documents: int
    represented_cross_document_relations: int


@dataclass(
    frozen=True,
    slots=True,
)
class ExactCandidateSelectionResult:
    """
    Resultado imutável de uma execução do seletor de candidatos.
    """

    groups: tuple[
        ForensicExactCandidateGroup,
        ...
    ]
    stats: ExactCandidateSelectionStats


class ExactCandidateSelectionEngine:
    """
    Seleciona grupos de candidatos produzidos por índices de
    equivalência exata.

    Esta camada não compara elementos e não produz findings.

    Sua responsabilidade é reduzir o espaço de busca, entregando
    somente grupos que justificam uma etapa analítica posterior.
    """

    def select(
        self,
        *,
        registry: ForensicIndexRegistry,
        index_names: list[str]
        | tuple[str, ...],
        cross_document_only: bool = True,
    ) -> ExactCandidateSelectionResult:
        if not isinstance(
            registry,
            ForensicIndexRegistry,
        ):
            raise TypeError(
                "registry deve ser um "
                "ForensicIndexRegistry."
            )

        if not isinstance(
            index_names,
            (list, tuple),
        ):
            raise TypeError(
                "index_names deve ser uma "
                "lista ou tupla."
            )

        canonical_names = {
            name.casefold(): name
            for name
            in registry.index_names()
        }

        requested_names = (
            self._normalize_requested_names(
                index_names
            )
        )

        candidate_groups: list[
            ForensicExactCandidateGroup
        ] = []

        for requested_name in (
            requested_names
        ):
            canonical_name = (
                canonical_names.get(
                    requested_name.casefold()
                )
            )

            if canonical_name is None:
                raise ValueError(
                    "Índice não registrado: "
                    f"{requested_name}."
                )

            index = registry.get_index(
                canonical_name
            )

            duplicate_groups = getattr(
                index,
                "duplicate_groups",
                None,
            )

            if not callable(
                duplicate_groups
            ):
                raise TypeError(
                    "O índice "
                    f"{canonical_name} "
                    "não oferece seleção por "
                    "grupos exatos."
                )

            groups = duplicate_groups(
                cross_document_only=(
                    cross_document_only
                )
            )

            for group in groups:
                if not isinstance(
                    group,
                    ForensicExactMatchGroup,
                ):
                    raise TypeError(
                        "duplicate_groups deve "
                        "retornar somente "
                        "ForensicExactMatchGroup."
                    )

                candidate_groups.append(
                    ForensicExactCandidateGroup(
                        source_index=(
                            canonical_name
                        ),
                        exact_group=group,
                    )
                )

        groups_tuple = tuple(
            candidate_groups
        )

        return ExactCandidateSelectionResult(
            groups=groups_tuple,
            stats=self._build_stats(
                groups_tuple
            ),
        )

    @staticmethod
    def _normalize_requested_names(
        index_names: list[str]
        | tuple[str, ...],
    ) -> tuple[str, ...]:
        """
        Normaliza os nomes solicitados e elimina repetições sem
        alterar a ordem da primeira ocorrência.
        """
        result: list[str] = []
        seen: set[str] = set()

        for name in index_names:
            if not isinstance(
                name,
                str,
            ):
                raise TypeError(
                    "Cada nome de índice deve "
                    "ser uma string."
                )

            normalized = name.strip()

            if not normalized:
                raise ValueError(
                    "O nome do índice não pode "
                    "ser vazio."
                )

            key = normalized.casefold()

            if key in seen:
                continue

            seen.add(
                key
            )

            result.append(
                normalized
            )

        return tuple(
            result
        )

    @staticmethod
    def _build_stats(
        groups: tuple[
            ForensicExactCandidateGroup,
            ...
        ],
    ) -> ExactCandidateSelectionStats:
        source_names = {
            group.source_index.casefold()
            for group in groups
        }

        element_ids = {
            element_id
            for group in groups
            for element_id
            in group.element_ids
        }

        document_ids = {
            document_id
            for group in groups
            for document_id
            in group.document_ids
        }

        represented_relations = sum(
            group
            .represented_cross_document_relations
            for group in groups
        )

        return ExactCandidateSelectionStats(
            sources_used=len(
                source_names
            ),
            candidate_groups=len(
                groups
            ),
            unique_elements=len(
                element_ids
            ),
            unique_documents=len(
                document_ids
            ),
            represented_cross_document_relations=(
                represented_relations
            ),
        )