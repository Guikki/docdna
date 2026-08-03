from __future__ import annotations

from typing import Any

from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
    CrossValidationSeverity,
)
from app.domain.models.qrcode_fingerprint_comparison import (
    QRCodeFingerprintComparison,
)
from app.domain.models.qrcode_fingerprint_pair import (
    QRCodeFingerprintPair,
)
from app.domain.models.qrcode_match_classification import (
    QRCodeMatchClassification,
)
from app.domain.services.qrcode_fingerprint_match_classifier import (
    QRCodeFingerprintMatchClassifier,
)


class QRCodeFingerprintFindingBuilder:
    """
    Converte o resultado técnico da comparação entre dois QR Codes
    em findings utilizados pela validação cruzada.

    Este componente não compara fingerprints e não define
    thresholds de classificação.

    As regras de classificação técnica são delegadas ao
    QRCodeFingerprintMatchClassifier.

    O builder interpreta fenômenos específicos do domínio,
    como QR Codes regenerados e divergências entre a imagem
    armazenada e o conteúdo decodificado.

    A classificação representa o grau de correspondência técnica.
    A severidade representa a relevância do fenômeno para análise
    documental. Esses conceitos são independentes.
    """

    def __init__(
        self,
        classifier: QRCodeFingerprintMatchClassifier | None = None,
    ) -> None:
        self._classifier = (
            classifier
            or QRCodeFingerprintMatchClassifier()
        )

    def build(
        self,
        *,
        pair: QRCodeFingerprintPair,
        comparison: QRCodeFingerprintComparison,
        comparator: str,
    ) -> list[CrossValidationFinding]:
        comparator_name = self._normalize_comparator_name(
            comparator
        )

        classification = self._classifier.classify(
            comparison
        )

        if classification is QRCodeMatchClassification.NONE:
            return []

        metadata = self._build_metadata(
            pair=pair,
            comparison=comparison,
            classification=classification,
        )

        if comparison.is_visually_equal_but_value_changed:
            return [
                CrossValidationFinding(
                    code="QRCODE_VALUE_MISMATCH",
                    title=(
                        "QR Code visualmente idêntico com "
                        "conteúdo divergente"
                    ),
                    description=(
                        "Os QR Codes comparados possuem a mesma "
                        "representação visual, mas os conteúdos "
                        "decodificados são diferentes. A divergência "
                        "deve ser analisada em conjunto com as demais "
                        "evidências documentais."
                    ),
                    severity=CrossValidationSeverity.HIGH,
                    confidence=1.0,
                    comparator=comparator_name,
                    document_ids=[
                        pair.first_document_id,
                        pair.second_document_id,
                    ],
                    metadata=metadata,
                )
            ]

        if comparison.is_same_value_with_different_image:
            return [
                CrossValidationFinding(
                    code="QRCODE_REGENERATED",
                    title=(
                        "QR Code possivelmente regenerado"
                    ),
                    description=(
                        "Os QR Codes possuem o mesmo conteúdo "
                        "decodificado, mas suas representações "
                        "visuais não são exatamente iguais. Isso "
                        "pode indicar regeneração, redimensionamento "
                        "ou reprocessamento da imagem."
                    ),
                    severity=CrossValidationSeverity.LOW,
                    confidence=1.0,
                    comparator=comparator_name,
                    document_ids=[
                        pair.first_document_id,
                        pair.second_document_id,
                    ],
                    metadata=metadata,
                )
            ]

        if classification is QRCodeMatchClassification.EXACT:
            return [
                CrossValidationFinding(
                    code="QRCODE_EXACT_MATCH",
                    title="QR Code idêntico localizado",
                    description=(
                        "Os QR Codes comparados possuem o mesmo "
                        "conteúdo decodificado e o mesmo hash de "
                        "imagem, indicando correspondência exata "
                        "entre elementos presentes em documentos "
                        "distintos do lote."
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

        return []

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
        pair: QRCodeFingerprintPair,
        comparison: QRCodeFingerprintComparison,
        classification: QRCodeMatchClassification,
    ) -> dict[str, Any]:
        first_qrcode = pair.first_qrcode
        second_qrcode = pair.second_qrcode

        return {
            "classification": classification.value,
            "same_value": comparison.same_value,
            "exact_image_match": (
                comparison.exact_image_match
            ),
            "same_encoding": comparison.same_encoding,
            "same_version": comparison.same_version,
            "same_error_correction": (
                comparison.same_error_correction
            ),
            "rotation_difference": (
                comparison.rotation_difference
            ),
            "has_encoding_comparison": (
                comparison.has_encoding_comparison
            ),
            "has_version_comparison": (
                comparison.has_version_comparison
            ),
            "has_error_correction_comparison": (
                comparison.has_error_correction_comparison
            ),
            "has_same_rotation": (
                comparison.has_same_rotation
            ),
            "is_same_qrcode": (
                comparison.is_same_qrcode
            ),
            "is_same_value_with_different_image": (
                comparison.is_same_value_with_different_image
            ),
            "is_visually_equal_but_value_changed": (
                comparison.is_visually_equal_but_value_changed
            ),
            "first_qrcode": {
                "page_number": (
                    first_qrcode.location.page_number
                ),
                "value": first_qrcode.value,
                "encoding": first_qrcode.encoding,
                "version": first_qrcode.version,
                "error_correction": (
                    first_qrcode.error_correction
                ),
                "image_hash": first_qrcode.image_hash,
                "rotation": first_qrcode.rotation,
            },
            "second_qrcode": {
                "page_number": (
                    second_qrcode.location.page_number
                ),
                "value": second_qrcode.value,
                "encoding": second_qrcode.encoding,
                "version": second_qrcode.version,
                "error_correction": (
                    second_qrcode.error_correction
                ),
                "image_hash": second_qrcode.image_hash,
                "rotation": second_qrcode.rotation,
            },
        }