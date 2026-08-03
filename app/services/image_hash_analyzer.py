from __future__ import annotations

import hashlib
from pathlib import Path

import imagehash
from PIL import Image, UnidentifiedImageError

from app.domain.models.document_image import DocumentImage
from app.domain.models.image_hash_analysis import ImageHashAnalysis


class ImageHashAnalyzer:
    """
    Calcula hashes visuais e criptográficos de uma imagem
    previamente extraída de um documento.

    Responsabilidades:

    - validar a existência do arquivo;
    - abrir a imagem;
    - calcular hashes perceptuais;
    - calcular o SHA-256 do arquivo original;
    - devolver um ImageHashAnalysis.

    Este componente não constrói fingerprints, não compara
    imagens e não produz evidências.
    """

    def analyze(
        self,
        image: DocumentImage,
    ) -> ImageHashAnalysis:
        image_path = Path(image.saved_path)

        self._validate_image_path(image_path)

        image_hash = self._calculate_sha256(image_path)

        try:
            with Image.open(image_path) as opened_image:
                normalized_image = opened_image.convert("RGB")

                perceptual_hash = str(
                    imagehash.phash(normalized_image)
                )
                average_hash = str(
                    imagehash.average_hash(normalized_image)
                )
                difference_hash = str(
                    imagehash.dhash(normalized_image)
                )

        except UnidentifiedImageError as error:
            raise ValueError(
                f"File is not a valid image: {image_path}"
            ) from error
        except OSError as error:
            raise ValueError(
                f"Image could not be processed: {image_path}"
            ) from error

        return ImageHashAnalysis(
            perceptual_hash=perceptual_hash,
            average_hash=average_hash,
            difference_hash=difference_hash,
            image_hash=image_hash,
        )

    @staticmethod
    def _validate_image_path(
        image_path: Path,
    ) -> None:
        if not image_path.exists():
            raise FileNotFoundError(
                f"Image file was not found: {image_path}"
            )

        if not image_path.is_file():
            raise ValueError(
                f"Image path must point to a file: {image_path}"
            )

    @staticmethod
    def _calculate_sha256(
        image_path: Path,
    ) -> str:
        sha256 = hashlib.sha256()

        with image_path.open("rb") as image_file:
            while chunk := image_file.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()