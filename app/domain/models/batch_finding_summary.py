from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BatchFindingSummary:
    """
    Resumo agregado de um tipo de achado dentro de um lote.

    A prevalência é calculada por documento, e não pela quantidade
    bruta de ocorrências.

    Exemplo:

        28 documentos possuem ocultação visual
        30 documentos foram analisados

        affected_documents = 28
        total_documents = 30
        prevalence_percentage = 93.33

    occurrence_count pode ser maior que affected_documents quando
    um mesmo documento contém múltiplas ocorrências do mesmo tipo.
    """

    code: str
    title: str

    affected_documents: int
    total_documents: int

    occurrence_count: int

    prevalence_percentage: float

    affected_document_ids: tuple[str, ...]

    highest_confidence: float = 0.0

    def __post_init__(self) -> None:
        normalized_code = self.code.strip().upper()
        normalized_title = self.title.strip()

        if not normalized_code:
            raise ValueError(
                "Batch finding summary code cannot be empty."
            )

        if not normalized_title:
            raise ValueError(
                "Batch finding summary title cannot be empty."
            )

        if self.affected_documents < 0:
            raise ValueError(
                "affected_documents cannot be negative."
            )

        if self.total_documents < 0:
            raise ValueError(
                "total_documents cannot be negative."
            )

        if self.occurrence_count < 0:
            raise ValueError(
                "occurrence_count cannot be negative."
            )

        if self.affected_documents > self.total_documents:
            raise ValueError(
                "affected_documents cannot be greater than "
                "total_documents."
            )

        if not 0.0 <= self.prevalence_percentage <= 100.0:
            raise ValueError(
                "prevalence_percentage must be between "
                "0.0 and 100.0."
            )

        if not 0.0 <= self.highest_confidence <= 1.0:
            raise ValueError(
                "highest_confidence must be between 0.0 and 1.0."
            )

        normalized_document_ids = tuple(
            dict.fromkeys(
                str(document_id).strip()
                for document_id in self.affected_document_ids
                if str(document_id).strip()
            )
        )

        if len(normalized_document_ids) != self.affected_documents:
            raise ValueError(
                "affected_document_ids must contain exactly one "
                "identifier for each affected document."
            )

        object.__setattr__(
            self,
            "code",
            normalized_code,
        )

        object.__setattr__(
            self,
            "title",
            normalized_title,
        )

        object.__setattr__(
            self,
            "affected_document_ids",
            normalized_document_ids,
        )

    @property
    def has_findings(self) -> bool:
        return self.affected_documents > 0

    @property
    def prevalence_ratio(self) -> float:
        if self.total_documents == 0:
            return 0.0

        return (
            self.affected_documents
            / self.total_documents
        )

    @property
    def prevalence_label(self) -> str:
        return (
            f"{self.affected_documents}"
            f"/{self.total_documents}"
            f" ({self.prevalence_percentage:.2f}%)"
        )