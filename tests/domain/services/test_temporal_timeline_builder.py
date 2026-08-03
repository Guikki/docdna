from datetime import date

import pytest

from app.domain.models.detected_date import (
    DateSource,
    DetectedDate,
)
from app.domain.services.temporal_timeline_builder import (
    TemporalTimelineBuilder,
)


def _build_detected_date(
    *,
    value: date,
    document_id: str = "document-001",
    source: DateSource = DateSource.NATIVE_TEXT,
    page_number: int | None = None,
    metadata_field: str | None = None,
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
        confidence=1.0,
    )


@pytest.fixture
def builder() -> TemporalTimelineBuilder:
    return TemporalTimelineBuilder()


def test_build_returns_empty_timeline(
    builder: TemporalTimelineBuilder,
) -> None:
    timeline = builder.build(
        document_id="document-001",
        detected_dates=[],
    )

    assert timeline.document_id == "document-001"
    assert timeline.dates == ()
    assert timeline.is_empty is True


def test_build_orders_dates_chronologically(
    builder: TemporalTimelineBuilder,
) -> None:
    detected_dates = [
        _build_detected_date(
            value=date(2026, 6, 25),
        ),
        _build_detected_date(
            value=date(2026, 6, 17),
        ),
        _build_detected_date(
            value=date(2026, 6, 20),
        ),
    ]

    timeline = builder.build(
        document_id="document-001",
        detected_dates=detected_dates,
    )

    assert tuple(
        detected.value
        for detected in timeline.dates
    ) == (
        date(2026, 6, 17),
        date(2026, 6, 20),
        date(2026, 6, 25),
    )


def test_build_preserves_repeated_date_occurrences(
    builder: TemporalTimelineBuilder,
) -> None:
    repeated_date = date(2026, 6, 17)

    detected_dates = [
        _build_detected_date(
            value=repeated_date,
            source=DateSource.NATIVE_TEXT,
            page_number=1,
        ),
        _build_detected_date(
            value=repeated_date,
            source=DateSource.OCR,
            page_number=1,
        ),
        _build_detected_date(
            value=repeated_date,
            source=DateSource.PDF_METADATA,
            metadata_field="creationDate",
        ),
    ]

    timeline = builder.build(
        document_id="document-001",
        detected_dates=detected_dates,
    )

    assert timeline.total_dates == 3
    assert len(
        timeline.dates_with_value(repeated_date)
    ) == 3


def test_build_places_metadata_before_page_dates_for_same_value(
    builder: TemporalTimelineBuilder,
) -> None:
    target_date = date(2026, 6, 17)

    metadata_date = _build_detected_date(
        value=target_date,
        source=DateSource.PDF_METADATA,
        page_number=None,
        metadata_field="creationDate",
    )

    page_date = _build_detected_date(
        value=target_date,
        source=DateSource.NATIVE_TEXT,
        page_number=1,
    )

    timeline = builder.build(
        document_id="document-001",
        detected_dates=[
            page_date,
            metadata_date,
        ],
    )

    assert timeline.dates[0] == metadata_date
    assert timeline.dates[1] == page_date


def test_build_orders_same_date_by_page_number(
    builder: TemporalTimelineBuilder,
) -> None:
    target_date = date(2026, 6, 17)

    page_three = _build_detected_date(
        value=target_date,
        page_number=3,
    )

    page_one = _build_detected_date(
        value=target_date,
        page_number=1,
    )

    page_two = _build_detected_date(
        value=target_date,
        page_number=2,
    )

    timeline = builder.build(
        document_id="document-001",
        detected_dates=[
            page_three,
            page_one,
            page_two,
        ],
    )

    assert tuple(
        detected.page_number
        for detected in timeline.dates
    ) == (
        1,
        2,
        3,
    )


def test_build_orders_same_date_and_page_by_source(
    builder: TemporalTimelineBuilder,
) -> None:
    target_date = date(2026, 6, 17)

    native_date = _build_detected_date(
        value=target_date,
        source=DateSource.NATIVE_TEXT,
        page_number=1,
    )

    ocr_date = _build_detected_date(
        value=target_date,
        source=DateSource.OCR,
        page_number=1,
    )

    timeline = builder.build(
        document_id="document-001",
        detected_dates=[
            ocr_date,
            native_date,
        ],
    )

    expected_sources = tuple(
        sorted(
            (
                DateSource.OCR,
                DateSource.NATIVE_TEXT,
            ),
            key=lambda source: source.value,
        )
    )

    assert tuple(
        detected.source
        for detected in timeline.dates
    ) == expected_sources


def test_build_strips_surrounding_whitespace_from_document_id(
    builder: TemporalTimelineBuilder,
) -> None:
    detected_date = _build_detected_date(
        value=date(2026, 6, 17),
        document_id="document-001",
    )

    timeline = builder.build(
        document_id="  document-001  ",
        detected_dates=[detected_date],
    )

    assert timeline.document_id == "document-001"


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
def test_build_rejects_empty_document_identifier(
    builder: TemporalTimelineBuilder,
    document_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="identificador do documento",
    ):
        builder.build(
            document_id=document_id,
            detected_dates=[],
        )


def test_build_rejects_date_from_different_document(
    builder: TemporalTimelineBuilder,
) -> None:
    detected_dates = [
        _build_detected_date(
            value=date(2026, 6, 17),
            document_id="document-001",
        ),
        _build_detected_date(
            value=date(2026, 6, 18),
            document_id="document-002",
        ),
    ]

    with pytest.raises(
        ValueError,
        match="documentos diferentes",
    ):
        builder.build(
            document_id="document-001",
            detected_dates=detected_dates,
        )


def test_build_error_includes_expected_document_identifier(
    builder: TemporalTimelineBuilder,
) -> None:
    detected_date = _build_detected_date(
        value=date(2026, 6, 17),
        document_id="document-999",
    )

    with pytest.raises(
        ValueError,
        match="Documento esperado: document-001",
    ):
        builder.build(
            document_id="document-001",
            detected_dates=[detected_date],
        )


def test_build_error_includes_invalid_document_identifiers(
    builder: TemporalTimelineBuilder,
) -> None:
    detected_dates = [
        _build_detected_date(
            value=date(2026, 6, 17),
            document_id="document-003",
        ),
        _build_detected_date(
            value=date(2026, 6, 18),
            document_id="document-002",
        ),
    ]

    with pytest.raises(ValueError) as error:
        builder.build(
            document_id="document-001",
            detected_dates=detected_dates,
        )

    message = str(error.value)

    assert "document-002" in message
    assert "document-003" in message


def test_build_accepts_generator(
    builder: TemporalTimelineBuilder,
) -> None:
    values = (
        date(2026, 6, 25),
        date(2026, 6, 17),
        date(2026, 6, 20),
    )

    detected_dates = (
        _build_detected_date(value=value)
        for value in values
    )

    timeline = builder.build(
        document_id="document-001",
        detected_dates=detected_dates,
    )

    assert timeline.distinct_values() == (
        date(2026, 6, 17),
        date(2026, 6, 20),
        date(2026, 6, 25),
    )


def test_build_does_not_modify_original_list(
    builder: TemporalTimelineBuilder,
) -> None:
    later_date = _build_detected_date(
        value=date(2026, 6, 25),
    )

    earlier_date = _build_detected_date(
        value=date(2026, 6, 17),
    )

    original = [
        later_date,
        earlier_date,
    ]

    builder.build(
        document_id="document-001",
        detected_dates=original,
    )

    assert original == [
        later_date,
        earlier_date,
    ]