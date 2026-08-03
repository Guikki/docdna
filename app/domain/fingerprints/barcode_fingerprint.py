from __future__ import annotations

from dataclasses import dataclass

from app.domain.fingerprints.fingerprint import Fingerprint


@dataclass(frozen=True, slots=True)
class BarcodeFingerprint(Fingerprint):
    """
    Representa um código de barras identificado
    em um documento.
    """

    value: str

    symbology: str | None = None

    image_hash: str | None = None

    rotation: float = 0.0

    raw_text: str | None = None

    def __post_init__(self):
        Fingerprint.__post_init__(self)

        if not self.value.strip():
            raise ValueError(
                "Barcode value cannot be empty."
            )