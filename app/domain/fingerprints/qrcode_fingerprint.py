from __future__ import annotations

from dataclasses import dataclass

from app.domain.fingerprints.fingerprint import Fingerprint


@dataclass(frozen=True, slots=True)
class QRCodeFingerprint(Fingerprint):
    """
    Representa um QR Code localizado dentro de um documento.
    """

    value: str

    encoding: str | None = None

    version: int | None = None

    error_correction: str | None = None

    image_hash: str | None = None

    rotation: float = 0.0

    def __post_init__(self) -> None:
        Fingerprint.__post_init__(self)

        if not self.value.strip():
            raise ValueError(
                "QR Code value cannot be empty."
            )