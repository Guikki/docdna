from datetime import date

import pytest

from app.domain.models.detected_date import (
    DateSource,
)
from app.domain.services.date_extractor_service import (
    DateExtractorService,
)


@pytest.fixture
def extractor() -> DateExtractorService:
    return DateExtractorService()


def test_extract_returns_empty_list_when_content_is_none(
    extractor: DateExtractorService,
) -> None:
    result = extractor.extract(
        content=None,
        source=DateSource.NATIVE_TEXT,
        document_id="document-001",
    )

    assert result == []


def test_extract_returns_empty_list_when_content_is_empty(
    extractor: DateExtractorService,
) -> None:
    result = extractor.extract(
        content="",
        source=DateSource.NATIVE_TEXT,
        document_id="document-001",
    )

    assert result == []


@pytest.mark.parametrize(
    (
        "content",
        "expected_raw_content",
        "expected_date",
    ),
    [
        (
            "Data de emissão: 17/06/2026.",
            "17/06/2026",
            date(2026, 6, 17),
        ),
        (
            "Documento emitido em 17-06-2026.",
            "17-06-2026",
            date(2026, 6, 17),
        ),
        (
            "Vencimento: 17.06.2026.",
            "17.06.2026",
            date(2026, 6, 17),
        ),
    ],
)
def test_extract_identifies_supported_date_formats(
    extractor: DateExtractorService,
    content: str,
    expected_raw_content: str,
    expected_date: date,
) -> None:
    result = extractor.extract(
        content=content,
        source=DateSource.NATIVE_TEXT,
        document_id="document-001",
    )

    assert len(result) == 1

    detected_date = result[0]

    assert detected_date.value == expected_date
    assert detected_date.raw_content == expected_raw_content
    assert detected_date.source == DateSource.NATIVE_TEXT
    assert detected_date.document_id == "document-001"


def test_extract_identifies_multiple_dates(
    extractor: DateExtractorService,
) -> None:
    content = (
        "Data de emissão: 17/06/2026. "
        "Data de vencimento: 25/06/2026."
    )

    result = extractor.extract(
        content=content,
        source=DateSource.OCR,
        document_id="document-002",
        page_number=1,
        confidence=92.5,
    )

    assert len(result) == 2

    assert result[0].value == date(2026, 6, 17)
    assert result[1].value == date(2026, 6, 25)

    assert result[0].source == DateSource.OCR
    assert result[1].source == DateSource.OCR

    assert result[0].page_number == 1
    assert result[1].page_number == 1

    assert result[0].confidence == 92.5
    assert result[1].confidence == 92.5


def test_extract_ignores_invalid_calendar_date(
    extractor: DateExtractorService,
) -> None:
    content = "Data informada: 31/02/2026."

    result = extractor.extract(
        content=content,
        source=DateSource.NATIVE_TEXT,
        document_id="document-003",
    )

    assert result == []


def test_extract_preserves_metadata_field(
    extractor: DateExtractorService,
) -> None:
    result = extractor.extract(
        content="18/11/2026",
        source=DateSource.PDF_METADATA,
        document_id="document-004",
        metadata_field="creationDate",
    )

    assert len(result) == 1

    detected_date = result[0]

    assert detected_date.metadata_field == "creationDate"
    assert detected_date.source == DateSource.PDF_METADATA


def test_extract_includes_surrounding_text(
    extractor: DateExtractorService,
) -> None:
    content = (
        "Comprovante de residência emitido em "
        "17/06/2026 para fins de validação cadastral."
    )

    result = extractor.extract(
        content=content,
        source=DateSource.NATIVE_TEXT,
        document_id="document-005",
    )

    assert len(result) == 1
    assert result[0].surrounding_text is not None
    assert "emitido em" in result[0].surrounding_text
    assert "17/06/2026" in result[0].surrounding_text


def test_extract_preserves_page_number_and_confidence(
    extractor: DateExtractorService,
) -> None:
    result = extractor.extract(
        content="Vencimento: 10/08/2026",
        source=DateSource.OCR,
        document_id="document-006",
        page_number=3,
        confidence=87.4,
    )

    assert len(result) == 1

    detected_date = result[0]

    assert detected_date.page_number == 3
    assert detected_date.confidence == 87.4


def test_extract_does_not_duplicate_same_match_position(
    extractor: DateExtractorService,
) -> None:
    content = "Data única: 17/06/2026."

    result = extractor.extract(
        content=content,
        source=DateSource.NATIVE_TEXT,
        document_id="document-007",
    )

    assert len(result) == 1
