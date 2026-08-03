from datetime import date, datetime
from re import fullmatch


class PdfMetadataDateParser:
    """
    Interpreta datas presentes nos metadados de arquivos PDF.

    O parser preserva uma abordagem tolerante: valores inválidos,
    incompletos ou desconhecidos retornam None em vez de interromper
    a análise documental.
    """

    def parse_date(
        self,
        raw_value: str | None,
    ) -> date | None:
        if raw_value is None:
            return None

        normalized_value = raw_value.strip()

        if not normalized_value:
            return None

        normalized_value = self._remove_pdf_prefix(
            normalized_value
        )

        digits = self._extract_initial_digits(
            normalized_value
        )

        if digits is not None:
            parsed_date = self._parse_compact_date(
                digits
            )

            if parsed_date is not None:
                return parsed_date

        return self._parse_common_formats(
            normalized_value
        )

    def _remove_pdf_prefix(
        self,
        raw_value: str,
    ) -> str:
        if raw_value.startswith("D:"):
            return raw_value[2:]

        return raw_value

    def _extract_initial_digits(
        self,
        raw_value: str,
    ) -> str | None:
        match = fullmatch(
            r"(\d{4,14})(?:Z|[+-].*)?",
            raw_value,
        )

        if match is None:
            return None

        return match.group(1)

    def _parse_compact_date(
        self,
        digits: str,
    ) -> date | None:
        if len(digits) < 8:
            return None

        year = self._to_int(
            digits[0:4]
        )
        month = self._to_int(
            digits[4:6]
        )
        day = self._to_int(
            digits[6:8]
        )

        if (
            year is None
            or month is None
            or day is None
        ):
            return None

        try:
            return date(
                year,
                month,
                day,
            )
        except ValueError:
            return None

    def _parse_common_formats(
        self,
        raw_value: str,
    ) -> date | None:
        supported_formats = (
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
        )

        for date_format in supported_formats:
            try:
                return datetime.strptime(
                    raw_value,
                    date_format,
                ).date()
            except ValueError:
                continue

        return None

    def _to_int(
        self,
        value: str,
    ) -> int | None:
        try:
            return int(value)
        except ValueError:
            return None