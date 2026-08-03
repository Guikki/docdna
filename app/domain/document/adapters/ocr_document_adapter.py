from __future__ import annotations

from pathlib import Path

import pymupdf

from app.domain.document.adapters.ocr_text_span_adapter import (
    OcrTextSpanAdapter,
)
from app.domain.document.models.document import (
    Document as NormalizedDocument,
)
from app.domain.document.models.page import Page
from app.domain.models.ocr_result import OcrResult


class OcrDocumentAdapter:
    """
    Constrói um documento normalizado a partir do resultado do OCR.

    O adaptador:

    - preserva o OcrResult original;
    - converte OcrTextBox em TextSpan;
    - obtém as dimensões reais das páginas no PDF;
    - inclui páginas sem texto;
    - cria Page e Document do novo domínio documental.

    Ele não avalia confiança, fraude, risco ou qualidade do OCR.
    """

    def __init__(
        self,
        text_span_adapter: OcrTextSpanAdapter | None = None,
    ) -> None:
        self._text_span_adapter = (
            text_span_adapter
            or OcrTextSpanAdapter()
        )

    def adapt(
        self,
        *,
        source: str,
        ocr_result: OcrResult,
    ) -> NormalizedDocument:
        normalized_source = self._validate_source(
            source
        )

        if not isinstance(ocr_result, OcrResult):
            raise TypeError(
                "OcrDocumentAdapter ocr_result "
                "must be an OcrResult."
            )

        spans_by_page = (
            self._text_span_adapter.adapt_by_page(
                ocr_result
            )
        )

        pages: list[Page] = []

        with pymupdf.open(normalized_source) as pdf:
            for page_number, pdf_page in enumerate(
                pdf,
                start=1,
            ):
                page_rect = pdf_page.rect

                pages.append(
                    Page(
                        number=page_number,
                        width=float(page_rect.width),
                        height=float(page_rect.height),
                        text_spans=spans_by_page.get(
                            page_number,
                            (),
                        ),
                    )
                )

        self._validate_ocr_page_numbers(
            spans_by_page=spans_by_page,
            page_count=len(pages),
        )

        return NormalizedDocument(
            pages=tuple(pages),
        )

    @staticmethod
    def _validate_source(
        source: str,
    ) -> str:
        if not isinstance(source, str):
            raise TypeError(
                "OcrDocumentAdapter source "
                "must be a string."
            )

        normalized = source.strip()

        if not normalized:
            raise ValueError(
                "OcrDocumentAdapter source "
                "cannot be empty."
            )

        path = Path(normalized)

        if not path.exists():
            raise FileNotFoundError(
                f"PDF source not found: {normalized}"
            )

        if not path.is_file():
            raise ValueError(
                "OcrDocumentAdapter source "
                "must reference a file."
            )

        return str(path)

    @staticmethod
    def _validate_ocr_page_numbers(
        *,
        spans_by_page: dict[int, tuple],
        page_count: int,
    ) -> None:
        invalid_page_numbers = sorted(
            page_number
            for page_number in spans_by_page
            if page_number > page_count
        )

        if not invalid_page_numbers:
            return

        formatted_numbers = ", ".join(
            str(number)
            for number in invalid_page_numbers
        )

        raise ValueError(
            "OCR contains text boxes for pages that do not "
            "exist in the source PDF: "
            f"{formatted_numbers}."
        )