from __future__ import annotations

from dataclasses import dataclass

from app.domain.document.models.page import Page


@dataclass(frozen=True, slots=True)
class Document:
    """
    Immutable representation of a complete document.

    A Document aggregates ordered Page instances and exposes derived,
    format-independent information about their contents.

    The model does not know how the pages were extracted and does not
    perform OCR, fraud detection, fingerprinting or risk classification.
    """

    pages: tuple[Page, ...] = ()

    def __post_init__(self) -> None:
        self._validate_pages(self.pages)

    @property
    def page_count(self) -> int:
        """
        Return the number of pages contained by the document.
        """

        return len(self.pages)

    @property
    def has_pages(self) -> bool:
        """
        Return whether the document contains at least one page.
        """

        return bool(self.pages)

    @property
    def page_numbers(self) -> tuple[int, ...]:
        """
        Return page numbers in their stored order.
        """

        return tuple(
            page.number
            for page in self.pages
        )

    @property
    def first_page(self) -> Page | None:
        """
        Return the first page or None when the document is empty.
        """

        if not self.pages:
            return None

        return self.pages[0]

    @property
    def last_page(self) -> Page | None:
        """
        Return the last page or None when the document is empty.
        """

        if not self.pages:
            return None

        return self.pages[-1]

    @property
    def has_text_spans(self) -> bool:
        """
        Return whether any page contains at least one TextSpan.

        A contained span may still have empty or whitespace-only content.
        """

        return any(
            page.has_text_spans
            for page in self.pages
        )

    @property
    def has_visible_text(self) -> bool:
        """
        Return whether any page contains non-whitespace textual content.

        This property evaluates text content only. It does not inspect
        rendering, opacity, clipping, layers or graphical visibility.
        """

        return any(
            page.has_visible_text
            for page in self.pages
        )

    @property
    def text(self) -> str:
        """
        Return original page texts separated by two line breaks.

        Empty pages are preserved in the textual composition so page order
        and page boundaries are not silently changed.
        """

        return "\n\n".join(
            page.text
            for page in self.pages
        )

    @property
    def normalized_text(self) -> str:
        """
        Return normalized non-empty page texts separated by two line breaks.

        Pages without normalized textual content are omitted from this
        comparison-friendly representation.
        """

        return "\n\n".join(
            normalized_text
            for page in self.pages
            if (normalized_text := page.normalized_text)
        )

    @property
    def text_span_count(self) -> int:
        """
        Return the total number of TextSpan instances in all pages.
        """

        return sum(
            page.text_span_count
            for page in self.pages
        )

    @property
    def character_count(self) -> int:
        """
        Return the sum of original characters stored by all pages.

        Separators introduced by the text property are not counted.
        """

        return sum(
            page.character_count
            for page in self.pages
        )

    @property
    def normalized_character_count(self) -> int:
        """
        Return the sum of normalized characters stored by all pages.

        Separators introduced by normalized_text are not counted.
        """

        return sum(
            page.normalized_character_count
            for page in self.pages
        )

    @property
    def word_count(self) -> int:
        """
        Return the sum of word counts from every page.
        """

        return sum(
            page.word_count
            for page in self.pages
        )

    @property
    def total_area(self) -> float:
        """
        Return the sum of the individual page areas.

        Pages have independent coordinate systems, so this value is an
        aggregate measurement and not a global document bounding box.
        """

        return sum(
            page.area
            for page in self.pages
        )

    @property
    def largest_page(self) -> Page | None:
        """
        Return the page with the greatest area.

        When multiple pages have the same greatest area, the first one in
        document order is returned. Returns None for an empty document.
        """

        if not self.pages:
            return None

        return max(
            self.pages,
            key=lambda page: page.area,
        )

    @property
    def smallest_page(self) -> Page | None:
        """
        Return the page with the smallest area.

        When multiple pages have the same smallest area, the first one in
        document order is returned. Returns None for an empty document.
        """

        if not self.pages:
            return None

        return min(
            self.pages,
            key=lambda page: page.area,
        )

    @property
    def average_page_area(self) -> float:
        """
        Return the arithmetic mean of page areas.

        An empty document has an average page area of zero.
        """

        if not self.pages:
            return 0.0

        return self.total_area / self.page_count

    def pages_with_text_spans(self) -> tuple[Page, ...]:
        """
        Return pages that contain at least one TextSpan.
        """

        return tuple(
            page
            for page in self.pages
            if page.has_text_spans
        )

    def pages_with_visible_text(self) -> tuple[Page, ...]:
        """
        Return pages containing non-whitespace textual content.
        """

        return tuple(
            page
            for page in self.pages
            if page.has_visible_text
        )

    def page_by_number(
        self,
        number: int,
    ) -> Page | None:
        """
        Return a page by its one-based number.

        Returns None when the document does not contain the requested page.
        """

        normalized_number = self._validate_requested_page_number(
            number
        )

        if normalized_number > self.page_count:
            return None

        return self.pages[normalized_number - 1]

    @staticmethod
    def _validate_pages(
        pages: tuple[Page, ...],
    ) -> None:
        if not isinstance(pages, tuple):
            raise TypeError(
                "Document pages must be a tuple."
            )

        for index, page in enumerate(pages):
            if not isinstance(page, Page):
                raise TypeError(
                    "Document pages must contain only Page instances. "
                    f"Invalid item at index {index}."
                )

            expected_number = index + 1

            if page.number != expected_number:
                raise ValueError(
                    "Document pages must use continuous numbering "
                    "starting at 1. "
                    f"Expected page number {expected_number} "
                    f"at index {index}, received {page.number}."
                )

    @staticmethod
    def _validate_requested_page_number(
        value: int,
    ) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                "Requested page number must be an integer."
            )

        if value < 1:
            raise ValueError(
                "Requested page number must be greater than or equal to 1."
            )

        return value