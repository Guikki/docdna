from __future__ import annotations

from typing import Any

from app.domain.models.document_evidence import (
    DocumentEvidence,
    EvidenceSeverity,
)
from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)
from app.domain.models.image_match_classification import (
    ImageMatchClassification,
)
from app.domain.services.image_fingerprint_match_classifier import (
    ImageFingerprintMatchClassifier,
)


class ImageFingerprintEvidenceBuilder:
    """
    Converte uma classificação técnica de similaridade
    em evidências documentais.

    Este componente não calcula similaridade.
    Toda decisão sobre os thresholds é delegada ao
    ImageFingerprintMatchClassifier.
    """

    def __init__(self) -> None:
        self._classifier = (
            ImageFingerprintMatchClassifier()
        )

    def build(
        self,
        *,
        comparison: ImageFingerprintComparison,
        first_document_id: str,
        second_document_id: str,
        first_image_reference: str | None = None,
        second_image_reference: str | None = None,
    ) -> list[DocumentEvidence]:

        classification = (
            self._classifier.classify(
                comparison
            )
        )

        document_ids = self._normalize_document_ids(
            first_document_id,
            second_document_id,
        )

        metadata = self._build_metadata(
            comparison=comparison,
            first_image_reference=first_image_reference,
            second_image_reference=second_image_reference,
        )

        if (
            classification
            is ImageMatchClassification.EXACT
        ):
            return [
                DocumentEvidence(
                    code="IMAGE_EXACT_MATCH",
                    title="Imagem idêntica localizada",
                    description=(
                        "As imagens comparadas possuem o mesmo hash "
                        "criptográfico, indicando conteúdo binário "
                        "exatamente igual."
                    ),
                    severity=EvidenceSeverity.INFO,
                    confidence=1.0,
                    source=self.__class__.__name__,
                    document_ids=document_ids,
                    metadata=metadata,
                )
            ]

        if (
            classification
            is ImageMatchClassification.STRONG
        ):
            severity = (
                EvidenceSeverity.MEDIUM
                if comparison.same_dimensions
                else EvidenceSeverity.LOW
            )

            return [
                DocumentEvidence(
                    code="IMAGE_STRONG_VISUAL_MATCH",
                    title="Forte semelhança visual entre imagens",
                    description=(
                        "As imagens possuem forte semelhança perceptual, "
                        "embora não apresentem igualdade criptográfica."
                    ),
                    severity=severity,
                    confidence=comparison.perceptual_similarity,
                    source=self.__class__.__name__,
                    document_ids=document_ids,
                    metadata=metadata,
                )
            ]

        if (
            classification
            is ImageMatchClassification.MODERATE
        ):
            return [
                DocumentEvidence(
                    code="IMAGE_VISUAL_MATCH",
                    title="Semelhança visual entre imagens",
                    description=(
                        "As imagens apresentam semelhança perceptual "
                        "relevante e devem ser avaliadas em conjunto "
                        "com outras evidências do documento."
                    ),
                    severity=EvidenceSeverity.LOW,
                    confidence=comparison.perceptual_similarity,
                    source=self.__class__.__name__,
                    document_ids=document_ids,
                    metadata=metadata,
                )
            ]

        return []

    @staticmethod
    def _normalize_document_ids(
        first_document_id: str,
        second_document_id: str,
    ) -> list[str]:

        first = first_document_id.strip()
        second = second_document_id.strip()

        if not first:
            raise ValueError(
                "first_document_id cannot be empty."
            )

        if not second:
            raise ValueError(
                "second_document_id cannot be empty."
            )

        return [
            first,
            second,
        ]

    @staticmethod
    def _build_metadata(
        *,
        comparison: ImageFingerprintComparison,
        first_image_reference: str | None,
        second_image_reference: str | None,
    ) -> dict[str, Any]:

        return {
            "exact_image_match": comparison.exact_image_match,
            "perceptual_distance": comparison.perceptual_distance,
            "perceptual_similarity": comparison.perceptual_similarity,
            "average_distance": comparison.average_distance,
            "average_similarity": comparison.average_similarity,
            "difference_distance": comparison.difference_distance,
            "difference_similarity": comparison.difference_similarity,
            "same_dimensions": comparison.same_dimensions,
            "width_difference": comparison.width_difference,
            "height_difference": comparison.height_difference,
            "first_image_reference": first_image_reference,
            "second_image_reference": second_image_reference,
        }