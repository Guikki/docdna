from __future__ import annotations

from app.domain.fingerprints.signature_fingerprint import SignatureFingerprint
from app.domain.models.document_image import DocumentImage
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation


class SignatureFingerprintBuilder:
    """
    Constrói um SignatureFingerprint a partir
    dos dados extraídos do documento.
    """

    def build(
        self,
        *,
        image: DocumentImage,
        location: DocumentLocation,
        confidence: ConfidenceScore,
        perceptual_hash: str,
        average_hash: str | None = None,
        difference_hash: str | None = None,
        image_hash: str | None = None,
        dpi: int | None = None,
        mime_type: str | None = None,
        description: str | None = None,
        signer_name: str | None = None,
    ) -> SignatureFingerprint:

        return SignatureFingerprint(
            location=location,
            confidence=confidence,
            perceptual_hash=perceptual_hash,
            average_hash=average_hash,
            difference_hash=difference_hash,
            image_hash=image_hash,
            width=image.width,
            height=image.height,
            dpi=dpi,
            mime_type=mime_type,
            description=description,
            signer_name=signer_name,
        )