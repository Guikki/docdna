import re

from app.domain.models.document_ocr import DocumentOcr
from app.domain.models.document_text import DocumentText
from app.domain.models.printed_numeric_line import PrintedNumericLine


class PrintedNumericLineReader:

    MIN_DIGITS = 40
    MAX_DIGITS = 50

    def read(
        self,
        native_text: DocumentText,
        ocr: DocumentOcr,
    ) -> list[PrintedNumericLine]:
        detected_lines: list[PrintedNumericLine] = []
        processed_values: set[str] = set()

        sources = [
            ("native_text", native_text.content),
            ("ocr", ocr.content),
        ]

        for source_name, content in sources:
            candidates = self._extract_candidates(content)

            for raw_content, normalized_content in candidates:
                if normalized_content in processed_values:
                    continue

                detected_lines.append(
                    PrintedNumericLine(
                        line_index=len(detected_lines) + 1,
                        source=source_name,
                        raw_content=raw_content,
                        normalized_content=normalized_content,
                        digit_count=len(normalized_content),
                    )
                )

                processed_values.add(normalized_content)

        return detected_lines

    def _extract_candidates(
        self,
        content: str,
    ) -> list[tuple[str, str]]:
        if not content:
            return []

        pattern = re.compile(r"(?:\d[\s.\-]*){40,50}")
        candidates: list[tuple[str, str]] = []

        for match in pattern.finditer(content):
            raw_content = match.group().strip()
            normalized_content = re.sub(r"\D", "", raw_content)

            if not (
                self.MIN_DIGITS
                <= len(normalized_content)
                <= self.MAX_DIGITS
            ):
                continue

            candidates.append(
                (raw_content, normalized_content)
            )

        return candidates