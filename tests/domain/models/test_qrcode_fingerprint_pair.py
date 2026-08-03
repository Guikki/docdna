from __future__ import annotations

import pytest

from app.domain.fingerprints.qrcode_fingerprint import (
    QRCodeFingerprint,
)
from app.domain.models.qrcode_fingerprint_pair import (
    QRCodeFingerprintPair,
)
from app.domain.value_objects.bounding_box import (
    BoundingBox,
)
from app.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from app.domain.value_objects.document_location import (
    DocumentLocation,
)


def make_qrcode(
    value: str = "PIX|123456789",
) -> QRCodeFingerprint:
    return QRCodeFingerprint(
        location=DocumentLocation(
            page_number=1,
            bounding_box=BoundingBox(
                x=10,
                y=20,
                width=120,
                height=120,
            ),
        ),
        confidence=ConfidenceScore(
            value=0.99,
        ),
        value=value,
        encoding="QR_CODE",
        version=5,
        error_correction="M",
        image_hash="abcdef",
        rotation=0.0,
    )


def test_should_create_pair() -> None:
    first_qrcode = make_qrcode(
        value="PIX|FIRST",
    )
    second_qrcode = make_qrcode(
        value="PIX|SECOND",
    )

    pair = QRCodeFingerprintPair(
        first_document_id="document-1",
        second_document_id="document-2",
        first_qrcode=first_qrcode,
        second_qrcode=second_qrcode,
    )

    assert pair.first_document_id == "document-1"
    assert pair.second_document_id == "document-2"
    assert pair.first_qrcode is first_qrcode
    assert pair.second_qrcode is second_qrcode


def test_should_trim_document_ids() -> None:
    pair = QRCodeFingerprintPair(
        first_document_id=" document-1 ",
        second_document_id=" document-2 ",
        first_qrcode=make_qrcode(),
        second_qrcode=make_qrcode(),
    )

    assert pair.first_document_id == "document-1"
    assert pair.second_document_id == "document-2"


@pytest.mark.parametrize(
    "document_id",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_should_not_allow_empty_first_document_id(
    document_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="first_document_id cannot be empty.",
    ):
        QRCodeFingerprintPair(
            first_document_id=document_id,
            second_document_id="document-2",
            first_qrcode=make_qrcode(),
            second_qrcode=make_qrcode(),
        )


@pytest.mark.parametrize(
    "document_id",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_should_not_allow_empty_second_document_id(
    document_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="second_document_id cannot be empty.",
    ):
        QRCodeFingerprintPair(
            first_document_id="document-1",
            second_document_id=document_id,
            first_qrcode=make_qrcode(),
            second_qrcode=make_qrcode(),
        )


def test_should_require_different_documents() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "QR Code fingerprints must belong "
            "to different documents."
        ),
    ):
        QRCodeFingerprintPair(
            first_document_id="document-1",
            second_document_id="document-1",
            first_qrcode=make_qrcode(),
            second_qrcode=make_qrcode(),
        )