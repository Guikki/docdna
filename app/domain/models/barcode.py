from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.document_location import (
    DocumentLocation,
)


@dataclass
class Barcode:
    """
    Representa um código de barras/QR Code detectado no documento.

    Os quatro campos originais continuam obrigatórios para manter
    compatibilidade com os consumidores existentes.

    Os metadados adicionais são puramente técnicos e opcionais.
    Eles preservam informações fornecidas pelo leitor visual sem
    realizar qualquer classificação de autenticidade ou fraude.
    """

    barcode_index: int
    page_number: int
    format: str
    content: str

    location: DocumentLocation | None = None
    image_hash: str | None = None
    orientation: float = 0.0
    error_correction: str | None = None
    content_type: str | None = None
