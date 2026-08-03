from __future__ import annotations

from app.domain.models.image_match_classification import (
    ImageMatchClassification,
)
from app.domain.models.logo_fingerprint_comparison import (
    LogoFingerprintComparison,
)
from app.domain.models.logo_match_classification import (
    LogoMatchClassification,
)
from app.domain.services.image_fingerprint_match_classifier import (
    ImageFingerprintMatchClassifier,
)


class LogoFingerprintMatchClassifier:
    """
    Classifica o grau de correspondência técnica entre logos.

    A classificação visual é delegada ao classificador de
    fingerprints de imagem, garantindo que os mesmos limites
    sejam utilizados nos dois módulos.

    A comparação do nome da empresa não altera diretamente
    esta classificação. Essa informação será utilizada em uma
    etapa posterior para construção de evidências e findings.

    Este componente não cria evidências e não define severidade.
    """

    def __init__(self) -> None:
        self._image_classifier = (
            ImageFingerprintMatchClassifier()
        )

    def classify(
        self,
        comparison: LogoFingerprintComparison,
    ) -> LogoMatchClassification:
        image_classification = (
            self._image_classifier.classify(
                comparison
            )
        )

        return self._convert_classification(
            image_classification
        )

    @staticmethod
    def _convert_classification(
        classification: ImageMatchClassification,
    ) -> LogoMatchClassification:
        return LogoMatchClassification(
            classification.value
        )