from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from app.domain.document.models.bounding_box import (
    BoundingBox,
)
from app.domain.document.models.color import Color
from app.domain.document.models.font import Font
from app.domain.document.models.text_span import (
    TextSpan,
)
from app.domain.models.ocr_result import OcrResult
from app.domain.models.ocr_text_box import OcrTextBox


@dataclass(frozen=True, slots=True)
class OcrTextSpanAdapter:
    """
    Converts legacy OCR text boxes into document-domain TextSpan objects.

    The adapter preserves the existing OCR models and does not modify
    confidence, language or OCR quality information.

    OCR-specific information remains available in OcrResult and
    OcrTextBox. The resulting TextSpan objects contain only the facts
    required by the normalized document domain:

    - text;
    - page number;
    - bounding box;
    - technical OCR font representation.

    The OCR engine does not know the real font used by the source
    document. For that reason, the adapter creates an explicit technical
    font named OCR_UNKNOWN instead of pretending that the original font
    was identified.
    """

    font_name: str = "OCR_UNKNOWN"
    default_font_size: float = 1.0
    font_color: Color = Color(
        red=0.0,
        green=0.0,
        blue=0.0,
    )

    def __post_init__(self) -> None:
        normalized_font_name = (
            self._normalize_font_name(
                self.font_name
            )
        )

        normalized_default_size = (
            self._normalize_default_font_size(
                self.default_font_size
            )
        )

        if not isinstance(
            self.font_color,
            Color,
        ):
            raise TypeError(
                "OcrTextSpanAdapter font_color "
                "must be a Color."
            )

        object.__setattr__(
            self,
            "font_name",
            normalized_font_name,
        )

        object.__setattr__(
            self,
            "default_font_size",
            normalized_default_size,
        )

    def adapt(
        self,
        result: OcrResult,
    ) -> tuple[TextSpan, ...]:
        """
        Convert every OCR text box into a TextSpan.

        The original order of the OCR text boxes is preserved.
        """

        if not isinstance(result, OcrResult):
            raise TypeError(
                "OcrTextSpanAdapter result "
                "must be an OcrResult."
            )

        if not isinstance(
            result.text_boxes,
            list,
        ):
            raise TypeError(
                "OcrResult text_boxes must be a list."
            )

        return tuple(
            self.adapt_box(
                text_box,
                index=index,
            )
            for index, text_box in enumerate(
                result.text_boxes
            )
        )

    def adapt_box(
        self,
        text_box: OcrTextBox,
        *,
        index: int | None = None,
    ) -> TextSpan:
        """
        Convert one legacy OCR text box into a TextSpan.
        """

        self._validate_text_box(
            text_box,
            index=index,
        )

        bounding_box = (
            BoundingBox.from_position_and_size(
                left=text_box.left,
                top=text_box.top,
                width=text_box.width,
                height=text_box.height,
            )
        )

        font = Font(
            name=self.font_name,
            size=self._estimate_font_size(
                text_box.height
            ),
            color=self.font_color,
            embedded=None,
        )

        return TextSpan(
            text=text_box.text,
            bounding_box=bounding_box,
            font=font,
            page_number=text_box.page_number,
        )

    def adapt_by_page(
        self,
        result: OcrResult,
    ) -> dict[int, tuple[TextSpan, ...]]:
        """
        Convert OCR text boxes and group TextSpan objects by page.

        Page order and the original order of boxes inside each page
        are preserved.
        """

        spans = self.adapt(result)

        spans_by_page: dict[
            int,
            list[TextSpan],
        ] = {}

        for span in spans:
            spans_by_page.setdefault(
                span.page_number,
                [],
            ).append(span)

        return {
            page_number: tuple(page_spans)
            for page_number, page_spans
            in spans_by_page.items()
        }

    def _estimate_font_size(
        self,
        box_height: int,
    ) -> float:
        """
        Use the OCR box height as a technical font-size estimate.

        A non-positive box height falls back to default_font_size.
        This does not claim to identify the original typographic size.
        """

        if box_height <= 0:
            return self.default_font_size

        return float(box_height)

    @staticmethod
    def _validate_text_box(
        text_box: OcrTextBox,
        *,
        index: int | None,
    ) -> None:
        location = (
            ""
            if index is None
            else f" at index {index}"
        )

        if not isinstance(
            text_box,
            OcrTextBox,
        ):
            raise TypeError(
                "OcrResult text_boxes must contain "
                "only OcrTextBox instances"
                f"{location}."
            )

        if not isinstance(
            text_box.text,
            str,
        ):
            raise TypeError(
                "OcrTextBox text must be a string"
                f"{location}."
            )

        if (
            isinstance(text_box.page_number, bool)
            or not isinstance(
                text_box.page_number,
                int,
            )
        ):
            raise TypeError(
                "OcrTextBox page_number must be "
                f"an integer{location}."
            )

        if text_box.page_number < 1:
            raise ValueError(
                "OcrTextBox page_number must be "
                "greater than or equal to 1"
                f"{location}."
            )

        for field_name in (
            "left",
            "top",
            "width",
            "height",
        ):
            value = getattr(
                text_box,
                field_name,
            )

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise TypeError(
                    f"OcrTextBox {field_name} must "
                    f"be an integer{location}."
                )

        if text_box.width < 0:
            raise ValueError(
                "OcrTextBox width cannot be negative"
                f"{location}."
            )

        if text_box.height < 0:
            raise ValueError(
                "OcrTextBox height cannot be negative"
                f"{location}."
            )

        if (
            isinstance(text_box.confidence, bool)
            or not isinstance(
                text_box.confidence,
                (int, float),
            )
        ):
            raise TypeError(
                "OcrTextBox confidence must be "
                f"a numeric value{location}."
            )

        if not isfinite(
            float(text_box.confidence)
        ):
            raise ValueError(
                "OcrTextBox confidence must be finite"
                f"{location}."
            )

    @staticmethod
    def _normalize_font_name(
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                "OcrTextSpanAdapter font_name "
                "must be a string."
            )

        normalized = " ".join(
            value.split()
        )

        if not normalized:
            raise ValueError(
                "OcrTextSpanAdapter font_name "
                "cannot be empty."
            )

        return normalized

    @staticmethod
    def _normalize_default_font_size(
        value: float,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (int, float),
            )
        ):
            raise TypeError(
                "OcrTextSpanAdapter "
                "default_font_size must be numeric."
            )

        normalized = float(value)

        if not isfinite(normalized):
            raise ValueError(
                "OcrTextSpanAdapter "
                "default_font_size must be finite."
            )

        if normalized <= 0.0:
            raise ValueError(
                "OcrTextSpanAdapter "
                "default_font_size must be "
                "greater than zero."
            )

        return normalized