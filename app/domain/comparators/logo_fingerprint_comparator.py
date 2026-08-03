from __future__ import annotations

from app.domain.comparators.image_fingerprint_comparator import (
    ImageFingerprintComparator,
)
from app.domain.fingerprints.logo_fingerprint import (
    LogoFingerprint,
)
from app.domain.models.logo_fingerprint_comparison import (
    LogoFingerprintComparison,
)


class LogoFingerprintComparator:
    """
    Compara dois LogoFingerprint.

    Toda a comparação visual é delegada ao
    ImageFingerprintComparator.

    Este componente apenas acrescenta a
    comparação do nome da empresa.
    """

    def __init__(self) -> None:
        self._image_comparator = (
            ImageFingerprintComparator()
        )

    def compare(
        self,
        first: LogoFingerprint,
        second: LogoFingerprint,
    ) -> LogoFingerprintComparison:

        image_result = (
            self._image_comparator.compare(
                first,
                second,
            )
        )

        return LogoFingerprintComparison(
            exact_image_match=image_result.exact_image_match,
            perceptual_distance=image_result.perceptual_distance,
            perceptual_similarity=image_result.perceptual_similarity,
            average_distance=image_result.average_distance,
            average_similarity=image_result.average_similarity,
            difference_distance=image_result.difference_distance,
            difference_similarity=image_result.difference_similarity,
            same_dimensions=image_result.same_dimensions,
            width_difference=image_result.width_difference,
            height_difference=image_result.height_difference,
            same_company_name=self._compare_company_name(
                first.company_name,
                second.company_name,
            ),
        )

    @staticmethod
    def _compare_company_name(
        first: str | None,
        second: str | None,
    ) -> bool | None:

        if first is None or second is None:
            return None

        first = first.strip()
        second = second.strip()

        if not first or not second:
            return None

        return (
            first.casefold()
            == second.casefold()
        )