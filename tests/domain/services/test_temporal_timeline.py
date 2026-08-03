from datetime import date

import pytest

from app.domain.models.detected_date import (
    DateSource,
    DetectedDate,
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
) -> DetectedDate:
    return DetectedDate(
        value=value,
        raw_content=value.strftime("%d/%m/%Y"),
        source=source,
        document_id=document_id,
        page_number=page_number,
        metadata_field=None,
        surrounding_text=None,
        confidence=1.0,
    )


def test_timeline_is_empty_when_no_dates_exist() -> None:
    timeline = TemporalTimeline(
        document_id="document-001",
        dates=(),
    )

    assert timeline.is_empty is True
    assert timeline.total_dates == 0
    assert timeline.earliest_date is None
    assert timeline.latest_date is None


def test_timeline_returns_total_dates() -> None:
    timeline = TemporalTimeline(
        document_id="document-001",
        dates=(
            _build_detected_date(value=date(2026, 6, 17)),
            _build_detected_date(value=date(2026, 6, 25)),
        ),
    )

    assert timeline.total_dates == 2


def test_timeline_returns_earliest_and_latest_dates() -> None:
    timeline = TemporalTimeline(
        document_id="document-001",
        dates=(
            _build_detected_date(value=date(2026, 6, 25)),
            _build_detected_date(value=date(2026, 6, 17)),
            _build_detected_date(value=date(2026, 6, 20)),
        ),
    )

    assert timeline.earliest_date == date(2026, 6, 17)
    assert timeline.latest_date == date(2026, 6, 25)


def test_timeline_filters_dates_by_source() -> None:
    timeline = TemporalTimeline(
        document_id="document-001",
        dates=(
            _build_detected_date(
                value=date(2026, 6, 17),
                source=DateSource.NATIVE_TEXT,
            ),
            _build_detected_date(
                value=date(2026, 6, 18),
                source=DateSource.OCR,
            ),
            _build_detected_date(
                value=date(2026, 6, 19),
                source=DateSource.OCR,
            ),
        ),
    )

    result = timeline.dates_from_source(
        DateSource.OCR,
    )

    assert len(result) == 2

    assert all(
        detected.source == DateSource.OCR
        for detected in result
    )


def test_timeline_filters_dates_by_page() -> None:
    timeline = TemporalTimeline(
        document_id="document-001",
        dates=(
            _build_detected_date(
                value=date(2026, 6, 17),
                page_number=1,
            ),
            _build_detected_date(
                value=date(2026, 6, 18),
                page_number=2,
            ),
            _build_detected_date(
                value=date(2026, 6, 19),
                page_number=2,
            ),
        ),
    )

    result = timeline.dates_from_page(2)

    assert len(result) == 2

    assert all(
        detected.page_number == 2
        for detected in result
    )


def test_timeline_filters_dates_by_value() -> None:
    target = date(2026, 6, 17)

    timeline = TemporalTimeline(
        document_id="document-001",
        dates=(
            _build_detected_date(value=target),
            _build_detected_date(
                value=target,
                source=DateSource.OCR,
            ),
            _build_detected_date(
                value=date(2026, 6, 18),
            ),
        ),
    )

    result = timeline.dates_with_value(target)

    assert len(result) == 2


def test_timeline_returns_distinct_values_sorted() -> None:
    timeline = TemporalTimeline(
        document_id="document-001",
        dates=(
            _build_detected_date(value=date(2026, 6, 25)),
            _build_detected_date(value=date(2026, 6, 17)),
            _build_detected_date(value=date(2026, 6, 17)),
            _build_detected_date(value=date(2026, 6, 20)),
        ),
    )

    assert timeline.distinct_values() == (
        date(2026, 6, 17),
        date(2026, 6, 20),
        date(2026, 6, 25),
    )


def test_timeline_has_source_returns_true_when_present() -> None:
    timeline = TemporalTimeline(
        document_id="document-001",
        dates=(
            _build_detected_date(
                value=date(2026, 6, 17),
                source=DateSource.PDF_METADATA,
            ),
        ),
    )

    assert timeline.has_source(
        DateSource.PDF_METADATA
    ) is True


def test_timeline_has_source_returns_false_when_absent() -> None:
    timeline = TemporalTimeline(
        document_id="document-001",
        dates=(
            _build_detected_date(
                value=date(2026, 6, 17),
                source=DateSource.NATIVE_TEXT,
            ),
        ),
    )

    assert timeline.has_source(
        DateSource.OCR
    ) is False


def test_timeline_rejects_dates_from_different_documents() -> None:
    with pytest.raises(ValueError):
        TemporalTimeline(
            document_id="document-001",
            dates=(
                _build_detected_date(
                    value=date(2026, 6, 17),
                    document_id="document-001",
                ),
                _build_detected_date(
                    value=date(2026, 6, 18),
                    document_id="document-002",
                ),
            ),
        )