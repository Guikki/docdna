from datetime import date

import pytest

from app.domain.models.detected_date import (
    DateSource,
)
from app.domain.models.pdf_info import PdfInfo
from app.domain.services.pdf_metadata_date_extractor import (
    PdfMetadataDateExtractor,
)


@pytest.fixture
def extractor() -> PdfMetadataDateExtractor:
    return PdfMetadataDateExtractor()


def _build_pdf_info(
    creation_date: str | None = None,
    modification_date: str | None = None,
) -> PdfInfo:
    return PdfInfo(
        page_count=1,
        title=None,
        author=None,
        creator=None,
        producer=None,
        creation_date=creation_date,
        modification_date=modification_date,
        pdf_version=None,
        has_text=True,
        has_images=False,
    )


def test_extract_returns_empty_when_pdf_has_no_dates(
    extractor: PdfMetadataDateExtractor,
) -> None:
    pdf_info = _build_pdf_info()

    result = extractor.extract(
        pdf_info=pdf_info,
        document_id="document-001",
    )

    assert result == []


def test_extract_returns_creation_date(
    extractor: PdfMetadataDateExtractor,
) -> None:
    pdf_info = _build_pdf_info(
        creation_date="D:20261118143022-03'00'",
    )

    result = extractor.extract(
        pdf_info=pdf_info,
        document_id="document-002",
    )

    assert len(result) == 1

    detected = result[0]

    assert detected.value == date(2026, 11, 18)
    assert detected.source == DateSource.PDF_METADATA
    assert detected.document_id == "document-002"
    assert detected.metadata_field == "creationDate"
    assert detected.page_number is None
    assert detected.confidence == 1.0


def test_extract_returns_modification_date(
    extractor: PdfMetadataDateExtractor,
) -> None:
    pdf_info = _build_pdf_info(
        modification_date="D:20261119101500-03'00'",
    )

    result = extractor.extract(
        pdf_info=pdf_info,
        document_id="document-003",
    )

    assert len(result) == 1

    detected = result[0]

    assert detected.value == date(2026, 11, 19)
    assert detected.metadata_field == "modDate"


def test_extract_returns_creation_and_modification_dates(
    extractor: PdfMetadataDateExtractor,
) -> None:
    pdf_info = _build_pdf_info(
        creation_date="D:20261118143022-03'00'",
        modification_date="D:20261119101500-03'00'",
    )

    result = extractor.extract(
        pdf_info=pdf_info,
        document_id="document-004",
    )

    assert len(result) == 2

    assert result[0].metadata_field == "creationDate"
    assert result[1].metadata_field == "modDate"


def test_extract_ignores_invalid_creation_date(
    extractor: PdfMetadataDateExtractor,
) -> None:
    pdf_info = _build_pdf_info(
        creation_date="sem-data",
    )

    result = extractor.extract(
        pdf_info=pdf_info,
        document_id="document-005",
    )

    assert result == []


def test_extract_ignores_invalid_modification_date(
    extractor: PdfMetadataDateExtractor,
) -> None:
    pdf_info = _build_pdf_info(
        modification_date="2026",
    )

    result = extractor.extract(
        pdf_info=pdf_info,
        document_id="document-006",
    )

    assert result == []


def test_extract_preserves_original_metadata_value(
    extractor: PdfMetadataDateExtractor,
) -> None:
    raw_value = "D:20261118143022-03'00'"

    pdf_info = _build_pdf_info(
        creation_date=raw_value,
    )

    result = extractor.extract(
        pdf_info=pdf_info,
        document_id="document-007",
    )

    assert len(result) == 1

    assert result[0].raw_content == raw_value


def test_extract_builds_human_readable_context(
    extractor: PdfMetadataDateExtractor,
) -> None:
    pdf_info = _build_pdf_info(
        creation_date="D:20261118143022-03'00'",
    )

    result = extractor.extract(
        pdf_info=pdf_info,
        document_id="document-008",
    )

    assert len(result) == 1

    context = result[0].surrounding_text

    assert context is not None
    assert "criação" in context.lower()


def test_extract_assigns_pdf_metadata_source(
    extractor: PdfMetadataDateExtractor,
) -> None:
    pdf_info = _build_pdf_info(
        creation_date="18/11/2026",
    )

    result = extractor.extract(
        pdf_info=pdf_info,
        document_id="document-009",
    )

    assert len(result) == 1

    assert result[0].source == DateSource.PDF_METADATA


def test_extract_preserves_document_identifier(
    extractor: PdfMetadataDateExtractor,
) -> None:
    pdf_info = _build_pdf_info(
        creation_date="18/11/2026",
    )

    result = extractor.extract(
        pdf_info=pdf_info,
        document_id="batch-2026-document-15",
    )

    assert len(result) == 1

    assert result[0].document_id == "batch-2026-document-15"