from __future__ import annotations

from dataclasses import dataclass

from app.domain.fingerprints.image_fingerprint import ImageFingerprint


@dataclass(frozen=True, slots=True)
class SignatureFingerprint(ImageFingerprint):
    """
    Representa uma assinatura identificada dentro de um documento.
    """

    signer_name: str | None = None

    def __post_init__(self) -> None:
        ImageFingerprint.__post_init__(self)