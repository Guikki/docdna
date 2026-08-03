from __future__ import annotations

from datetime import date
from re import finditer

from app.domain.models.detected_date import (
    DateSource,
    DetectedDate,
)


class DateExtractorService:
    """
    Extrai datas presentes em um conteúdo textual.

    Este serviço apenas identifica datas e as converte em
    DetectedDate. Ele não compara datas nem produz evidências.
    """

    _SUPPORTED_PATTERNS = (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
    )

    def extract(
        self,
        *,
        content: str | None,
        source: DateSource,
        document_id: str,
        page_number: int | None = None,
        confidence: float | None = None,
        metadata_field: str | None = None,
    ) -> list[DetectedDate]:

        if not content:
            return []

        results: list[DetectedDate] = []

        pattern = r"\b\d{2}[\/\.-]\d{2}[\/\.-]\d{4}\b"

        for match in finditer(pattern, content):
            raw_value = match.group()

            parsed_date = self._parse_date(raw_value)

            if parsed_date is None:
                continue

            surrounding_text = self._extract_context(
                content,
                match.start(),
                match.end(),
            )

            results.append(
                DetectedDate(
                    value=parsed_date,
                    raw_content=raw_value,
                    source=source,
                    document_id=document_id,
                    page_number=page_number,
                    metadata_field=metadata_field,
                    surrounding_text=surrounding_text,
                    confidence=confidence,
                )
            )

        return results

    def _parse_date(
        self,
        raw_value: str,
    ) -> date | None:

        from datetime import datetime

        for date_format in self._SUPPORTED_PATTERNS:
            try:
                return datetime.strptime(
                    raw_value,
                    date_format,
                ).date()
            except ValueError:
                continue

        return None

    def _extract_context(
        self,
        content: str,
        start: int,
        end: int,
    ) -> str:

        radius = 40

        left = max(
            start - radius,
            0,
        )

        right = min(
            end + radius,
            len(content),
        )

        return content[left:right].strip()