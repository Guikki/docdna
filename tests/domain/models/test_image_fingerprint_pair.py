from __future__ import annotations

import pytest

from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.models.image_fingerprint_pair import (
    ImageFingerprintPair,
)
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from app.domain.value_objects.document_location import (
    DocumentLocation,
)


def create_fingerprint(
    *,
    perceptual_hash: str = "0000000000000000",
    page_number: int = 1,
) -> ImageFingerprint:
    return ImageFingerprint(
        location=DocumentLocation(
            page_number=page_number,
            bounding_box=BoundingBox(
                x=0.0,
                y=0.0,
                width=640.0,
                height=480.0,
            ),
        ),
        confidence=ConfidenceScore(1.0),
        perceptual_hash=perceptual_hash,
        average_hash="0000000000000000",
        difference_hash="0000000000000000",
        image_hash="a" * 64,
        width=640,
        height=480,
        mime_type="image/png",
    )


def test_should_create_image_fingerprint_pair() -> None:
    first_image = create_fingerprint(
        perceptual_hash="0000000000000000",
    )

    second_image = create_fingerprint(
        perceptual_hash="0000000000000001",
    )

    pair = ImageFingerprintPair(
        first_document_id="document-1",
        second_document_id="document-2",
        first_image=first_image,
        second_image=second_image,
    )

    assert pair.first_document_id == "document-1"
    assert pair.second_document_id == "document-2"
    assert pair.first_image is first_image
    assert pair.second_image is second_image


def test_should_normalize_document_ids() -> None:
    pair = ImageFingerprintPair(
        first_document_id=" document-1 ",
        second_document_id=" document-2 ",
        first_image=create_fingerprint(),
        second_image=create_fingerprint(),
    )

    assert pair.first_document_id == "document-1"
    assert pair.second_document_id == "document-2"


@pytest.mark.parametrize(
    "first_document_id,second_document_id,error_message",
    [
        (
            "",
            "document-2",
            "first_document_id cannot be empty",
        ),
        (
            "   ",
            "document-2",
            "first_document_id cannot be empty",
        ),
        (
            "document-1",
            "",
            "second_document_id cannot be empty",
        ),
        (
            "document-1",
            "   ",
            "second_document_id cannot be empty",
        ),
    ],
)
def test_should_reject_empty_document_ids(
    first_document_id: str,
    second_document_id: str,
    error_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=error_message,
    ):
        ImageFingerprintPair(
            first_document_id=first_document_id,
            second_document_id=second_document_id,
            first_image=create_fingerprint(),
            second_image=create_fingerprint(),
        )


def test_should_reject_images_from_same_document() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "image fingerprints must belong to "
            "different documents"
        ),
    ):
        ImageFingerprintPair(
            first_document_id="document-1",
            second_document_id="document-1",
            first_image=create_fingerprint(),
            second_image=create_fingerprint(),
        )


def test_should_reject_same_document_after_normalization() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "image fingerprints must belong to "
            "different documents"
        ),
    ):
        ImageFingerprintPair(
            first_document_id=" document-1 ",
            second_document_id="document-1",
            first_image=create_fingerprint(),
            second_image=create_fingerprint(),
        )