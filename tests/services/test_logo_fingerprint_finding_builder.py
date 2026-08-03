from __future__ import annotations

import pytest

from app.domain.fingerprints.logo_fingerprint import (
    LogoFingerprint,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationSeverity,
)
from app.domain.models.logo_fingerprint_comparison import (
    LogoFingerprintComparison,
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
from app.domain.services.logo_fingerprint_finding_builder import (
    LogoFingerprintFindingBuilder,
)


def make_logo(
    *,
    company_name: str | None,
    image_hash: str = "image-hash",
    perceptual_hash: str = "0000000000000000",
    average_hash: str | None = "1111111111111111",
    difference_hash: str | None = "2222222222222222",
    page_number: int = 1,
    width: int = 200,
    height: int = 100,
) -> LogoFingerprint:
    return LogoFingerprint(
        location=DocumentLocation(
            page_number=page_number,
            bounding_box=BoundingBox(
                x=10,
                y=20,
                width=width,
                height=height,
            ),
        ),
        confidence=ConfidenceScore(0.95),
        perceptual_hash=perceptual_hash,
        average_hash=average_hash,
        difference_hash=difference_hash,
        image_hash=image_hash,
        width=width,
        height=height,
        dpi=300,
        mime_type="image/png",
        description="Logo encontrado no documento.",
        company_name=company_name,
    )


def make_pair(
    *,
    first_company_name: str | None = "Empresa Alpha",
    second_company_name: str | None = "Empresa Alpha",
) -> LogoFingerprintPair:
    return LogoFingerprintPair(
        first_document_id="document-001",
        first_logo=make_logo(
            company_name=first_company_name,
            page_number=1,
        ),
        second_document_id="document-002",
        second_logo=make_logo(
            company_name=second_company_name,
            page_number=2,
        ),
    )


def make_comparison(
    *,
    exact_image_match: bool = False,
    perceptual_distance: int = 5,
    perceptual_similarity: float = 0.92,
    same_dimensions: bool = True,
    same_company_name: bool | None = True,
) -> LogoFingerprintComparison:
    return LogoFingerprintComparison(
        exact_image_match=exact_image_match,
        perceptual_distance=perceptual_distance,
        perceptual_similarity=perceptual_similarity,
        average_distance=4,
        average_similarity=0.93,
        difference_distance=6,
        difference_similarity=0.90,
        same_dimensions=same_dimensions,
        width_difference=0,
        height_difference=0,
        same_company_name=same_company_name,
    )


def test_build_returns_empty_list_for_no_match() -> None:
    builder = LogoFingerprintFindingBuilder()

    comparison = make_comparison(
        perceptual_distance=40,
        perceptual_similarity=0.30,
    )

    findings = builder.build(
        pair=make_pair(),
        comparison=comparison,
        comparator="LogoFingerprintCrossComparator",
    )

    assert findings == []


def test_build_creates_exact_match_finding() -> None:
    builder = LogoFingerprintFindingBuilder()

    comparison = make_comparison(
        exact_image_match=True,
        perceptual_distance=0,
        perceptual_similarity=1.0,
        same_company_name=True,
    )

    findings = builder.build(
        pair=make_pair(),
        comparison=comparison,
        comparator="LogoFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "LOGO_EXACT_MATCH"
    assert finding.severity is CrossValidationSeverity.INFO
    assert finding.confidence == 1.0
    assert finding.document_ids == [
        "document-001",
        "document-002",
    ]
    assert finding.metadata["classification"] == "exact"
    assert finding.metadata["same_company_name"] is True


def test_build_creates_strong_visual_match_finding() -> None:
    builder = LogoFingerprintFindingBuilder()

    comparison = make_comparison(
        exact_image_match=False,
        perceptual_distance=2,
        perceptual_similarity=0.98,
        same_company_name=True,
    )

    findings = builder.build(
        pair=make_pair(),
        comparison=comparison,
        comparator="LogoFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "LOGO_STRONG_VISUAL_MATCH"
    assert finding.severity is CrossValidationSeverity.MEDIUM
    assert finding.confidence == 0.98


def test_strong_match_with_different_dimensions_is_low() -> None:
    builder = LogoFingerprintFindingBuilder()

    comparison = make_comparison(
        exact_image_match=False,
        perceptual_distance=2,
        perceptual_similarity=0.98,
        same_dimensions=False,
        same_company_name=True,
    )

    findings = builder.build(
        pair=make_pair(),
        comparison=comparison,
        comparator="LogoFingerprintCrossComparator",
    )

    assert len(findings) == 1
    assert findings[0].severity is CrossValidationSeverity.LOW


def test_build_creates_visual_match_finding() -> None:
    builder = LogoFingerprintFindingBuilder()

    comparison = make_comparison(
        exact_image_match=False,
        perceptual_distance=5,
        perceptual_similarity=0.95,
        same_company_name=True,
    )

    findings = builder.build(
        pair=make_pair(),
        comparison=comparison,
        comparator="LogoFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "LOGO_VISUAL_MATCH"
    assert finding.severity is CrossValidationSeverity.LOW
    assert finding.confidence == 0.95


def test_company_name_mismatch_has_precedence_over_exact_match() -> None:
    builder = LogoFingerprintFindingBuilder()

    pair = make_pair(
        first_company_name="Empresa Alpha",
        second_company_name="Empresa Beta",
    )

    comparison = make_comparison(
        exact_image_match=True,
        perceptual_distance=0,
        perceptual_similarity=1.0,
        same_company_name=False,
    )

    findings = builder.build(
        pair=pair,
        comparison=comparison,
        comparator="LogoFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "LOGO_COMPANY_NAME_MISMATCH"
    assert finding.severity is CrossValidationSeverity.HIGH
    assert finding.confidence == 1.0
    assert "Empresa Alpha" in finding.description
    assert "Empresa Beta" in finding.description


def test_company_name_mismatch_with_strong_match_is_high() -> None:
    builder = LogoFingerprintFindingBuilder()

    pair = make_pair(
        first_company_name="Empresa Alpha",
        second_company_name="Empresa Beta",
    )

    comparison = make_comparison(
        exact_image_match=False,
        perceptual_distance=2,
        perceptual_similarity=0.98,
        same_company_name=False,
    )

    findings = builder.build(
        pair=pair,
        comparison=comparison,
        comparator="LogoFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "LOGO_COMPANY_NAME_MISMATCH"
    assert finding.severity is CrossValidationSeverity.HIGH
    assert finding.confidence == 0.98


def test_company_name_mismatch_with_moderate_match_is_medium() -> None:
    builder = LogoFingerprintFindingBuilder()

    pair = make_pair(
        first_company_name="Empresa Alpha",
        second_company_name="Empresa Beta",
    )

    comparison = make_comparison(
        exact_image_match=False,
        perceptual_distance=5,
        perceptual_similarity=0.95,
        same_company_name=False,
    )

    findings = builder.build(
        pair=pair,
        comparison=comparison,
        comparator="LogoFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "LOGO_COMPANY_NAME_MISMATCH"
    assert finding.severity is CrossValidationSeverity.MEDIUM
    assert finding.confidence == 0.95


def test_metadata_contains_logo_information() -> None:
    builder = LogoFingerprintFindingBuilder()

    pair = make_pair(
        first_company_name="Empresa Alpha",
        second_company_name="Empresa Beta",
    )

    comparison = make_comparison(
        exact_image_match=True,
        perceptual_distance=0,
        perceptual_similarity=1.0,
        same_company_name=False,
    )

    finding = builder.build(
        pair=pair,
        comparison=comparison,
        comparator="LogoFingerprintCrossComparator",
    )[0]

    first_logo = finding.metadata["first_logo"]
    second_logo = finding.metadata["second_logo"]

    assert first_logo["company_name"] == "Empresa Alpha"
    assert second_logo["company_name"] == "Empresa Beta"
    assert first_logo["page_number"] == 1
    assert second_logo["page_number"] == 2
    assert first_logo["width"] == 200
    assert first_logo["height"] == 100


def test_comparator_name_is_trimmed() -> None:
    builder = LogoFingerprintFindingBuilder()

    findings = builder.build(
        pair=make_pair(),
        comparison=make_comparison(
            exact_image_match=True,
            perceptual_distance=0,
            perceptual_similarity=1.0,
        ),
        comparator="  LogoFingerprintCrossComparator  ",
    )

    assert findings[0].comparator == (
        "LogoFingerprintCrossComparator"
    )


@pytest.mark.parametrize(
    "comparator",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_empty_comparator_name_raises_value_error(
    comparator: str,
) -> None:
    builder = LogoFingerprintFindingBuilder()

    with pytest.raises(
        ValueError,
        match="comparator cannot be empty",
    ):
        builder.build(
            pair=make_pair(),
            comparison=make_comparison(
                exact_image_match=True,
                perceptual_distance=0,
                perceptual_similarity=1.0,
            ),
            comparator=comparator,
        )