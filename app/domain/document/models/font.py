from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from unicodedata import normalize

from app.domain.document.models.color import Color


@dataclass(frozen=True, slots=True)
class Font:
    """
    Immutable description of a font observed in a document.

    This model stores only objective typographic properties extracted
    from the source document. It does not determine whether a font is
    suspicious, inconsistent or fraudulent.

    The embedded field may be None when the source reader cannot
    determine whether the font is embedded in the document.
    """

    name: str
    size: float
    color: Color

    bold: bool = False
    italic: bool = False
    underline: bool = False
    monospaced: bool = False
    embedded: bool | None = None

    def __post_init__(self) -> None:
        normalized_name = self._normalize_required_name(
            self.name
        )

        normalized_size = self._normalize_size(
            self.size
        )

        if not isinstance(self.color, Color):
            raise TypeError(
                "Font color must be a Color."
            )

        self._validate_boolean(
            name="bold",
            value=self.bold,
        )
        self._validate_boolean(
            name="italic",
            value=self.italic,
        )
        self._validate_boolean(
            name="underline",
            value=self.underline,
        )
        self._validate_boolean(
            name="monospaced",
            value=self.monospaced,
        )
        self._validate_optional_boolean(
            name="embedded",
            value=self.embedded,
        )

        object.__setattr__(
            self,
            "name",
            normalized_name,
        )
        object.__setattr__(
            self,
            "size",
            normalized_size,
        )

    @property
    def normalized_name(self) -> str:
        """
        Return a comparison-friendly representation of the font name.

        The original capitalization stored in name is preserved. This
        property applies Unicode normalization, collapses whitespace
        and performs case-insensitive normalization.
        """

        unicode_normalized = normalize(
            "NFKC",
            self.name,
        )

        return " ".join(
            unicode_normalized.split()
        ).casefold()

    @property
    def is_regular(self) -> bool:
        """
        Return whether no explicit typographic emphasis is active.

        Monospaced is considered a font family characteristic rather
        than an emphasis style, so it does not affect this property.
        """

        return not (
            self.bold
            or self.italic
            or self.underline
        )

    @property
    def style_names(self) -> tuple[str, ...]:
        """
        Return the active typographic characteristics.

        The returned tuple follows a stable order so it can safely be
        used in reports, comparisons and serialized representations.
        """

        styles: list[str] = []

        if self.bold:
            styles.append("bold")

        if self.italic:
            styles.append("italic")

        if self.underline:
            styles.append("underline")

        if self.monospaced:
            styles.append("monospaced")

        if not styles:
            styles.append("regular")

        return tuple(styles)

    @property
    def has_emphasis(self) -> bool:
        """
        Return whether bold, italic or underline is active.
        """

        return not self.is_regular

    @property
    def embedding_known(self) -> bool:
        """
        Return whether the font embedding state is known.
        """

        return self.embedded is not None

    @property
    def is_embedded(self) -> bool:
        """
        Return whether the font is explicitly known to be embedded.

        An unknown embedding state returns False. Consumers that need
        to distinguish False from an unknown value should inspect
        embedding_known or embedded directly.
        """

        return self.embedded is True

    @staticmethod
    def _normalize_required_name(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError(
                "Font name must be a string."
            )

        normalized_value = " ".join(
            normalize(
                "NFKC",
                value,
            ).split()
        )

        if not normalized_value:
            raise ValueError(
                "Font name cannot be empty."
            )

        return normalized_value

    @staticmethod
    def _normalize_size(value: float) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise TypeError(
                "Font size must be a numeric value."
            )

        normalized_value = float(value)

        if not isfinite(normalized_value):
            raise ValueError(
                "Font size must be finite."
            )

        if normalized_value <= 0.0:
            raise ValueError(
                "Font size must be greater than zero."
            )

        return normalized_value

    @staticmethod
    def _validate_boolean(
        *,
        name: str,
        value: bool,
    ) -> None:
        if not isinstance(value, bool):
            raise TypeError(
                f"Font {name} must be a boolean."
            )

    @staticmethod
    def _validate_optional_boolean(
        *,
        name: str,
        value: bool | None,
    ) -> None:
        if value is not None and not isinstance(value, bool):
            raise TypeError(
                f"Font {name} must be a boolean or None."
            )