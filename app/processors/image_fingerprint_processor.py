from __future__ import annotations

import mimetypes

from app.domain.fingerprints.image_fingerprint import ImageFingerprint
from app.domain.models.document_image import DocumentImage
from app.domain.readers.image_reader import ImageReader
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation
from app.services.image_fingerprint_builder import ImageFingerprintBuilder
from app.services.image_hash_analyzer import ImageHashAnalyzer


class ImageFingerprintProcessor:
    """
    Coordena a geração de fingerprints das imagens extraídas
    de um documento.

    Fluxo coordenado:

    1. extrair imagens com ImageReader;
    2. analisar os hashes com ImageHashAnalyzer;
    3. construir os fingerprints com ImageFingerprintBuilder;
    4. devolver os fingerprints produzidos.

    O Processor não executa leitura de PDF diretamente, não calcula
    hashes e não implementa regras de comparação.
    """

    def __init__(
        self,
        reader: ImageReader | None = None,
        analyzer: ImageHashAnalyzer | None = None,
        builder: ImageFingerprintBuilder | None = None,
    ) -> None:
        self._reader = reader or ImageReader()
        self._analyzer = analyzer or ImageHashAnalyzer()
        self._builder = builder or ImageFingerprintBuilder()

    def process(
        self,
        source: str,
        confidence: ConfidenceScore | None = None,
    ) -> list[ImageFingerprint]:
        """
        Processa todas as imagens extraídas de um documento.

        A confiança padrão é 1.0 porque, neste estágio, ela representa
        apenas a confiança técnica na extração da imagem, e não uma
        classificação de autenticidade ou fraude.
        """

        images = self._reader.read(source)

        extraction_confidence = confidence or ConfidenceScore(1.0)

        return [
            self._process_image(
                image=image,
                confidence=extraction_confidence,
            )
            for image in images
        ]

    def _process_image(
        self,
        image: DocumentImage,
        confidence: ConfidenceScore,
    ) -> ImageFingerprint:
        analysis = self._analyzer.analyze(image)

        location = self._create_location(image)
        mime_type = self._detect_mime_type(image)

        return self._builder.build_from_analysis(
            image=image,
            location=location,
            confidence=confidence,
            analysis=analysis,
            mime_type=mime_type,
            description=self._create_description(image),
        )

    @staticmethod
    def _create_location(
        image: DocumentImage,
    ) -> DocumentLocation:
        """
        Cria uma localização correspondente à área completa da imagem.

        O ImageReader ainda não fornece as coordenadas da imagem na página.
        Portanto, o BoundingBox representa, por enquanto, o espaço interno
        da própria imagem extraída.
        """

        return DocumentLocation(
            page_number=image.page_number,
            bounding_box=BoundingBox(
                x=0.0,
                y=0.0,
                width=float(image.width),
                height=float(image.height),
            ),
        )

    @staticmethod
    def _detect_mime_type(
        image: DocumentImage,
    ) -> str | None:
        mime_type, _ = mimetypes.guess_type(image.filename)
        return mime_type

    @staticmethod
    def _create_description(
        image: DocumentImage,
    ) -> str:
        return (
            f"Imagem {image.image_index} extraída da página "
            f"{image.page_number}, xref {image.xref}."
        )