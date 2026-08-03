from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation


@dataclass(frozen=True, slots=True)
class Fingerprint:
    """
    Classe base para qualquer fingerprint extraído
    de um documento.

    Representa um elemento localizado em uma página
    com determinado grau de confiança.
    """

    location: DocumentLocation

    confidence: ConfidenceScore

    def __post_init__(self) -> None:
        """
        Hook para subclasses.

        A classe base atualmente não possui validações,
        porém este método permite que subclasses chamem
        super().__post_init__() de forma segura, além de
        facilitar futuras validações comuns sem quebrar
        as implementações existentes.
        """
        pass