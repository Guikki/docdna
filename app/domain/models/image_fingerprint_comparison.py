from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImageFingerprintComparison:
    """
    Representa o resultado técnico da comparação entre
    dois fingerprints de imagem.

    Cada algoritmo mantém sua própria distância e similaridade,
    evitando que métricas diferentes sejam confundidas.

    Distância:
        quantidade de bits diferentes entre dois hashes.

    Similaridade:
        valor normalizado entre 0.0 e 1.0.
    """

    exact_image_match: bool

    perceptual_distance: int
    perceptual_similarity: float

    average_distance: int | None = None
    average_similarity: float | None = None

    difference_distance: int | None = None
    difference_similarity: float | None = None

    same_dimensions: bool = False

    width_difference: int = 0
    height_difference: int = 0

    def __post_init__(self) -> None:
        self._validate_distance(
            name="perceptual_distance",
            value=self.perceptual_distance,
        )

        self._validate_similarity(
            name="perceptual_similarity",
            value=self.perceptual_similarity,
        )

        self._validate_optional_metric(
            distance_name="average_distance",
            distance=self.average_distance,
            similarity_name="average_similarity",
            similarity=self.average_similarity,
        )

        self._validate_optional_metric(
            distance_name="difference_distance",
            distance=self.difference_distance,
            similarity_name="difference_similarity",
            similarity=self.difference_similarity,
        )

        if self.width_difference < 0:
            raise ValueError(
                "width_difference cannot be negative."
            )

        if self.height_difference < 0:
            raise ValueError(
                "height_difference cannot be negative."
            )

    @property
    def is_visually_identical(self) -> bool:
        """
        Considera identidade visual quando o perceptual hash
        não apresenta qualquer bit diferente.
        """

        return self.perceptual_distance == 0

    @property
    def has_average_hash_comparison(self) -> bool:
        return (
            self.average_distance is not None
            and self.average_similarity is not None
        )

    @property
    def has_difference_hash_comparison(self) -> bool:
        return (
            self.difference_distance is not None
            and self.difference_similarity is not None
        )

    @staticmethod
    def _validate_distance(
        *,
        name: str,
        value: int,
    ) -> None:
        if value < 0:
            raise ValueError(
                f"{name} cannot be negative."
            )

    @staticmethod
    def _validate_similarity(
        *,
        name: str,
        value: float,
    ) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{name} must be between 0.0 and 1.0."
            )

    @classmethod
    def _validate_optional_metric(
        cls,
        *,
        distance_name: str,
        distance: int | None,
        similarity_name: str,
        similarity: float | None,
    ) -> None:
        if (distance is None) != (similarity is None):
            raise ValueError(
                f"{distance_name} and {similarity_name} "
                "must both be informed or both be None."
            )

        if distance is not None:
            cls._validate_distance(
                name=distance_name,
                value=distance,
            )

        if similarity is not None:
            cls._validate_similarity(
                name=similarity_name,
                value=similarity,
            )