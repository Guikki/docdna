from __future__ import annotations

from app.domain.models.detected_date import DetectedDate
from app.domain.models.document_fingerprint import (
    DocumentFingerprint,
)


class DocumentFingerprintBuilder:
    """
    Constrói um DocumentFingerprint a partir das informações
    produzidas pelas etapas anteriores da pipeline.

    O Builder não extrai informações do documento.
    Ele apenas consolida dados já obtidos.
    """

    def build(
        self,
        *,
        document_id: str,
        file_name: str | None = None,
        file_hash: str | None = None,
        visual_hash: str | None = None,
        text_hash: str | None = None,
        metadata_hash: str | None = None,
        barcode_values: tuple[str, ...] = (),
        qrcode_values: tuple[str, ...] = (),
        detected_dates: tuple[DetectedDate, ...] = (),
        image_hashes: tuple[str, ...] = (),
        font_names: tuple[str, ...] = (),
        metadata_fields: dict[str, str] | None = None,
        text_length: int = 0,
        page_count: int = 0,
    ) -> DocumentFingerprint:

        return DocumentFingerprint(
            document_id=document_id,
            file_name=file_name,
            file_hash=file_hash,
            visual_hash=visual_hash,
            text_hash=text_hash,
            metadata_hash=metadata_hash,
            barcode_values=tuple(barcode_values),
            qrcode_values=tuple(qrcode_values),
            detected_dates=tuple(detected_dates),
            image_hashes=tuple(image_hashes),
            font_names=tuple(font_names),
            metadata_fields=metadata_fields or {},
            text_length=text_length,
            page_count=page_count,
        )