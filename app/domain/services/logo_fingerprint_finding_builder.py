from __future__ import annotations

from typing import Any

from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
    CrossValidationSeverity,
)
from app.domain.models.logo_fingerprint_comparison import (
    LogoFingerprintComparison,
)
from app.domain.models.logo_fingerprint_pair import (
    LogoFingerprintPair,
)
from app.domain.models.logo_match_classification import (
    LogoMatchClassification,
)
from app.domain.services.logo_fingerprint_match_classifier import (
    LogoFingerprintMatchClassifier,
)


class LogoFingerprintFindingBuilder:
    """
    Converte o resultado técnico da comparação entre dois logos
    em findings utilizados pela validação cruzada.

    Este componente não calcula similaridade e não conhece
    os thresholds de classificação visual.

    As regras de classificação são delegadas ao
    LogoFingerprintMatchClassifier.

    A divergência entre nomes de empresas possui precedência
    sobre os findings puramente visuais quando os logos apresentam
    correspondência visual relevante.
    """

    def __init__(
        self,
        classifier: LogoFingerprintMatchClassifier | None = None,
    ) -> None:
        self._classifier = (
            classifier
            or LogoFingerprintMatchClassifier()
        )

    def build(
        self,
        *,
        pair: LogoFingerprintPair,
        comparison: LogoFingerprintComparison,
        comparator: str,
    ) -> list[CrossValidationFinding]:
        comparator_name = self._normalize_comparator_name(
            comparator
        )

        classification = self._classifier.classify(
            comparison
        )

        if classification is LogoMatchClassification.NONE:
            return []

        metadata = self._build_metadata(
            pair=pair,
            comparison=comparison,
            classification=classification,
        )

        if comparison.same_company_name is False:
            return [
                self._build_company_name_mismatch_finding(
                    pair=pair,
                    comparison=comparison,
                    classification=classification,
                    comparator=comparator_name,
                    metadata=metadata,
                )
            ]

        if classification is LogoMatchClassification.EXACT:
            return [
                CrossValidationFinding(
                    code="LOGO_EXACT_MATCH",
                    title="Logo idêntico localizado",
                    description=(
                        "Os logos comparados possuem o mesmo hash "
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

        if classification is LogoMatchClassification.STRONG:
            severity = (
                CrossValidationSeverity.MEDIUM
                if comparison.same_dimensions
                else CrossValidationSeverity.LOW
            )

            return [
                CrossValidationFinding(
                    code="LOGO_STRONG_VISUAL_MATCH",
                    title=(
                        "Forte semelhança visual entre logos"
                    ),
                    description=(
                        "Os logos apresentam forte semelhança "
                        "perceptual, embora não possuam igualdade "
                        "criptográfica."
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
                code="LOGO_VISUAL_MATCH",
                title="Semelhança visual entre logos",
                description=(
                    "Os logos apresentam semelhança perceptual "
                    "relevante e devem ser avaliados em conjunto "
                    "com as demais evidências dos documentos."
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
    def _build_company_name_mismatch_finding(
        *,
        pair: LogoFingerprintPair,
        comparison: LogoFingerprintComparison,
        classification: LogoMatchClassification,
        comparator: str,
        metadata: dict[str, Any],
    ) -> CrossValidationFinding:
        first_company_name = (
            pair.first_logo.company_name
            or "não informado"
        )
        second_company_name = (
            pair.second_logo.company_name
            or "não informado"
        )

        if classification is LogoMatchClassification.EXACT:
            severity = CrossValidationSeverity.HIGH
            confidence = 1.0
            match_description = (
                "Os logos possuem conteúdo binário exatamente igual"
            )
        elif classification is LogoMatchClassification.STRONG:
            severity = CrossValidationSeverity.HIGH
            confidence = comparison.perceptual_similarity
            match_description = (
                "Os logos possuem forte semelhança visual"
            )
        else:
            severity = CrossValidationSeverity.MEDIUM
            confidence = comparison.perceptual_similarity
            match_description = (
                "Os logos possuem semelhança visual relevante"
            )

        return CrossValidationFinding(
            code="LOGO_COMPANY_NAME_MISMATCH",
            title=(
                "Logo semelhante associado a empresas diferentes"
            ),
            description=(
                f"{match_description}, mas estão associados a "
                "nomes de empresas diferentes: "
                f"'{first_company_name}' e "
                f"'{second_company_name}'."
            ),
            severity=severity,
            confidence=confidence,
            comparator=comparator,
            document_ids=[
                pair.first_document_id,
                pair.second_document_id,
            ],
            metadata=metadata,
        )

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
        pair: LogoFingerprintPair,
        comparison: LogoFingerprintComparison,
        classification: LogoMatchClassification,
    ) -> dict[str, Any]:
        first_logo = pair.first_logo
        second_logo = pair.second_logo

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
            "same_company_name": (
                comparison.same_company_name
            ),
            "first_logo": {
                "page_number": (
                    first_logo.location.page_number
                ),
                "width": first_logo.width,
                "height": first_logo.height,
                "mime_type": first_logo.mime_type,
                "image_hash": first_logo.image_hash,
                "perceptual_hash": (
                    first_logo.perceptual_hash
                ),
                "average_hash": (
                    first_logo.average_hash
                ),
                "difference_hash": (
                    first_logo.difference_hash
                ),
                "company_name": (
                    first_logo.company_name
                ),
            },
            "second_logo": {
                "page_number": (
                    second_logo.location.page_number
                ),
                "width": second_logo.width,
                "height": second_logo.height,
                "mime_type": second_logo.mime_type,
                "image_hash": second_logo.image_hash,
                "perceptual_hash": (
                    second_logo.perceptual_hash
                ),
                "average_hash": (
                    second_logo.average_hash
                ),
                "difference_hash": (
                    second_logo.difference_hash
                ),
                "company_name": (
                    second_logo.company_name
                ),
            },
        }