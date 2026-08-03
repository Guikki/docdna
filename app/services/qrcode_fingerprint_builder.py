from __future__ import annotations

from app.domain.fingerprints.qrcode_fingerprint import QRCodeFingerprint
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation


class QRCodeFingerprintBuilder:
    """
    Constrói um QRCodeFingerprint a partir
    dos dados extraídos por um leitor de QR Code.
    """

    def build(
        self,
        *,
        location: DocumentLocation,
        confidence: ConfidenceScore,
        value: str,
        encoding: str | None = None,
        version: int | None = None,
        error_correction: str | None = None,
        image_hash: str | None = None,
        rotation: float = 0.0,
    ) -> QRCodeFingerprint:

        return QRCodeFingerprint(
            location=location,
            confidence=confidence,
            value=value,
            encoding=encoding,
            version=version,
            error_correction=error_correction,
            image_hash=image_hash,
            rotation=rotation,
        )