from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from app.domain.concealment.services.visual_concealment_analysis_service import (
    VisualConcealmentAnalysisService,
)
from app.domain.concealment.services.visual_concealment_evidence_builder import (
    VisualConcealmentEvidenceBuilder,
)
from app.domain.document.models.bounding_box import BoundingBox
from app.domain.document.models.color import Color
from app.domain.document.models.document import Document
from app.domain.document.models.font import Font
from app.domain.document.models.page import Page
from app.domain.document.models.text_span import TextSpan


def _create_low_contrast_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page(
        width=595.0,
        height=842.0,
    )
    gray = 187 / 255.0
    page.insert_text(
        (100.0, 110.0),
        "Texto de baixo contraste",
        fontsize=11.0,
        color=(gray, gray, gray),
    )
    document.save(path)
    document.close()


def _normalized_document() -> Document:
    span = TextSpan(
        text="Texto de baixo contraste",
        bounding_box=BoundingBox(
            left=95.0,
            top=92.0,
            right=280.0,
            bottom=114.0,
        ),
        font=Font(
            name="Helvetica",
            size=11.0,
            color=Color.from_hex("#BBBBBB"),
        ),
        page_number=1,
    )

    return Document(
        pages=(
            Page(
                number=1,
                width=595.0,
                height=842.0,
                text_spans=(span,),
            ),
        )
    )


def test_low_contrast_should_generate_located_visual_evidence(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "low_contrast_document.pdf"
    _create_low_contrast_pdf(pdf_path)

    analysis = VisualConcealmentAnalysisService().analyze(
        _normalized_document(),
        pdf_path=str(pdf_path),
    )

    assert analysis.low_contrast_text_count == 1
    finding = analysis.low_contrast_text_findings[0]
    assert finding.code == "low_contrast_text"
    assert finding.contrast_ratio is not None
    assert finding.contrast_ratio < 2.0

    locations = VisualConcealmentEvidenceBuilder().build(
        pdf_path=str(pdf_path),
        findings=analysis.text_concealment_findings,
    )

    low_contrast_locations = [
        location
        for location in locations
        if location.finding_code == "low_contrast_text"
    ]

    assert len(low_contrast_locations) == 1
    location = low_contrast_locations[0]
    assert location.located is True
    assert location.detector == "low_contrast_text_detector"
    assert location.page_number == 1
    assert location.matched_content == "Texto de baixo contraste"
    assert location.left == pytest.approx(95.0)
    assert location.top == pytest.approx(92.0)
    assert location.width == pytest.approx(185.0)
    assert location.height == pytest.approx(22.0)

    source_path = Path(location.source_image_path)
    annotated_path = Path(location.annotated_image_path)

    assert source_path.exists()
    assert annotated_path.exists()

    with Image.open(source_path) as source_image:
        source_bytes = source_image.convert("RGB").tobytes()

    with Image.open(annotated_path) as annotated_image:
        annotated_bytes = annotated_image.convert("RGB").tobytes()

    assert source_bytes != annotated_bytes
