from __future__ import annotations

from dataclasses import dataclass

from app.domain.fingerprints.image_fingerprint import ImageFingerprint


@dataclass(frozen=True, slots=True)
class LogoFingerprint(ImageFingerprint):
    """
    Representa uma logo identificada dentro de um documento.
    """

    company_name: str | None = None

    def __post_init__(self) -> None:
        ImageFingerprint.__post_init__(self)