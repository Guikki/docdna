from __future__ import annotations

from typing import Any

from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
    CrossValidationSeverity,
)
from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)
from app.domain.models.image_fingerprint_pair import (
    ImageFingerprintPair,
)
from app.domain.models.image_match_classification import (
    ImageMatchClassification,
)
from app.domain.services.image_fingerprint_match_classifier import (
    ImageFingerprintMatchClassifier,
)


class ImageFingerprintFindingBuilder:
    """
    Converte o resultado técnico da comparação entre duas imagens
    em findings utilizados pela validação cruzada.

    Este componente não calcula similaridade e não conhece
    os thresholds de classificação.

    As regras de classificação são delegadas ao
    ImageFingerprintMatchClassifier.
    """

    def __init__(
        self,
        classifier: ImageFingerprintMatchClassifier | None = None,
    ) -> None:
        self._classifier = (
            classifier
            or ImageFingerprintMatchClassifier()
        )

    def build(
        self,
        *,
        pair: ImageFingerprintPair,
        comparison: ImageFingerprintComparison,
        comparator: str,
    ) -> list[CrossValidationFinding]:
        comparator_name = self._normalize_comparator_name(
            comparator
        )

        classification = self._classifier.classify(
            comparison
        )

        if classification is ImageMatchClassification.NONE:
            return []

        metadata = self._build_metadata(
            pair=pair,
            comparison=comparison,
            classification=classification,
        )

        if classification is ImageMatchClassification.EXACT:
            return [
                CrossValidationFinding(
                    code="IMAGE_EXACT_MATCH",
                    title="Imagem idêntica localizada",
                    description=(
                        "As imagens comparadas possuem o mesmo hash "
                        "criptográfico, indicando conteúdo binário "
                        "exatamente igual em documentos distintos "
                        "do lote."
                    ),
                    severity=CrossValidationSeverity.INFO,
                    confidence=1.0,
                    comparator=comparator_name,
                    document_ids=[
                        pair.first_document_id,
                        pair.second_document_id,
                    ],
                    metadata=metadata,
                )
            ]

        if classification is ImageMatchClassification.STRONG:
            severity = (
                CrossValidationSeverity.MEDIUM
                if comparison.same_dimensions
                else CrossValidationSeverity.LOW
            )

            return [
                CrossValidationFinding(
                    code="IMAGE_STRONG_VISUAL_MATCH",
                    title=(
                        "Forte semelhança visual entre imagens"
                    ),
                    description=(
                        "As imagens possuem forte semelhança "
                        "perceptual, embora não apresentem "
                        "igualdade criptográfica."
                    ),
                    severity=severity,
                    confidence=(
                        comparison.perceptual_similarity
                    ),
                    comparator=comparator_name,
                    document_ids=[
                        pair.first_document_id,
                        pair.second_document_id,
                    ],
                    metadata=metadata,
                )
            ]

        return [
            CrossValidationFinding(
                code="IMAGE_VISUAL_MATCH",
                title="Semelhança visual entre imagens",
                description=(
                    "As imagens apresentam semelhança perceptual "
                    "relevante e devem ser avaliadas em conjunto "
                    "com outras evidências dos documentos."
                ),
                severity=CrossValidationSeverity.LOW,
                confidence=comparison.perceptual_similarity,
                comparator=comparator_name,
                document_ids=[
                    pair.first_document_id,
                    pair.second_document_id,
                ],
                metadata=metadata,
            )
        ]

    @staticmethod
    def _normalize_comparator_name(
        comparator: str,
    ) -> str:
        normalized = comparator.strip()

        if not normalized:
            raise ValueError(
                "comparator cannot be empty."
            )

        return normalized

    @staticmethod
    def _build_metadata(
        *,
        pair: ImageFingerprintPair,
        comparison: ImageFingerprintComparison,
        classification: ImageMatchClassification,
    ) -> dict[str, Any]:
        first_image = pair.first_image
        second_image = pair.second_image

        return {
            "classification": classification.value,
            "exact_image_match": (
                comparison.exact_image_match
            ),
            "perceptual_distance": (
                comparison.perceptual_distance
            ),
            "perceptual_similarity": (
                comparison.perceptual_similarity
            ),
            "average_distance": (
                comparison.average_distance
            ),
            "average_similarity": (
                comparison.average_similarity
            ),
            "difference_distance": (
                comparison.difference_distance
            ),
            "difference_similarity": (
                comparison.difference_similarity
            ),
            "same_dimensions": (
                comparison.same_dimensions
            ),
            "width_difference": (
                comparison.width_difference
            ),
            "height_difference": (
                comparison.height_difference
            ),
            "first_image": {
                "page_number": (
                    first_image.location.page_number
                ),
                "width": first_image.width,
                "height": first_image.height,
                "mime_type": first_image.mime_type,
                "image_hash": first_image.image_hash,
                "perceptual_hash": (
                    first_image.perceptual_hash
                ),
                "average_hash": first_image.average_hash,
                "difference_hash": (
                    first_image.difference_hash
                ),
            },
            "second_image": {
                "page_number": (
                    second_image.location.page_number
                ),
                "width": second_image.width,
                "height": second_image.height,
                "mime_type": second_image.mime_type,
                "image_hash": second_image.image_hash,
                "perceptual_hash": (
                    second_image.perceptual_hash
                ),
                "average_hash": second_image.average_hash,
                "difference_hash": (
                    second_image.difference_hash
                ),
            },
        }