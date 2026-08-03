from dataclasses import dataclass
from datetime import date
from enum import Enum


class DateSource(str, Enum):
    """
    Origem técnica da data identificada.

    A origem informa de qual camada de leitura a data foi obtida,
    sem atribuir significado jurídico ou conclusivo ao conteúdo.
    """

    NATIVE_TEXT = "native_text"
    OCR = "ocr"
    PDF_METADATA = "pdf_metadata"
    FILE_SYSTEM = "file_system"


@dataclass(frozen=True)
class DetectedDate:
    """
    Representa uma data identificada durante a análise documental.

    Este modelo não representa, por si só, uma inconsistência ou
    evidência. Ele apenas registra uma data, sua origem e o contexto
    técnico necessário para comparações temporais posteriores.
    """

    value: date
    raw_content: str
    source: DateSource
    document_id: str

    page_number: int | None = None
    metadata_field: str | None = None
    surrounding_text: str | None = None
    confidence: float | None = None