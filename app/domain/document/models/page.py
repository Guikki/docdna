from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from app.domain.document.models.bounding_box import BoundingBox
from app.domain.document.models.text_span import TextSpan


@dataclass(frozen=True, slots=True)
class Page:
    """
    Immutable representation of a document page.

    A Page stores objective page dimensions and the textual spans observed
    on that page. It does not perform OCR, fraud classification, layout
    interpretation or any other analytical operation.

    Every TextSpan contained by the page must reference the same page number.
    """

    number: int
    width: float
    height: float
    text_spans: tuple[TextSpan, ...] = ()

    def __post_init__(self) -> None:
        normalized_number = self._normalize_number(
            self.number
        )
        normalized_width = self._normalize_dimension(
            name="width",
            value=self.width,
        )
        normalized_height = self._normalize_dimension(
            name="height",
            value=self.height,
        )

        self._validate_text_spans(
            text_spans=self.text_spans,
            page_number=normalized_number,
        )

        object.__setattr__(
            self,
            "number",
            normalized_number,
        )
        object.__setattr__(
            self,
            "width",
            normalized_width,
        )
        object.__setattr__(
            self,
            "height",
            normalized_height,
        )

    @property
    def area(self) -> float:
        """
        Return the total page area in document coordinate units.
        """

        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        """
        Return the page width divided by its height.
        """

        return self.width / self.height

    @property
    def page_box(self) -> BoundingBox:
        """
        Return the complete page region using an origin at (0, 0).

        Readers remain responsible for normalizing source coordinates before
        creating the Page.
        """

        return BoundingBox(
            left=0.0,
            top=0.0,
            right=self.width,
            bottom=self.height,
        )

    @property
    def text_span_count(self) -> int:
        """
        Return the number of textual spans stored by the page.
        """

        return len(self.text_spans)

    @property
    def has_text_spans(self) -> bool:
        """
        Return whether the page contains at least one TextSpan.

        A span may contain an empty string or whitespace-only content.
        """

        return bool(self.text_spans)

    @property
    def has_visible_text(self) -> bool:
        """
        Return whether at least one span contains non-whitespace text.

        This property evaluates textual content only. It does not inspect
        opacity, clipping, layers, page boundaries or rendering conditions.
        """

        return any(
            span.has_visible_text
            for span in self.text_spans
        )

    @property
    def text(self) -> str:
        """
        Return the original span texts joined by line breaks.

        The original content of each TextSpan is preserved.
        """

        return "\n".join(
            span.text
            for span in self.text_spans
        )

    @property
    def normalized_text(self) -> str:
        """
        Return normalized non-empty span texts joined by line breaks.

        Empty and whitespace-only normalized spans are omitted from this
        comparison-friendly representation.
        """

        return "\n".join(
            normalized_text
            for span in self.text_spans
            if (normalized_text := span.normalized_text)
        )

    @property
    def character_count(self) -> int:
        """
        Return the sum of characters stored by all spans.

        Separating line breaks introduced by the text property are not counted.
        """

        return sum(
            span.character_count
            for span in self.text_spans
        )

    @property
    def normalized_character_count(self) -> int:
        """
        Return the sum of normalized characters from all spans.

        Separating line breaks are not counted.
        """

        return sum(
            span.normalized_character_count
            for span in self.text_spans
        )

    @property
    def word_count(self) -> int:
        """
        Return the sum of the word counts from all spans.
        """

        return sum(
            span.word_count
            for span in self.text_spans
        )

    @property
    def text_bounding_box(self) -> BoundingBox | None:
        """
        Return the smallest box containing every textual span.

        Returns None when the page has no TextSpan instances.
        """

        if not self.text_spans:
            return None

        return BoundingBox(
            left=min(
                span.bounding_box.left
                for span in self.text_spans
            ),
            top=min(
                span.bounding_box.top
                for span in self.text_spans
            ),
            right=max(
                span.bounding_box.right
                for span in self.text_spans
            ),
            bottom=max(
                span.bounding_box.bottom
                for span in self.text_spans
            ),
        )

    def spans_with_visible_text(self) -> tuple[TextSpan, ...]:
        """
        Return spans containing at least one non-whitespace character.
        """

        return tuple(
            span
            for span in self.text_spans
            if span.has_visible_text
        )

    @staticmethod
    def _normalize_number(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                "Page number must be an integer."
            )

        if value < 1:
            raise ValueError(
                "Page number must be greater than or equal to 1."
            )

        return value

    @staticmethod
    def _normalize_dimension(
        *,
        name: str,
        value: float,
    ) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise TypeError(
                f"Page {name} must be a numeric value."
            )

        normalized_value = float(value)

        if not isfinite(normalized_value):
            raise ValueError(
                f"Page {name} must be finite."
            )

        if normalized_value <= 0.0:
            raise ValueError(
                f"Page {name} must be greater than zero."
            )

        return normalized_value

    @staticmethod
    def _validate_text_spans(
        *,
        text_spans: tuple[TextSpan, ...],
        page_number: int,
    ) -> None:
        if not isinstance(text_spans, tuple):
            raise TypeError(
                "Page text_spans must be a tuple."
            )

        for index, span in enumerate(text_spans):
            if not isinstance(span, TextSpan):
                raise TypeError(
                    "Page text_spans must contain only TextSpan instances. "
                    f"Invalid item at index {index}."
                )

            if span.page_number != page_number:
                raise ValueError(
                    "TextSpan page_number must match the containing "
                    f"Page number. Invalid item at index {index}."
                )