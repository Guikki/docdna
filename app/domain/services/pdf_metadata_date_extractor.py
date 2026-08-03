from app.domain.models.detected_date import (
    DateSource,
    DetectedDate,
)
from app.domain.models.pdf_info import PdfInfo
from app.domain.services.pdf_metadata_date_parser import (
    PdfMetadataDateParser,
)


class PdfMetadataDateExtractor:
    """
    Converte datas brutas presentes em PdfInfo em objetos DetectedDate.

    Este serviço não avalia inconsistências e não produz evidências.
    Sua responsabilidade é apenas interpretar e registrar datas
    provenientes dos metadados técnicos do PDF.
    """

    CREATION_DATE_FIELD = "creationDate"
    MODIFICATION_DATE_FIELD = "modDate"

    def __init__(
        self,
        parser: PdfMetadataDateParser | None = None,
    ) -> None:
        self._parser = (
            parser
            if parser is not None
            else PdfMetadataDateParser()
        )

    def extract(
        self,
        *,
        pdf_info: PdfInfo,
        document_id: str,
    ) -> list[DetectedDate]:
        detected_dates: list[DetectedDate] = []

        creation_date = self._build_detected_date(
            raw_value=pdf_info.creation_date,
            metadata_field=self.CREATION_DATE_FIELD,
            document_id=document_id,
        )

        if creation_date is not None:
            detected_dates.append(creation_date)

        modification_date = self._build_detected_date(
            raw_value=pdf_info.modification_date,
            metadata_field=self.MODIFICATION_DATE_FIELD,
            document_id=document_id,
        )

        if modification_date is not None:
            detected_dates.append(modification_date)

        return detected_dates

    def _build_detected_date(
        self,
        *,
        raw_value: str | None,
        metadata_field: str,
        document_id: str,
    ) -> DetectedDate | None:
        parsed_date = self._parser.parse_date(
            raw_value
        )

        if parsed_date is None:
            return None

        normalized_raw_value = (
            raw_value.strip()
            if raw_value is not None
            else ""
        )

        return DetectedDate(
            value=parsed_date,
            raw_content=normalized_raw_value,
            source=DateSource.PDF_METADATA,
            document_id=document_id,
            page_number=None,
            metadata_field=metadata_field,
            surrounding_text=self._build_context(
                metadata_field=metadata_field,
                raw_value=normalized_raw_value,
            ),
            confidence=1.0,
        )

    def _build_context(
        self,
        *,
        metadata_field: str,
        raw_value: str,
    ) -> str:
        if metadata_field == self.CREATION_DATE_FIELD:
            field_label = "Data de criação do PDF"
        elif metadata_field == self.MODIFICATION_DATE_FIELD:
            field_label = "Data de modificação do PDF"
        else:
            field_label = metadata_field

        return f"{field_label}: {raw_value}"