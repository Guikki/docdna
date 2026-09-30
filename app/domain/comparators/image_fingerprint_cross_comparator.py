from __future__ import annotations

from typing import Any

from app.domain.comparators.base_comparator import (
    BaseComparator,
)
from app.domain.comparators.image_fingerprint_comparator import (
    ImageFingerprintComparator,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
)
from app.domain.models.image_fingerprint_candidate_selection import (
    ImageFingerprintCandidateSelectionStats,
)
from app.domain.services.image_fingerprint_candidate_selector import (
    ImageFingerprintCandidateSelector,
)
from app.domain.services.image_fingerprint_finding_builder import (
    ImageFingerprintFindingBuilder,
)


class ImageFingerprintCrossComparator(
    BaseComparator
):
    """
    Executa a comparação cruzada dos fingerprints de imagem
    pertencentes a documentos distintos.

    O componente trabalha em duas etapas:

    1. seleção dos pares candidatos;
    2. comparação técnica apenas dos candidatos selecionados.

    A seleção evita a materialização do produto cartesiano global
    entre todas as imagens dos documentos.

    Este componente não calcula hashes, não classifica fraude e
    não define regras de severidade.
    """

    def __init__(
        self,
        candidate_selector: (
            ImageFingerprintCandidateSelector
            | None
        ) = None,
        image_comparator: (
            ImageFingerprintComparator
            | None
        ) = None,
        finding_builder: (
            ImageFingerprintFindingBuilder
            | None
        ) = None,
    ) -> None:
        self._candidate_selector = (
            candidate_selector
            or ImageFingerprintCandidateSelector()
        )

        self._image_comparator = (
            image_comparator
            or ImageFingerprintComparator()
        )

        self._finding_builder = (
            finding_builder
            or ImageFingerprintFindingBuilder()
        )

        self._selection_stats: (
            ImageFingerprintCandidateSelectionStats
            | None
        ) = None

    @property
    def selection_stats(
        self,
    ) -> (
        ImageFingerprintCandidateSelectionStats
        | None
    ):
        """
        Expõe as métricas da seleção de candidatos da última
        execução.

        Esse dado será utilizado posteriormente pela camada de
        observabilidade para medir a redução real do espaço de
        comparação.
        """
        return self._selection_stats

    def compare(
        self,
        analyses: list[
            dict[str, Any]
        ],
    ) -> list[
        CrossValidationFinding
    ]:
        selection = (
            self._candidate_selector.select(
                analyses
            )
        )

        self._selection_stats = (
            selection.stats
        )

        findings: list[
            CrossValidationFinding
        ] = []

        for pair in selection.pairs:
            comparison = (
                self._image_comparator.compare(
                    pair.first_image,
                    pair.second_image,
                )
            )

            pair_findings = (
                self._finding_builder.build(
                    pair=pair,
                    comparison=comparison,
                    comparator=(
                        self.__class__.__name__
                    ),
                )
            )

            findings.extend(
                pair_findings
            )

        return findings