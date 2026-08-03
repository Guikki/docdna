from datetime import date

import pytest

from app.domain.services.pdf_metadata_date_parser import (
    PdfMetadataDateParser,
)


@pytest.fixture
def parser() -> PdfMetadataDateParser:
    return PdfMetadataDateParser()


@pytest.mark.parametrize(
    (
        "raw_value",
        "expected_date",
    ),
    [
        (
            "D:20261118143022-03'00'",
            date(2026, 11, 18),
        ),
        (
            "20261118143022",
            date(2026, 11, 18),
        ),
        (
            "D:20261118",
            date(2026, 11, 18),
        ),
        (
            "18/11/2026",
            date(2026, 11, 18),
        ),
        (
            "2026-11-18",
            date(2026, 11, 18),
        ),
        (
            "18-11-2026",
            date(2026, 11, 18),
        ),
        (
            "2026/11/18",
            date(2026, 11, 18),
        ),
        (
            "18.11.2026",
            date(2026, 11, 18),
        ),
    ],
)
def test_parse_date_returns_normalized_date(
    parser: PdfMetadataDateParser,
    raw_value: str,
    expected_date: date,
) -> None:
    result = parser.parse_date(raw_value)

    assert result == expected_date


@pytest.mark.parametrize(
    "raw_value",
    [
        None,
        "",
        "   ",
        "sem-data",
        "2026",
        "D:20261345120000",
        "31/02/2026",
        "2026-02-31",
    ],
)
def test_parse_date_returns_none_for_invalid_values(
    parser: PdfMetadataDateParser,
    raw_value: str | None,
) -> None:
    result = parser.parse_date(raw_value)

    assert result is None


def test_parse_date_ignores_surrounding_whitespace(
    parser: PdfMetadataDateParser,
) -> None:
    result = parser.parse_date(
        "  D:20261118143022-03'00'  "
    )

    assert result == date(2026, 11, 18)