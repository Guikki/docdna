from __future__ import annotations

from typing import Any

from app.domain.document.models.bounding_box import BoundingBox
from app.domain.document.models.color import Color
from app.domain.document.models.font import Font
from app.domain.document.models.text_span import TextSpan


class NativeTextSpanAdapter:
    """
    Converte spans textuais extraídos diretamente do PDF pelo PyMuPDF
    em TextSpan do domínio documental.

    Diferentemente do OcrTextSpanAdapter, este adaptador preserva
    propriedades tipográficas reais presentes na camada nativa do PDF:
    fonte, tamanho, cor e bounding box.

    Ele não classifica ocultação, fraude ou Prompt Injection.
    """

    PYMUPDF_FLAG_ITALIC = 2
    PYMUPDF_FLAG_MONOSPACED = 8
    PYMUPDF_FLAG_BOLD = 16

    def adapt(
        self,
        *,
        span_data: dict[str, Any],
        page_number: int,
    ) -> TextSpan:
        if not isinstance(
            span_data,
            dict,
        ):
            raise TypeError(
                "NativeTextSpanAdapter span_data must be a dictionary."
            )

        if (
            isinstance(page_number, bool)
            or not isinstance(
                page_number,
                int,
            )
        ):
            raise TypeError(
                "NativeTextSpanAdapter page_number must be an integer."
            )

        if page_number < 1:
            raise ValueError(
                "NativeTextSpanAdapter page_number must be "
                "greater than or equal to 1."
            )

        text = span_data.get(
            "text",
            "",
        )

        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "Native PDF span text must be a string."
            )

        bbox = span_data.get(
            "bbox"
        )

        if (
            not isinstance(
                bbox,
                (
                    tuple,
                    list,
                ),
            )
            or len(
                bbox
            )
            != 4
        ):
            raise ValueError(
                "Native PDF span bbox must contain "
                "four coordinates."
            )

        left, top, right, bottom = (
            float(
                value
            )
            for value in bbox
        )

        font_name = span_data.get(
            "font",
            "Unknown",
        )

        if not isinstance(
            font_name,
            str,
        ):
            font_name = str(
                font_name
            )

        font_name = (
            font_name.strip()
            or "Unknown"
        )

        raw_size = span_data.get(
            "size",
            1.0,
        )

        if (
            isinstance(
                raw_size,
                bool,
            )
            or not isinstance(
                raw_size,
                (
                    int,
                    float,
                ),
            )
        ):
            raise TypeError(
                "Native PDF span font size must be numeric."
            )

        font_size = float(
            raw_size
        )

        if font_size <= 0.0:
            font_size = 1.0

        color = self._color_from_pymupdf(
            span_data.get(
                "color",
                0,
            )
        )

        flags = span_data.get(
            "flags",
            0,
        )

        if (
            isinstance(
                flags,
                bool,
            )
            or not isinstance(
                flags,
                int,
            )
        ):
            flags = 0

        return TextSpan(
            text=text,
            bounding_box=BoundingBox(
                left=left,
                top=top,
                right=right,
                bottom=bottom,
            ),
            font=Font(
                name=font_name,
                size=font_size,
                color=color,
                bold=bool(
                    flags
                    & self.PYMUPDF_FLAG_BOLD
                ),
                italic=bool(
                    flags
                    & self.PYMUPDF_FLAG_ITALIC
                ),
                underline=False,
                monospaced=bool(
                    flags
                    & self.PYMUPDF_FLAG_MONOSPACED
                ),
                embedded=None,
            ),
            page_number=page_number,
        )

    def adapt_many(
        self,
        *,
        spans_data: list[
            dict[str, Any]
        ],
        page_number: int,
    ) -> tuple[
        TextSpan,
        ...
    ]:
        if not isinstance(
            spans_data,
            list,
        ):
            raise TypeError(
                "NativeTextSpanAdapter spans_data must be a list."
            )

        result: list[
            TextSpan
        ] = []

        for span_data in spans_data:
            span = self.adapt(
                span_data=span_data,
                page_number=page_number,
            )

            # Preservamos espaços internos e conteúdo original,
            # mas spans sem qualquer caractere não acrescentam
            # informação útil ao documento normalizado.
            if span.text == "":
                continue

            result.append(
                span
            )

        return tuple(
            result
        )

    @staticmethod
    def _color_from_pymupdf(
        value: Any,
    ) -> Color:
        """
        PyMuPDF fornece a cor textual como inteiro 0xRRGGBB.
        """

        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                int,
            )
        ):
            value = 0

        normalized = (
            value
            & 0xFFFFFF
        )

        red = (
            normalized
            >> 16
        ) & 0xFF

        green = (
            normalized
            >> 8
        ) & 0xFF

        blue = (
            normalized
        ) & 0xFF

        return Color.from_rgb255(
            red=red,
            green=green,
            blue=blue,
        )