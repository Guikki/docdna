from __future__ import annotations

from dataclasses import dataclass

from app.domain.fingerprints.fingerprint import Fingerprint


@dataclass(frozen=True, slots=True)
class ImageFingerprint(Fingerprint):
    """
    Representa uma imagem localizada dentro de um documento.
    """

    perceptual_hash: str

    average_hash: str | None = None

    difference_hash: str | None = None

    image_hash: str | None = None

    width: int = 0

    height: int = 0

    dpi: int | None = None

    mime_type: str | None = None

    description: str | None = None

    def __post_init__(self) -> None:
        Fingerprint.__post_init__(self)

        if not self.perceptual_hash.strip():
            raise ValueError(
                "perceptual_hash cannot be empty."
            )

        if self.width <= 0:
            raise ValueError(
                "width must be greater than zero."
            )

        if self.height <= 0:
            raise ValueError(
                "height must be greater than zero."
            )