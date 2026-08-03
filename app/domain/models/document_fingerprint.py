from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.models.detected_date import DetectedDate


@dataclass(frozen=True, slots=True)
class DocumentFingerprint:
    """
    Representa a identidade técnica de um documento.

    Esta estrutura consolida todas as informações relevantes
    para comparação entre documentos, independentemente
    da origem dos dados.
    """

    document_id: str

    # Identificação do arquivo
    file_name: str | None = None
    file_hash: str | None = None

    # Impressões (fingerprints)
    visual_hash: str | None = None
    text_hash: str | None = None
    metadata_hash: str | None = None

    # Conteúdo identificado
    barcode_values: tuple[str, ...] = field(default_factory=tuple)
    qrcode_values: tuple[str, ...] = field(default_factory=tuple)

    detected_dates: tuple[DetectedDate, ...] = field(default_factory=tuple)

    image_hashes: tuple[str, ...] = field(default_factory=tuple)

    font_names: tuple[str, ...] = field(default_factory=tuple)

    metadata_fields: dict[str, str] = field(default_factory=dict)

    text_length: int = 0

    page_count: int = 0

    @property
    def has_visual_information(self) -> bool:
        return (
            self.visual_hash is not None
            or bool(self.image_hashes)
        )

    @property
    def has_text_information(self) -> bool:
        return (
            self.text_hash is not None
            or self.text_length > 0
        )

    @property
    def has_metadata_information(self) -> bool:
        return (
            self.metadata_hash is not None
            or bool(self.metadata_fields)
        )

    @property
    def has_barcodes(self) -> bool:
        return bool(self.barcode_values)

    @property
    def has_qrcodes(self) -> bool:
        return bool(self.qrcode_values)

    @property
    def has_dates(self) -> bool:
        return bool(self.detected_dates)

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.file_hash,
                self.visual_hash,
                self.text_hash,
                self.metadata_hash,
                self.barcode_values,
                self.qrcode_values,
                self.detected_dates,
                self.image_hashes,
                self.font_names,
                self.metadata_fields,
            )
        )