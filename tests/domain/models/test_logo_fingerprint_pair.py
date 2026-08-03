from __future__ import annotations

import pytest

from app.domain.fingerprints.logo_fingerprint import (
    LogoFingerprint,
)
from app.domain.models.logo_fingerprint_pair import (
    LogoFingerprintPair,
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


def create_logo() -> LogoFingerprint:
    return LogoFingerprint(
        location=DocumentLocation(
            page_number=1,
            bounding_box=BoundingBox(
                x=0,
                y=0,
                width=100,
                height=50,
            ),
        ),
        confidence=ConfidenceScore(
            value=1.0,
        ),
        perceptual_hash="0123456789abcdef",
        average_hash="0123456789abcdef",
        difference_hash="0123456789abcdef",
        image_hash="abcdef",
        width=100,
        height=50,
        company_name="OpenAI",
    )


def test_should_create_logo_pair() -> None:
    first_logo = create_logo()
    second_logo = create_logo()

    pair = LogoFingerprintPair(
        first_document_id="doc-1",
        second_document_id="doc-2",
        first_logo=first_logo,
        second_logo=second_logo,
    )

    assert pair.first_document_id == "doc-1"
    assert pair.second_document_id == "doc-2"
    assert pair.first_logo is first_logo
    assert pair.second_logo is second_logo


def test_should_trim_document_ids() -> None:
    pair = LogoFingerprintPair(
        first_document_id=" doc-1 ",
        second_document_id=" doc-2 ",
        first_logo=create_logo(),
        second_logo=create_logo(),
    )

    assert pair.first_document_id == "doc-1"
    assert pair.second_document_id == "doc-2"


@pytest.mark.parametrize(
    "document_id",
    [
        "",
        "   ",
    ],
)
def test_should_not_allow_empty_first_document_id(
    document_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="first_document_id cannot be empty.",
    ):
        LogoFingerprintPair(
            first_document_id=document_id,
            second_document_id="doc-2",
            first_logo=create_logo(),
            second_logo=create_logo(),
        )


@pytest.mark.parametrize(
    "document_id",
    [
        "",
        "   ",
    ],
)
def test_should_not_allow_empty_second_document_id(
    document_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="second_document_id cannot be empty.",
    ):
        LogoFingerprintPair(
            first_document_id="doc-1",
            second_document_id=document_id,
            first_logo=create_logo(),
            second_logo=create_logo(),
        )


def test_should_not_allow_same_document() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "logo fingerprints must belong "
            "to different documents."
        ),
    ):
        LogoFingerprintPair(
            first_document_id="doc",
            second_document_id="doc",
            first_logo=create_logo(),
            second_logo=create_logo(),
        )