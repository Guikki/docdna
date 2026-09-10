from __future__ import annotations

from app.domain.models.barcode import Barcode
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.document_location import (
    DocumentLocation,
)
from app.processors.qrcode_fingerprint_processor import (
    QRCodeFingerprintProcessor,
)


def _location(
    page_number: int = 1,
) -> DocumentLocation:
    return DocumentLocation(
        page_number=page_number,
        bounding_box=BoundingBox(
            x=10.0,
            y=20.0,
            width=120.0,
            height=120.0,
        ),
    )


def _barcode(
    *,
    barcode_format: str = "QRCode",
    content: str = "https://docdna.local",
    location: DocumentLocation | None = None,
    image_hash: str | None = "a" * 64,
    orientation: float = 90.0,
    error_correction: str | None = "M",
) -> Barcode:
    return Barcode(
        barcode_index=1,
        page_number=1,
        format=barcode_format,
        content=content,
        location=(
            location
            if location is not None
            else _location()
        ),
        image_hash=image_hash,
        orientation=orientation,
        error_correction=error_correction,
    )


def test_should_build_qrcode_fingerprint_from_detected_barcode(
) -> None:
    fingerprint = (
        QRCodeFingerprintProcessor()
        .process(
            [
                _barcode()
            ]
        )[0]
    )

    assert (
        fingerprint.value
        == "https://docdna.local"
    )
    assert (
        fingerprint.location
        == _location()
    )
    assert (
        fingerprint.confidence.value
        == 1.0
    )
    assert (
        fingerprint.image_hash
        == "a" * 64
    )
    assert (
        fingerprint.error_correction
        == "M"
    )
    assert (
        fingerprint.rotation
        == 90.0
    )

    assert fingerprint.encoding is None
    assert fingerprint.version is None


def test_should_ignore_non_qrcode_barcodes(
) -> None:
    result = (
        QRCodeFingerprintProcessor()
        .process(
            [
                _barcode(
                    barcode_format="ITF",
                )
            ]
        )
    )

    assert result == []


def test_should_accept_common_qrcode_format_variants(
) -> None:
    processor = (
        QRCodeFingerprintProcessor()
    )

    for barcode_format in (
        "QRCode",
        "QR Code",
        "QR_CODE",
        "qr-code",
    ):
        result = processor.process(
            [
                _barcode(
                    barcode_format=(
                        barcode_format
                    ),
                )
            ]
        )

        assert len(result) == 1


def test_should_ignore_qrcode_without_real_location(
) -> None:
    barcode = Barcode(
        barcode_index=1,
        page_number=1,
        format="QRCode",
        content="https://docdna.local",
        location=None,
    )

    result = (
        QRCodeFingerprintProcessor()
        .process(
            [
                barcode
            ]
        )
    )

    assert result == []


def test_should_ignore_invalid_items_without_breaking_valid_items(
) -> None:
    valid = _barcode()

    result = (
        QRCodeFingerprintProcessor()
        .process(
            [
                None,
                "invalid",
                valid,
            ]
        )
    )

    assert len(result) == 1
    assert result[0].value == valid.content


def test_should_return_empty_collection_when_no_barcodes_exist(
) -> None:
    assert (
        QRCodeFingerprintProcessor()
        .process(
            []
        )
        == []
    )
