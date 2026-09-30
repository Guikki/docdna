from __future__ import annotations

import hashlib
from pathlib import Path

import imagehash
from PIL import Image, UnidentifiedImageError

from app.domain.models.document_image import DocumentImage
from app.domain.models.image_hash_analysis import ImageHashAnalysis
from app.observability.performance_timer import PerformanceTimer


class ImageHashAnalyzer:
    """
    Calcula hashes visuais e criptográficos de uma imagem
    previamente extraída de um documento.

    Além do resultado analítico, expõe um relatório de desempenho
    da última execução para fins de observabilidade da pipeline.
    """

    def __init__(
        self,
    ) -> None:
        self._performance_report: dict | None = None

    @property
    def performance_report(
        self,
    ) -> dict | None:
        return self._performance_report

    def analyze(
        self,
        image: DocumentImage,
    ) -> ImageHashAnalysis:
        timer = PerformanceTimer()
        image_path = Path(image.saved_path)

        try:
            with timer.measure(
                "image_hash_validate_path"
            ):
                self._validate_image_path(
                    image_path
                )

            with timer.measure(
                "image_hash_sha256"
            ):
                image_hash = (
                    self._calculate_sha256(
                        image_path
                    )
                )

            try:
                with timer.measure(
                    "image_hash_open_convert"
                ):
                    with Image.open(
                        image_path
                    ) as opened_image:
                        normalized_image = (
                            opened_image.convert(
                                "RGB"
                            )
                        )

                with timer.measure(
                    "image_hash_phash"
                ):
                    perceptual_hash = str(
                        imagehash.phash(
                            normalized_image
                        )
                    )

                with timer.measure(
                    "image_hash_average_hash"
                ):
                    average_hash = str(
                        imagehash.average_hash(
                            normalized_image
                        )
                    )

                with timer.measure(
                    "image_hash_difference_hash"
                ):
                    difference_hash = str(
                        imagehash.dhash(
                            normalized_image
                        )
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
                perceptual_hash=(
                    perceptual_hash
                ),
                average_hash=(
                    average_hash
                ),
                difference_hash=(
                    difference_hash
                ),
                image_hash=image_hash,
            )

        finally:
            self._performance_report = (
                timer.to_dict()
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

        with image_path.open(
            "rb"
        ) as image_file:
            while chunk := image_file.read(
                8192
            ):
                sha256.update(
                    chunk
                )

        return sha256.hexdigest()
