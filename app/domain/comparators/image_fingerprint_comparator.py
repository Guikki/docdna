from __future__ import annotations

from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)


class ImageFingerprintComparator:
    """
    Compara dois fingerprints de imagem.

    O comparador utiliza:

    - image_hash para igualdade criptográfica exata;
    - perceptual_hash para semelhança visual;
    - average_hash para semelhança global;
    - difference_hash para semelhança de gradientes;
    - dimensões para apoio estrutural.

    O componente não classifica fraude e não produz evidências.
    """

    def compare(
        self,
        first: ImageFingerprint,
        second: ImageFingerprint,
    ) -> ImageFingerprintComparison:
        perceptual_distance, perceptual_similarity = (
            self._compare_required_hashes(
                first.perceptual_hash,
                second.perceptual_hash,
                hash_name="perceptual_hash",
            )
        )

        average_result = self._compare_optional_hashes(
            first.average_hash,
            second.average_hash,
            hash_name="average_hash",
        )

        difference_result = self._compare_optional_hashes(
            first.difference_hash,
            second.difference_hash,
            hash_name="difference_hash",
        )

        average_distance, average_similarity = average_result
        difference_distance, difference_similarity = difference_result

        width_difference = abs(first.width - second.width)
        height_difference = abs(first.height - second.height)

        return ImageFingerprintComparison(
            exact_image_match=self._has_exact_image_match(
                first.image_hash,
                second.image_hash,
            ),
            perceptual_distance=perceptual_distance,
            perceptual_similarity=perceptual_similarity,
            average_distance=average_distance,
            average_similarity=average_similarity,
            difference_distance=difference_distance,
            difference_similarity=difference_similarity,
            same_dimensions=(
                first.width == second.width
                and first.height == second.height
            ),
            width_difference=width_difference,
            height_difference=height_difference,
        )

    @staticmethod
    def _has_exact_image_match(
        first_hash: str | None,
        second_hash: str | None,
    ) -> bool:
        """
        Só existe igualdade criptográfica quando ambos os hashes
        estão presentes e possuem exatamente o mesmo conteúdo.
        """

        if first_hash is None or second_hash is None:
            return False

        first_normalized = first_hash.strip().lower()
        second_normalized = second_hash.strip().lower()

        if not first_normalized or not second_normalized:
            return False

        return first_normalized == second_normalized

    def _compare_required_hashes(
        self,
        first_hash: str,
        second_hash: str,
        *,
        hash_name: str,
    ) -> tuple[int, float]:
        return self._calculate_hash_metrics(
            first_hash=first_hash,
            second_hash=second_hash,
            hash_name=hash_name,
        )

    def _compare_optional_hashes(
        self,
        first_hash: str | None,
        second_hash: str | None,
        *,
        hash_name: str,
    ) -> tuple[int | None, float | None]:
        """
        Uma métrica opcional só é calculada quando os dois
        fingerprints possuem aquele tipo de hash.
        """

        if first_hash is None or second_hash is None:
            return None, None

        return self._calculate_hash_metrics(
            first_hash=first_hash,
            second_hash=second_hash,
            hash_name=hash_name,
        )

    def _calculate_hash_metrics(
        self,
        *,
        first_hash: str,
        second_hash: str,
        hash_name: str,
    ) -> tuple[int, float]:
        first_normalized = self._normalize_hash(
            first_hash,
            hash_name=hash_name,
        )

        second_normalized = self._normalize_hash(
            second_hash,
            hash_name=hash_name,
        )

        if len(first_normalized) != len(second_normalized):
            raise ValueError(
                f"{hash_name} values must have the same length."
            )

        total_bits = len(first_normalized) * 4

        first_value = int(first_normalized, 16)
        second_value = int(second_normalized, 16)

        distance = (
            first_value ^ second_value
        ).bit_count()

        similarity = 1.0 - (distance / total_bits)

        return distance, similarity

    @staticmethod
    def _normalize_hash(
        value: str,
        *,
        hash_name: str,
    ) -> str:
        normalized = value.strip().lower()

        if not normalized:
            raise ValueError(
                f"{hash_name} cannot be empty."
            )

        try:
            int(normalized, 16)
        except ValueError as error:
            raise ValueError(
                f"{hash_name} must be a hexadecimal string."
            ) from error

        return normalized