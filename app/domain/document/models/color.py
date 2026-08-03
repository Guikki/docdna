from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt


@dataclass(frozen=True, slots=True)
class Color:
    """
    Immutable RGBA color represented by normalized channel values.

    Every channel uses the interval from 0.0 to 1.0.
    """

    red: float
    green: float
    blue: float
    alpha: float = 1.0

    def __post_init__(self) -> None:
        normalized_channels: dict[str, float] = {}

        for name, value in {
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
            "alpha": self.alpha,
        }.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"Color {name} channel must be a numeric value."
                )

            normalized_value = float(value)

            if not isfinite(normalized_value):
                raise ValueError(
                    f"Color {name} channel must be finite."
                )

            if not 0.0 <= normalized_value <= 1.0:
                raise ValueError(
                    f"Color {name} channel must be between 0.0 and 1.0."
                )

            normalized_channels[name] = normalized_value

        object.__setattr__(self, "red", normalized_channels["red"])
        object.__setattr__(self, "green", normalized_channels["green"])
        object.__setattr__(self, "blue", normalized_channels["blue"])
        object.__setattr__(self, "alpha", normalized_channels["alpha"])

    @classmethod
    def from_rgb255(
        cls,
        *,
        red: int,
        green: int,
        blue: int,
        alpha: int = 255,
    ) -> Color:
        """
        Create a color from integer channels in the interval 0 to 255.
        """

        channels = {
            "red": red,
            "green": green,
            "blue": blue,
            "alpha": alpha,
        }

        for name, value in channels.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"Color {name} channel must be an integer."
                )

            if not 0 <= value <= 255:
                raise ValueError(
                    f"Color {name} channel must be between 0 and 255."
                )

        return cls(
            red=red / 255.0,
            green=green / 255.0,
            blue=blue / 255.0,
            alpha=alpha / 255.0,
        )

    @classmethod
    def from_hex(cls, value: str) -> Color:
        """
        Create a color from hexadecimal RGB or RGBA notation.

        Accepted examples:

            #FFFFFF
            FFFFFF
            #FFFFFFFF
            FFFFFFFF
        """

        if not isinstance(value, str):
            raise TypeError(
                "Hex color value must be a string."
            )

        normalized_value = value.strip().removeprefix("#")

        if len(normalized_value) not in {6, 8}:
            raise ValueError(
                "Hex color must contain 6 or 8 hexadecimal characters."
            )

        try:
            red = int(normalized_value[0:2], 16)
            green = int(normalized_value[2:4], 16)
            blue = int(normalized_value[4:6], 16)

            alpha = (
                int(normalized_value[6:8], 16)
                if len(normalized_value) == 8
                else 255
            )
        except ValueError as exc:
            raise ValueError(
                "Hex color contains invalid hexadecimal characters."
            ) from exc

        return cls.from_rgb255(
            red=red,
            green=green,
            blue=blue,
            alpha=alpha,
        )

    @property
    def rgb(self) -> tuple[float, float, float]:
        return self.red, self.green, self.blue

    @property
    def rgba(self) -> tuple[float, float, float, float]:
        return self.red, self.green, self.blue, self.alpha

    @property
    def rgb255(self) -> tuple[int, int, int]:
        return (
            round(self.red * 255),
            round(self.green * 255),
            round(self.blue * 255),
        )

    @property
    def rgba255(self) -> tuple[int, int, int, int]:
        return (
            round(self.red * 255),
            round(self.green * 255),
            round(self.blue * 255),
            round(self.alpha * 255),
        )

    @property
    def is_fully_transparent(self) -> bool:
        return self.alpha == 0.0

    @property
    def is_fully_opaque(self) -> bool:
        return self.alpha == 1.0

    @property
    def relative_luminance(self) -> float:
        """
        Calculate WCAG relative luminance from the RGB channels.
        """

        red = self._linearized_channel(self.red)
        green = self._linearized_channel(self.green)
        blue = self._linearized_channel(self.blue)

        return (
            0.2126 * red
            + 0.7152 * green
            + 0.0722 * blue
        )

    def contrast_ratio(self, other: Color) -> float:
        """
        Return the WCAG contrast ratio between two colors.

        Alpha is intentionally not included in this method. When alpha
        composition is needed, composite_over should be called first.
        """

        self._validate_other_color(other)

        lighter = max(
            self.relative_luminance,
            other.relative_luminance,
        )
        darker = min(
            self.relative_luminance,
            other.relative_luminance,
        )

        return (lighter + 0.05) / (darker + 0.05)

    def distance(self, other: Color) -> float:
        """
        Return the normalized Euclidean distance between RGB channels.

        The result lies between 0.0 and 1.0.
        """

        self._validate_other_color(other)

        raw_distance = sqrt(
            ((self.red - other.red) ** 2)
            + ((self.green - other.green) ** 2)
            + ((self.blue - other.blue) ** 2)
        )

        return raw_distance / sqrt(3.0)

    def is_close_to(
        self,
        other: Color,
        *,
        threshold: float = 0.05,
    ) -> bool:
        """
        Return whether the RGB distance is below or equal to the threshold.
        """

        self._validate_other_color(other)

        if isinstance(threshold, bool) or not isinstance(
            threshold,
            (int, float),
        ):
            raise TypeError(
                "Color distance threshold must be numeric."
            )

        normalized_threshold = float(threshold)

        if not isfinite(normalized_threshold):
            raise ValueError(
                "Color distance threshold must be finite."
            )

        if not 0.0 <= normalized_threshold <= 1.0:
            raise ValueError(
                "Color distance threshold must be between 0.0 and 1.0."
            )

        return self.distance(other) <= normalized_threshold

    def composite_over(self, background: Color) -> Color:
        """
        Return this color alpha-composited over an opaque or translucent
        background.
        """

        self._validate_other_color(background)

        output_alpha = (
            self.alpha
            + background.alpha * (1.0 - self.alpha)
        )

        if output_alpha == 0.0:
            return Color(
                red=0.0,
                green=0.0,
                blue=0.0,
                alpha=0.0,
            )

        output_red = (
            self.red * self.alpha
            + background.red
            * background.alpha
            * (1.0 - self.alpha)
        ) / output_alpha

        output_green = (
            self.green * self.alpha
            + background.green
            * background.alpha
            * (1.0 - self.alpha)
        ) / output_alpha

        output_blue = (
            self.blue * self.alpha
            + background.blue
            * background.alpha
            * (1.0 - self.alpha)
        ) / output_alpha

        return Color(
            red=output_red,
            green=output_green,
            blue=output_blue,
            alpha=output_alpha,
        )

    def to_hex(
        self,
        *,
        include_alpha: bool = False,
    ) -> str:
        red, green, blue, alpha = self.rgba255

        if include_alpha:
            return f"#{red:02X}{green:02X}{blue:02X}{alpha:02X}"

        return f"#{red:02X}{green:02X}{blue:02X}"

    @staticmethod
    def _linearized_channel(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92

        return ((channel + 0.055) / 1.055) ** 2.4

    @staticmethod
    def _validate_other_color(other: Color) -> None:
        if not isinstance(other, Color):
            raise TypeError(
                "Color operation requires another Color."
            )