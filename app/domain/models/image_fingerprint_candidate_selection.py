from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.image_fingerprint_pair import (
    ImageFingerprintPair,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ImageFingerprintCandidateSelectionStats:
    """
    Resume o espaço de busca visual antes e depois da seleção
    de candidatos.

    potential_cross_document_pairs representa matematicamente
    quantas comparações seriam realizadas pelo modelo exaustivo.

    candidate_pairs representa quantas comparações permanecem
    após a seleção por índices.
    """

    documents_total: int
    fingerprints_total: int
    potential_cross_document_pairs: int
    candidate_pairs: int
    exact_sha256_pairs: int
    perceptual_only_pairs: int
    reduction_ratio: float


@dataclass(
    frozen=True,
    slots=True,
)
class ImageFingerprintCandidateSelectionResult:
    """
    Resultado da seleção de candidatos visuais.

    Apenas pares capazes de produzir correspondência exata ou
    visual segundo os critérios atuais seguem para o comparador.
    """

    pairs: tuple[
        ImageFingerprintPair,
        ...
    ]

    stats: (
        ImageFingerprintCandidateSelectionStats
    )