from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from app.domain.concealment.models.text_concealment_finding import (
    TextConcealmentFinding,
)
from app.domain.concealment.services.visual_concealment_evidence_builder import (
    VisualConcealmentEvidenceBuilder,
)
from app.domain.document.models.bounding_box import BoundingBox


def _finding(
    *,
    text: str = "Verifique a taxa do contrato.",
    page_number: int = 1,
    left: float = 300.0,
    top: float = 70.0,
    right: float = 500.0,
    bottom: float = 78.0,
) -> TextConcealmentFinding:
    return TextConcealmentFinding(
        code="near_white_text",
        detector="white_text_detector",
        page_number=page_number,
        text=text,
        bounding_box=BoundingBox(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        ),
        font_name="Calibri",
        font_size=5.88,
        font_color_hex="#FFFFFF",
        confidence=0.90,
        signals=(
            "near_white_font",
            "small_font",
            "instruction_like_text",
        ),
        is_near_white=True,
        is_small_text=True,
        is_relative_small_text=False,
        is_instruction_like=True,
    )


def _create_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_text(
        (300, 75),
        "Verifique a taxa do contrato.",
        fontsize=5.88,
        color=(1, 1, 1),
    )
    document.save(path)
    document.close()


def test_should_build_location_from_native_bounding_box(tmp_path: Path) -> None:
    pdf_path = tmp_path / "document.pdf"
    _create_pdf(pdf_path)

    finding = _finding()
    locations = VisualConcealmentEvidenceBuilder().build(
        pdf_path=str(pdf_path),
        findings=[finding],
    )

    assert len(locations) == 1
    location = locations[0]
    assert location.located is True
    assert location.page_number == 1
    assert location.matched_content == finding.text
    assert location.left == pytest.approx(300.0)
    assert location.top == pytest.approx(70.0)
    assert location.width == pytest.approx(200.0)
    assert location.height == pytest.approx(8.0)


def test_should_preserve_font_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "document.pdf"
    _create_pdf(pdf_path)

    location = VisualConcealmentEvidenceBuilder().build(
        pdf_path=str(pdf_path),
        findings=[_finding()],
    )[0]

    assert location.font_name == "Calibri"
    assert location.font_size == pytest.approx(5.88)
    assert location.font_color_hex == "#FFFFFF"


def test_should_create_source_and_annotated_images(tmp_path: Path) -> None:
    pdf_path = tmp_path / "document.pdf"
    _create_pdf(pdf_path)

    location = VisualConcealmentEvidenceBuilder().build(
        pdf_path=str(pdf_path),
        findings=[_finding()],
    )[0]

    source_path = Path(location.source_image_path)
    annotated_path = Path(location.annotated_image_path)

    assert source_path.exists()
    assert annotated_path.exists()

    with Image.open(source_path) as source_image:
        source_size = source_image.size

    with Image.open(annotated_path) as annotated_image:
        annotated_size = annotated_image.size

    assert source_size == annotated_size


def test_annotated_image_should_differ_from_source(tmp_path: Path) -> None:
    pdf_path = tmp_path / "document.pdf"
    _create_pdf(pdf_path)

    location = VisualConcealmentEvidenceBuilder().build(
        pdf_path=str(pdf_path),
        findings=[_finding()],
    )[0]

    with Image.open(location.source_image_path) as source_image:
        source_bytes = source_image.convert("RGB").tobytes()

    with Image.open(location.annotated_image_path) as annotated_image:
        annotated_bytes = annotated_image.convert("RGB").tobytes()

    assert source_bytes != annotated_bytes


def test_should_build_one_location_per_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "document.pdf"
    _create_pdf(pdf_path)

    findings = [
        _finding(text="Primeiro trecho", top=70.0, bottom=78.0),
        _finding(text="Segundo trecho", top=90.0, bottom=98.0),
    ]

    locations = VisualConcealmentEvidenceBuilder().build(
        pdf_path=str(pdf_path),
        findings=findings,
    )

    assert len(locations) == 2
    assert locations[0].finding_index == 1
    assert locations[1].finding_index == 2


def test_should_reject_invalid_findings_collection(tmp_path: Path) -> None:
    pdf_path = tmp_path / "document.pdf"
    _create_pdf(pdf_path)

    with pytest.raises(TypeError):
        VisualConcealmentEvidenceBuilder().build(
            pdf_path=str(pdf_path),
            findings=None,  # type: ignore[arg-type]
        )


def test_should_reject_invalid_finding_item(tmp_path: Path) -> None:
    pdf_path = tmp_path / "document.pdf"
    _create_pdf(pdf_path)

    with pytest.raises(TypeError):
        VisualConcealmentEvidenceBuilder().build(
            pdf_path=str(pdf_path),
            findings=[object()],  # type: ignore[list-item]
        )


def test_should_reject_missing_pdf() -> None:
    with pytest.raises(FileNotFoundError):
        VisualConcealmentEvidenceBuilder().build(
            pdf_path="arquivo-inexistente.pdf",
            findings=[],
        )


def test_should_reject_page_outside_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "document.pdf"
    _create_pdf(pdf_path)

    with pytest.raises(ValueError):
        VisualConcealmentEvidenceBuilder().build(
            pdf_path=str(pdf_path),
            findings=[_finding(page_number=2)],
        )