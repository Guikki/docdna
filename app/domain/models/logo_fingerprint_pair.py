from __future__ import annotations

from dataclasses import dataclass

from app.domain.fingerprints.logo_fingerprint import (
    LogoFingerprint,
)


@dataclass(frozen=True, slots=True)
class LogoFingerprintPair:
    """
    Representa um par de fingerprints de logo
    pertencentes a documentos distintos.

    O modelo apenas transporta os elementos que
    serão comparados.
    """

    first_document_id: str
    second_document_id: str

    first_logo: LogoFingerprint
    second_logo: LogoFingerprint

    def __post_init__(self) -> None:
        first_document_id = (
            self.first_document_id.strip()
        )

        second_document_id = (
            self.second_document_id.strip()
        )

        if not first_document_id:
            raise ValueError(
                "first_document_id cannot be empty."
            )

        if not second_document_id:
            raise ValueError(
                "second_document_id cannot be empty."
            )

        if first_document_id == second_document_id:
            raise ValueError(
                "logo fingerprints must belong "
                "to different documents."
            )

        object.__setattr__(
            self,
            "first_document_id",
            first_document_id,
        )

        object.__setattr__(
            self,
            "second_document_id",
            second_document_id,
        )