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
from app.domain.services.image_fingerprint_finding_builder import (
    ImageFingerprintFindingBuilder,
)
from app.domain.services.image_fingerprint_pair_generator import (
    ImageFingerprintPairGenerator,
)


class ImageFingerprintCrossComparator(BaseComparator):
    """
    Executa a comparação cruzada dos fingerprints de imagem
    pertencentes a documentos distintos.

    Este componente apenas orquestra:

    - geração dos pares;
    - comparação técnica dos fingerprints;
    - construção dos findings.

    Ele não calcula hashes, não classifica similaridade e não
    define regras de severidade.
    """

    def __init__(
        self,
        pair_generator: ImageFingerprintPairGenerator | None = None,
        image_comparator: ImageFingerprintComparator | None = None,
        finding_builder: ImageFingerprintFindingBuilder | None = None,
    ) -> None:
        self._pair_generator = (
            pair_generator
            or ImageFingerprintPairGenerator()
        )

        self._image_comparator = (
            image_comparator
            or ImageFingerprintComparator()
        )

        self._finding_builder = (
            finding_builder
            or ImageFingerprintFindingBuilder()
        )

    def compare(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[CrossValidationFinding]:
        pairs = self._pair_generator.generate(
            analyses
        )

        findings: list[CrossValidationFinding] = []

        for pair in pairs:
            comparison = self._image_comparator.compare(
                pair.first_image,
                pair.second_image,
            )

            pair_findings = self._finding_builder.build(
                pair=pair,
                comparison=comparison,
                comparator=self.__class__.__name__,
            )

            findings.extend(pair_findings)

        return findings