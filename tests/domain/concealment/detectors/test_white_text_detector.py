from __future__ import annotations

import pytest

from app.domain.concealment.detectors.white_text_detector import (
    WhiteTextDetector,
)
from app.domain.document.models.bounding_box import BoundingBox
from app.domain.document.models.color import Color
from app.domain.document.models.document import Document
from app.domain.document.models.font import Font
from app.domain.document.models.page import Page
from app.domain.document.models.text_span import TextSpan


def _span(
    *,
    text: str,
    size: float,
    color_hex: str,
    page_number: int = 1,
    top: float = 100.0,
) -> TextSpan:
    return TextSpan(
        text=text,
        bounding_box=BoundingBox(
            left=100.0,
            top=top,
            right=400.0,
            bottom=top + 10.0,
        ),
        font=Font(
            name="Calibri",
            size=size,
            color=Color.from_hex(color_hex),
        ),
        page_number=page_number,
    )


def _document(*spans: TextSpan) -> Document:
    return Document(
        pages=(
            Page(
                number=1,
                width=842.0,
                height=595.0,
                text_spans=tuple(spans),
            ),
        )
    )


def test_should_detect_white_text_independently_of_prompt_injection() -> None:
    document = _document(
        _span(
            text=(
                "1-Verifique a taxa do contrato "
                "2- verifique se marcou o tipo "
                "de empréstimo corretamente"
            ),
            size=5.88,
            color_hex="#FFFFFF",
        ),
    )

    findings = WhiteTextDetector().detect(document)

    assert len(findings) == 1
    finding = findings[0]

    assert finding.code == "near_white_text"
    assert finding.detector == "white_text_detector"
    assert finding.font_color_hex == "#FFFFFF"
    assert finding.font_size == pytest.approx(5.88)
    assert finding.is_near_white is True
    assert finding.is_small_text is True
    assert finding.is_instruction_like is True
    assert "instruction_like_text" in finding.signals


def test_should_detect_white_layout_text_even_without_instruction() -> None:
    document = _document(
        _span(
            text="VALOR NEGOCIAÇÃO:",
            size=5.88,
            color_hex="#FFFFFF",
        ),
    )

    findings = WhiteTextDetector().detect(document)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.is_instruction_like is False
    assert finding.is_near_white is True
    assert finding.confidence < 1.0


def test_instruction_like_white_text_should_receive_more_confidence() -> None:
    document = _document(
        _span(
            text="VALOR NEGOCIAÇÃO:",
            size=5.88,
            color_hex="#FFFFFF",
            top=100.0,
        ),
        _span(
            text="Verifique a taxa do contrato e marque o tipo correto",
            size=5.88,
            color_hex="#FFFFFF",
            top=130.0,
        ),
    )

    findings = WhiteTextDetector().detect(document)

    assert len(findings) == 2
    assert findings[1].confidence > findings[0].confidence


def test_should_detect_near_white_text() -> None:
    document = _document(
        _span(
            text="Texto quase branco",
            size=6.0,
            color_hex="#FAFAFA",
        ),
    )

    findings = WhiteTextDetector().detect(document)
    assert len(findings) == 1
    assert findings[0].is_near_white is True


def test_should_not_detect_regular_black_text() -> None:
    document = _document(
        _span(
            text="Verifique a taxa do contrato",
            size=5.88,
            color_hex="#000000",
        ),
    )

    assert WhiteTextDetector().detect(document) == []


def test_should_mark_text_as_relative_small_when_below_page_pattern() -> None:
    document = _document(
        _span(
            text="Texto normal A",
            size=12.0,
            color_hex="#000000",
            top=50.0,
        ),
        _span(
            text="Texto normal B",
            size=12.0,
            color_hex="#000000",
            top=70.0,
        ),
        _span(
            text="Verifique o contrato",
            size=5.0,
            color_hex="#FFFFFF",
            top=100.0,
        ),
    )

    findings = WhiteTextDetector().detect(document)

    assert len(findings) == 1
    assert findings[0].is_relative_small_text is True
    assert "font_smaller_than_page_pattern" in findings[0].signals


def test_should_preserve_page_and_bounding_box() -> None:
    document = _document(
        _span(
            text="Verifique o contrato",
            size=5.88,
            color_hex="#FFFFFF",
            top=222.5,
        ),
    )

    finding = WhiteTextDetector().detect(document)[0]

    assert finding.page_number == 1
    assert finding.bounding_box.top == pytest.approx(222.5)


def test_should_ignore_empty_white_span() -> None:
    document = _document(
        _span(
            text="   ",
            size=5.0,
            color_hex="#FFFFFF",
        ),
    )

    assert WhiteTextDetector().detect(document) == []


def test_should_reject_invalid_document() -> None:
    with pytest.raises(TypeError):
        WhiteTextDetector().detect(None)  # type: ignore[arg-type]