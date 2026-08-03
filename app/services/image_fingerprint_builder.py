from __future__ import annotations

from app.domain.fingerprints.image_fingerprint import ImageFingerprint
from app.domain.models.document_image import DocumentImage
from app.domain.models.image_hash_analysis import ImageHashAnalysis
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation


class ImageFingerprintBuilder:
    """
    Constrói um ImageFingerprint a partir de uma imagem extraída
    e dos resultados técnicos produzidos pelos analyzers.

    O builder não calcula hashes, não abre arquivos e não executa
    comparações. Sua responsabilidade é exclusivamente construir
    objetos válidos do domínio.
    """

    def build(
        self,
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
    ) -> ImageFingerprint:
        """
        Constrói um fingerprint a partir dos hashes informados
        individualmente.

        Este método permanece disponível para compatibilidade com
        componentes já existentes.
        """

        return ImageFingerprint(
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
        )

    def build_from_analysis(
        self,
        image: DocumentImage,
        location: DocumentLocation,
        confidence: ConfidenceScore,
        analysis: ImageHashAnalysis,
        dpi: int | None = None,
        mime_type: str | None = None,
        description: str | None = None,
    ) -> ImageFingerprint:
        """
        Constrói um fingerprint utilizando o resultado produzido
        pelo ImageHashAnalyzer.
        """

        return self.build(
            image=image,
            location=location,
            confidence=confidence,
            perceptual_hash=analysis.perceptual_hash,
            average_hash=analysis.average_hash,
            difference_hash=analysis.difference_hash,
            image_hash=analysis.image_hash,
            dpi=dpi,
            mime_type=mime_type,
            description=description,
        )