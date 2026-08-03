from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """
    Immutable rectangular region expressed in document coordinates.

    Coordinates follow the edge-based representation:

        left, top, right, bottom

    The class does not assume a specific coordinate origin. Readers and
    normalizers are responsible for converting source-library coordinates
    into a consistent document coordinate system.
    """

    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        coordinates = {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
        }

        for name, value in coordinates.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"BoundingBox {name} must be a numeric value."
                )

            if not isfinite(float(value)):
                raise ValueError(
                    f"BoundingBox {name} must be finite."
                )

        normalized_left = float(self.left)
        normalized_top = float(self.top)
        normalized_right = float(self.right)
        normalized_bottom = float(self.bottom)

        if normalized_right < normalized_left:
            raise ValueError(
                "BoundingBox right cannot be lower than left."
            )

        if normalized_bottom < normalized_top:
            raise ValueError(
                "BoundingBox bottom cannot be lower than top."
            )

        object.__setattr__(self, "left", normalized_left)
        object.__setattr__(self, "top", normalized_top)
        object.__setattr__(self, "right", normalized_right)
        object.__setattr__(self, "bottom", normalized_bottom)

    @classmethod
    def from_position_and_size(
        cls,
        *,
        left: float,
        top: float,
        width: float,
        height: float,
    ) -> BoundingBox:
        """
        Create a bounding box from its top-left position and dimensions.
        """

        for name, value in {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"BoundingBox {name} must be a numeric value."
                )

            if not isfinite(float(value)):
                raise ValueError(
                    f"BoundingBox {name} must be finite."
                )

        normalized_width = float(width)
        normalized_height = float(height)

        if normalized_width < 0.0:
            raise ValueError(
                "BoundingBox width cannot be negative."
            )

        if normalized_height < 0.0:
            raise ValueError(
                "BoundingBox height cannot be negative."
            )

        normalized_left = float(left)
        normalized_top = float(top)

        return cls(
            left=normalized_left,
            top=normalized_top,
            right=normalized_left + normalized_width,
            bottom=normalized_top + normalized_height,
        )

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center_x(self) -> float:
        return self.left + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        return self.top + (self.height / 2.0)

    @property
    def center(self) -> tuple[float, float]:
        return self.center_x, self.center_y

    @property
    def has_area(self) -> bool:
        return self.width > 0.0 and self.height > 0.0

    def contains_point(
        self,
        *,
        x: float,
        y: float,
        inclusive: bool = True,
    ) -> bool:
        """
        Return whether a point lies inside the bounding box.

        When inclusive is True, points on the edges are considered contained.
        """

        normalized_x = self._validate_numeric_coordinate(
            name="x",
            value=x,
        )
        normalized_y = self._validate_numeric_coordinate(
            name="y",
            value=y,
        )

        if inclusive:
            return (
                self.left <= normalized_x <= self.right
                and self.top <= normalized_y <= self.bottom
            )

        return (
            self.left < normalized_x < self.right
            and self.top < normalized_y < self.bottom
        )

    def contains_box(
        self,
        other: BoundingBox,
        *,
        inclusive: bool = True,
    ) -> bool:
        """
        Return whether another box is entirely contained by this box.
        """

        self._validate_other_box(other)

        if inclusive:
            return (
                self.left <= other.left
                and self.top <= other.top
                and self.right >= other.right
                and self.bottom >= other.bottom
            )

        return (
            self.left < other.left
            and self.top < other.top
            and self.right > other.right
            and self.bottom > other.bottom
        )

    def intersects(
        self,
        other: BoundingBox,
        *,
        include_edges: bool = False,
    ) -> bool:
        """
        Return whether this box intersects another box.

        By default, touching edges are not treated as an intersection with
        positive area. Set include_edges=True to treat edge contact as an
        intersection.
        """

        self._validate_other_box(other)

        if include_edges:
            return not (
                self.right < other.left
                or self.left > other.right
                or self.bottom < other.top
                or self.top > other.bottom
            )

        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.bottom <= other.top
            or self.top >= other.bottom
        )

    def intersection(
        self,
        other: BoundingBox,
    ) -> BoundingBox | None:
        """
        Return the positive-area intersection between two boxes.

        Returns None when the boxes do not overlap with positive area.
        """

        self._validate_other_box(other)

        left = max(self.left, other.left)
        top = max(self.top, other.top)
        right = min(self.right, other.right)
        bottom = min(self.bottom, other.bottom)

        if right <= left or bottom <= top:
            return None

        return BoundingBox(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        )

    def intersection_area(
        self,
        other: BoundingBox,
    ) -> float:
        intersection = self.intersection(other)

        if intersection is None:
            return 0.0

        return intersection.area

    def intersection_ratio(
        self,
        other: BoundingBox,
    ) -> float:
        """
        Return how much of this box is covered by the intersection.

        The ratio is relative to this instance, not to the union of both boxes.
        """

        self._validate_other_box(other)

        if not self.has_area:
            return 0.0

        return self.intersection_area(other) / self.area

    def iou(
        self,
        other: BoundingBox,
    ) -> float:
        """
        Return the Intersection over Union ratio.
        """

        self._validate_other_box(other)

        intersection_area = self.intersection_area(other)
        union_area = self.area + other.area - intersection_area

        if union_area <= 0.0:
            return 0.0

        return intersection_area / union_area

    def translated(
        self,
        *,
        delta_x: float = 0.0,
        delta_y: float = 0.0,
    ) -> BoundingBox:
        normalized_delta_x = self._validate_numeric_coordinate(
            name="delta_x",
            value=delta_x,
        )
        normalized_delta_y = self._validate_numeric_coordinate(
            name="delta_y",
            value=delta_y,
        )

        return BoundingBox(
            left=self.left + normalized_delta_x,
            top=self.top + normalized_delta_y,
            right=self.right + normalized_delta_x,
            bottom=self.bottom + normalized_delta_y,
        )

    @staticmethod
    def _validate_other_box(other: BoundingBox) -> None:
        if not isinstance(other, BoundingBox):
            raise TypeError(
                "BoundingBox operation requires another BoundingBox."
            )

    @staticmethod
    def _validate_numeric_coordinate(
        *,
        name: str,
        value: float,
    ) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(
                f"BoundingBox {name} must be a numeric value."
            )

        normalized_value = float(value)

        if not isfinite(normalized_value):
            raise ValueError(
                f"BoundingBox {name} must be finite."
            )

        return normalized_value