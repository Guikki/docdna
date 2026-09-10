from __future__ import annotations

from collections.abc import Iterable

from app.domain.fingerprints.qrcode_fingerprint import (
    QRCodeFingerprint,
)
from app.domain.models.barcode import Barcode
from app.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from app.services.qrcode_fingerprint_builder import (
    QRCodeFingerprintBuilder,
)


class QRCodeFingerprintProcessor:
    """
    Converte QR Codes já detectados pelo BarcodeReader
    em QRCodeFingerprint.

    O processor não relê o PDF e não executa novamente o ZXing.
    Ele apenas transforma fatos técnicos previamente extraídos
    em objetos do domínio.
    """

    QR_CODE_FORMATS = {
        "qr",
        "qrcode",
    }

    def __init__(
        self,
        builder: (
            QRCodeFingerprintBuilder
            | None
        ) = None,
    ) -> None:
        self._builder = (
            builder
            or QRCodeFingerprintBuilder()
        )

    def process(
        self,
        barcodes: Iterable[Barcode],
    ) -> list[QRCodeFingerprint]:
        fingerprints: list[
            QRCodeFingerprint
        ] = []

        confidence = ConfidenceScore(
            1.0
        )

        for barcode in barcodes:
            if not isinstance(
                barcode,
                Barcode,
            ):
                continue

            if not self._is_qrcode(
                barcode.format
            ):
                continue

            if barcode.location is None:
                continue

            fingerprints.append(
                self._builder.build(
                    location=(
                        barcode.location
                    ),
                    confidence=confidence,
                    value=barcode.content,
                    encoding=None,
                    version=None,
                    error_correction=(
                        barcode
                        .error_correction
                    ),
                    image_hash=(
                        barcode.image_hash
                    ),
                    rotation=(
                        barcode.orientation
                    ),
                )
            )

        return fingerprints

    def _is_qrcode(
        self,
        barcode_format: str,
    ) -> bool:
        normalized = (
            str(
                barcode_format
                or ""
            )
            .strip()
            .lower()
            .replace(
                "-",
                "",
            )
            .replace(
                "_",
                "",
            )
            .replace(
                " ",
                "",
            )
        )

        return (
            normalized
            in self.QR_CODE_FORMATS
        )
