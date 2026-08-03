from __future__ import annotations

from app.domain.fingerprints.qrcode_fingerprint import (
    QRCodeFingerprint,
)
from app.domain.models.qrcode_fingerprint_comparison import (
    QRCodeFingerprintComparison,
)


class QRCodeFingerprintComparator:
    """
    Compara dois QRCodeFingerprint.

    O componente realiza apenas comparação técnica,
    sem produzir findings ou classificar fraude.
    """

    def compare(
        self,
        first: QRCodeFingerprint,
        second: QRCodeFingerprint,
    ) -> QRCodeFingerprintComparison:

        return QRCodeFingerprintComparison(
            exact_image_match=self._same_image_hash(
                first.image_hash,
                second.image_hash,
            ),
            same_value=self._same_required_text(
                first.value,
                second.value,
            ),
            same_encoding=self._same_optional_text(
                first.encoding,
                second.encoding,
            ),
            same_version=self._same_optional_value(
                first.version,
                second.version,
            ),
            same_error_correction=self._same_optional_text(
                first.error_correction,
                second.error_correction,
            ),
            rotation_difference=abs(
                first.rotation
                - second.rotation
            ),
        )

    @staticmethod
    def _same_image_hash(
        first: str | None,
        second: str | None,
    ) -> bool:

        if first is None or second is None:
            return False

        first = first.strip().lower()
        second = second.strip().lower()

        if not first or not second:
            return False

        return first == second

    @staticmethod
    def _same_required_text(
        first: str,
        second: str,
    ) -> bool:

        return (
            first.strip().casefold()
            == second.strip().casefold()
        )

    @staticmethod
    def _same_optional_text(
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

    @staticmethod
    def _same_optional_value(
        first: int | None,
        second: int | None,
    ) -> bool | None:

        if first is None or second is None:
            return None

        return first == second