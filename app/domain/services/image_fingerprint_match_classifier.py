from __future__ import annotations

from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)
from app.domain.models.image_match_classification import (
    ImageMatchClassification,
)


class ImageFingerprintMatchClassifier:
    """
    Classifica o grau de correspondência técnica entre imagens.

    A classificação utiliza:

    - igualdade criptográfica para correspondência exata;
    - similaridade perceptual para correspondência visual;
    - limites centralizados para correspondência forte e moderada.

    Este componente não cria evidências e não define severidade.
    """

    STRONG_VISUAL_SIMILARITY = 0.98
    MODERATE_VISUAL_SIMILARITY = 0.95

    def classify(
        self,
        comparison: ImageFingerprintComparison,
    ) -> ImageMatchClassification:
        if comparison.exact_image_match:
            return ImageMatchClassification.EXACT

        if (
            comparison.perceptual_similarity
            >= self.STRONG_VISUAL_SIMILARITY
        ):
            return ImageMatchClassification.STRONG

        if (
            comparison.perceptual_similarity
            >= self.MODERATE_VISUAL_SIMILARITY
        ):
            return ImageMatchClassification.MODERATE

        return ImageMatchClassification.NONE