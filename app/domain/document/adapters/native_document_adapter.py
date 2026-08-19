from __future__ import annotations

from pathlib import Path
from typing import Any

import pymupdf

from app.domain.document.adapters.native_text_span_adapter import (
    NativeTextSpanAdapter,
)
from app.domain.document.models.document import (
    Document as NormalizedDocument,
)
from app.domain.document.models.page import Page


class NativeDocumentAdapter:
    """
    Constrói o documento normalizado a partir da camada textual
    nativa do PDF.

    Esta é a fonte apropriada para análises que dependem de:
    - coordenadas reais do texto;
    - nome e tamanho de fonte;
    - cor textual;
    - texto muito pequeno;
    - conteúdo branco ou visualmente oculto.

    OCR permanece uma fonte paralela e independente.
    """

    def __init__(
        self,
        text_span_adapter: (
            NativeTextSpanAdapter
            | None
        ) = None,
    ) -> None:
        self._text_span_adapter = (
            text_span_adapter
            or NativeTextSpanAdapter()
        )

    def adapt(
        self,
        *,
        source: str,
    ) -> NormalizedDocument:
        normalized_source = (
            self._validate_source(
                source
            )
        )

        pages: list[
            Page
        ] = []

        with pymupdf.open(
            normalized_source
        ) as pdf:
            for (
                page_number,
                pdf_page,
            ) in enumerate(
                pdf,
                start=1,
            ):
                page_rect = (
                    pdf_page.rect
                )

                text_dict = (
                    pdf_page.get_text(
                        "dict"
                    )
                )

                span_payloads = (
                    self._extract_span_payloads(
                        text_dict
                    )
                )

                text_spans = (
                    self._text_span_adapter
                    .adapt_many(
                        spans_data=(
                            span_payloads
                        ),
                        page_number=(
                            page_number
                        ),
                    )
                )

                pages.append(
                    Page(
                        number=page_number,
                        width=float(
                            page_rect.width
                        ),
                        height=float(
                            page_rect.height
                        ),
                        text_spans=(
                            text_spans
                        ),
                    )
                )

        return NormalizedDocument(
            pages=tuple(
                pages
            ),
        )

    @staticmethod
    def _extract_span_payloads(
        text_dict: dict[
            str,
            Any,
        ],
    ) -> list[
        dict[
            str,
            Any,
        ]
    ]:
        if not isinstance(
            text_dict,
            dict,
        ):
            raise TypeError(
                "PyMuPDF text dictionary must be a dictionary."
            )

        result: list[
            dict[
                str,
                Any,
            ]
        ] = []

        blocks = text_dict.get(
            "blocks",
            [],
        )

        if not isinstance(
            blocks,
            list,
        ):
            return result

        for block in blocks:
            if not isinstance(
                block,
                dict,
            ):
                continue

            # type == 0 representa bloco textual no formato dict.
            if block.get(
                "type",
                0,
            ) != 0:
                continue

            lines = block.get(
                "lines",
                [],
            )

            if not isinstance(
                lines,
                list,
            ):
                continue

            for line in lines:
                if not isinstance(
                    line,
                    dict,
                ):
                    continue

                spans = line.get(
                    "spans",
                    [],
                )

                if not isinstance(
                    spans,
                    list,
                ):
                    continue

                for span in spans:
                    if not isinstance(
                        span,
                        dict,
                    ):
                        continue

                    result.append(
                        span
                    )

        return result

    @staticmethod
    def _validate_source(
        source: str,
    ) -> str:
        if not isinstance(
            source,
            str,
        ):
            raise TypeError(
                "NativeDocumentAdapter source must be a string."
            )

        normalized = (
            source.strip()
        )

        if not normalized:
            raise ValueError(
                "NativeDocumentAdapter source cannot be empty."
            )

        path = Path(
            normalized
        )

        if not path.exists():
            raise FileNotFoundError(
                f"PDF source not found: {normalized}"
            )

        if not path.is_file():
            raise ValueError(
                "NativeDocumentAdapter source must reference a file."
            )

        return str(
            path
        )