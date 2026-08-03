from datetime import date

import pytest

from app.domain.detectors.temporal_evidence_detector import (
    TemporalEvidenceDetector,
)
from app.domain.models.detected_date import (
    DateSource,
    DetectedDate,
)
from app.domain.models.document_evidence import (
    EvidenceSeverity,
)
from app.domain.models.temporal_timeline import (
    TemporalTimeline,
)


def _build_detected_date(
    *,
    value: date,
    source: DateSource = DateSource.NATIVE_TEXT,
    document_id: str = "document-001",
    page_number: int | None = None,
    metadata_field: str | None = None,
    confidence: float = 1.0,
    raw_content: str | None = None,
) -> DetectedDate:
    return DetectedDate(
        value=value,
        raw_content=(
            raw_content
            if raw_content is not None
            else value.strftime("%d/%m/%Y")
        ),
        source=source,
        document_id=document_id,
        page_number=page_number,
        metadata_field=metadata_field,
        surrounding_text=None,
        confidence=confidence,
    )


def _build_timeline(
    *detected_dates: DetectedDate,
    document_id: str = "document-001",
) -> TemporalTimeline:
    return TemporalTimeline(
        document_id=document_id,
        dates=tuple(detected_dates),
    )


@pytest.fixture
def detector() -> TemporalEvidenceDetector:
    return TemporalEvidenceDetector()


def test_detect_returns_empty_when_timeline_is_empty(
    detector: TemporalEvidenceDetector,
) -> None:
    timeline = _build_timeline()

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert result == []


def test_detect_returns_empty_when_no_temporal_inconsistency_exists(
    detector: TemporalEvidenceDetector,
) -> None:
    timeline = _build_timeline(
        _build_detected_date(
            value=date(2026, 6, 1),
            source=DateSource.PDF_METADATA,
            metadata_field="creationDate",
        ),
        _build_detected_date(
            value=date(2026, 6, 2),
            source=DateSource.PDF_METADATA,
            metadata_field="modDate",
        ),
        _build_detected_date(
            value=date(2026, 6, 5),
            source=DateSource.NATIVE_TEXT,
            page_number=1,
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert result == []


def test_detect_identifies_modification_before_creation(
    detector: TemporalEvidenceDetector,
) -> None:
    timeline = _build_timeline(
        _build_detected_date(
            value=date(2026, 7, 20),
            source=DateSource.PDF_METADATA,
            metadata_field="creationDate",
        ),
        _build_detected_date(
            value=date(2026, 7, 18),
            source=DateSource.PDF_METADATA,
            metadata_field="modDate",
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert len(result) == 1

    evidence = result[0]

    assert (
        evidence.code
        == TemporalEvidenceDetector.INVALID_METADATA_ORDER_CODE
    )
    assert evidence.severity == EvidenceSeverity.HIGH
    assert evidence.confidence == 1.0
    assert evidence.source == "temporal_evidence_detector"
    assert evidence.metadata["creation_date"] == "2026-07-20"
    assert evidence.metadata["modification_date"] == "2026-07-18"


def test_detect_does_not_report_valid_metadata_order(
    detector: TemporalEvidenceDetector,
) -> None:
    timeline = _build_timeline(
        _build_detected_date(
            value=date(2026, 7, 18),
            source=DateSource.PDF_METADATA,
            metadata_field="creationDate",
        ),
        _build_detected_date(
            value=date(2026, 7, 20),
            source=DateSource.PDF_METADATA,
            metadata_field="modDate",
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert result == []


def test_detect_identifies_future_date(
    detector: TemporalEvidenceDetector,
) -> None:
    timeline = _build_timeline(
        _build_detected_date(
            value=date(2026, 8, 15),
            source=DateSource.NATIVE_TEXT,
            page_number=2,
            confidence=0.94,
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert len(result) == 1

    evidence = result[0]

    assert (
        evidence.code
        == TemporalEvidenceDetector.FUTURE_DATE_CODE
    )
    assert evidence.severity == EvidenceSeverity.MEDIUM
    assert evidence.confidence == 0.94
    assert evidence.metadata["reference_date"] == "2026-07-20"
    assert evidence.metadata["future_dates"] == ["2026-08-15"]
    assert evidence.metadata["occurrence_count"] == 1
    assert evidence.metadata["affected_pages"] == [2]


def test_detect_aggregates_multiple_future_dates(
    detector: TemporalEvidenceDetector,
) -> None:
    timeline = _build_timeline(
        _build_detected_date(
            value=date(2026, 8, 15),
            source=DateSource.NATIVE_TEXT,
            page_number=1,
            confidence=0.95,
        ),
        _build_detected_date(
            value=date(2026, 8, 15),
            source=DateSource.OCR,
            page_number=1,
            confidence=0.82,
        ),
        _build_detected_date(
            value=date(2026, 9, 1),
            source=DateSource.OCR,
            page_number=3,
            confidence=0.88,
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert len(result) == 1

    evidence = result[0]

    assert evidence.metadata["future_dates"] == [
        "2026-08-15",
        "2026-09-01",
    ]
    assert evidence.metadata["occurrence_count"] == 3
    assert evidence.metadata["affected_pages"] == [1, 3]
    assert evidence.confidence == 0.82

    assert set(evidence.metadata["sources"]) == {
        DateSource.NATIVE_TEXT.value,
        DateSource.OCR.value,
    }


def test_detect_does_not_report_reference_date_as_future(
    detector: TemporalEvidenceDetector,
) -> None:
    timeline = _build_timeline(
        _build_detected_date(
            value=date(2026, 7, 20),
            source=DateSource.NATIVE_TEXT,
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert result == []


def test_detect_identifies_excessive_temporal_range() -> None:
    detector = TemporalEvidenceDetector(
        maximum_expected_range_days=365,
    )

    timeline = _build_timeline(
        _build_detected_date(
            value=date(2020, 1, 1),
        ),
        _build_detected_date(
            value=date(2026, 1, 1),
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert len(result) == 1

    evidence = result[0]

    assert (
        evidence.code
        == TemporalEvidenceDetector.EXCESSIVE_RANGE_CODE
    )
    assert evidence.severity == EvidenceSeverity.LOW
    assert evidence.metadata["earliest_date"] == "2020-01-01"
    assert evidence.metadata["latest_date"] == "2026-01-01"
    assert evidence.metadata["interval_days"] > 365
    assert evidence.metadata["maximum_expected_range_days"] == 365


def test_detect_does_not_report_range_equal_to_limit() -> None:
    detector = TemporalEvidenceDetector(
        maximum_expected_range_days=10,
    )

    timeline = _build_timeline(
        _build_detected_date(
            value=date(2026, 7, 1),
        ),
        _build_detected_date(
            value=date(2026, 7, 11),
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert result == []


def test_detect_identifies_metadata_content_divergence() -> None:
    detector = TemporalEvidenceDetector(
        metadata_content_tolerance_days=365,
    )

    timeline = _build_timeline(
        _build_detected_date(
            value=date(2026, 7, 1),
            source=DateSource.PDF_METADATA,
            metadata_field="creationDate",
        ),
        _build_detected_date(
            value=date(2020, 7, 1),
            source=DateSource.NATIVE_TEXT,
            page_number=1,
            confidence=0.91,
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert len(result) == 1

    evidence = result[0]

    assert (
        evidence.code
        == TemporalEvidenceDetector.METADATA_CONTENT_DIVERGENCE_CODE
    )
    assert evidence.severity == EvidenceSeverity.MEDIUM
    assert evidence.confidence == 0.91
    assert evidence.metadata["metadata_date"] == "2026-07-01"
    assert evidence.metadata["metadata_field"] == "creationDate"
    assert evidence.metadata["content_date"] == "2020-07-01"
    assert evidence.metadata["content_source"] == (
        DateSource.NATIVE_TEXT.value
    )
    assert evidence.metadata["content_page"] == 1
    assert evidence.metadata["difference_days"] > 365
    assert evidence.metadata["tolerance_days"] == 365


def test_detect_does_not_compare_metadata_with_metadata() -> None:
    detector = TemporalEvidenceDetector(
        metadata_content_tolerance_days=30,
    )

    timeline = _build_timeline(
        _build_detected_date(
            value=date(2020, 1, 1),
            source=DateSource.PDF_METADATA,
            metadata_field="creationDate",
        ),
        _build_detected_date(
            value=date(2026, 1, 1),
            source=DateSource.PDF_METADATA,
            metadata_field="modDate",
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    divergence_evidences = [
        evidence
        for evidence in result
        if (
            evidence.code
            == TemporalEvidenceDetector.METADATA_CONTENT_DIVERGENCE_CODE
        )
    ]

    assert divergence_evidences == []


def test_detect_does_not_compare_content_with_content() -> None:
    detector = TemporalEvidenceDetector(
        metadata_content_tolerance_days=30,
    )

    timeline = _build_timeline(
        _build_detected_date(
            value=date(2020, 1, 1),
            source=DateSource.NATIVE_TEXT,
            page_number=1,
        ),
        _build_detected_date(
            value=date(2026, 1, 1),
            source=DateSource.OCR,
            page_number=2,
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    divergence_evidences = [
        evidence
        for evidence in result
        if (
            evidence.code
            == TemporalEvidenceDetector.METADATA_CONTENT_DIVERGENCE_CODE
        )
    ]

    assert divergence_evidences == []


def test_detect_can_return_multiple_evidences() -> None:
    detector = TemporalEvidenceDetector(
        maximum_expected_range_days=365,
        metadata_content_tolerance_days=365,
    )

    timeline = _build_timeline(
        _build_detected_date(
            value=date(2026, 7, 20),
            source=DateSource.PDF_METADATA,
            metadata_field="creationDate",
        ),
        _build_detected_date(
            value=date(2026, 7, 18),
            source=DateSource.PDF_METADATA,
            metadata_field="modDate",
        ),
        _build_detected_date(
            value=date(2020, 1, 1),
            source=DateSource.NATIVE_TEXT,
            page_number=1,
        ),
        _build_detected_date(
            value=date(2027, 1, 1),
            source=DateSource.OCR,
            page_number=2,
        ),
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    evidence_codes = {
        evidence.code
        for evidence in result
    }

    assert (
        TemporalEvidenceDetector.INVALID_METADATA_ORDER_CODE
        in evidence_codes
    )
    assert (
        TemporalEvidenceDetector.FUTURE_DATE_CODE
        in evidence_codes
    )
    assert (
        TemporalEvidenceDetector.EXCESSIVE_RANGE_CODE
        in evidence_codes
    )
    assert (
        TemporalEvidenceDetector.METADATA_CONTENT_DIVERGENCE_CODE
        in evidence_codes
    )


def test_detect_preserves_timeline_document_identifier(
    detector: TemporalEvidenceDetector,
) -> None:
    timeline = _build_timeline(
        _build_detected_date(
            value=date(2027, 1, 1),
            document_id="document-999",
        ),
        document_id="document-999",
    )

    result = detector.detect(
        timeline=timeline,
        reference_date=date(2026, 7, 20),
    )

    assert len(result) == 1

    evidence = result[0]

    assert "document-999" in evidence.document_ids


@pytest.mark.parametrize(
    "maximum_expected_range_days",
    [
        -1,
        -10,
    ],
)
def test_constructor_rejects_negative_range(
    maximum_expected_range_days: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="intervalo temporal máximo",
    ):
        TemporalEvidenceDetector(
            maximum_expected_range_days=(
                maximum_expected_range_days
            )
        )


@pytest.mark.parametrize(
    "metadata_content_tolerance_days",
    [
        -1,
        -30,
    ],
)
def test_constructor_rejects_negative_tolerance(
    metadata_content_tolerance_days: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="tolerância entre metadados",
    ):
        TemporalEvidenceDetector(
            metadata_content_tolerance_days=(
                metadata_content_tolerance_days
            )
        )