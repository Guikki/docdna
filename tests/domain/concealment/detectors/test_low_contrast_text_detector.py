from __future__ import annotations

import pytest

from app.domain.concealment.detectors.low_contrast_text_detector import (
    LowContrastTextDetector,
)
from app.domain.concealment.models.background_color_estimate import (
    BackgroundColorEstimate,
)
from app.domain.document.models.bounding_box import BoundingBox
from app.domain.document.models.color import Color
from app.domain.document.models.document import Document
from app.domain.document.models.font import Font
from app.domain.document.models.page import Page
from app.domain.document.models.text_span import TextSpan


class _FakeBackgroundSampler:
    def __init__(
        self,
        estimate: BackgroundColorEstimate | None,
    ) -> None:
        self._estimate = estimate

    def sample(
        self,
        *,
        pdf_path: str,
        span: TextSpan,
    ) -> BackgroundColorEstimate | None:
        return self._estimate


def _estimate(
    color: Color,
    *,
    dominance_ratio: float = 0.90,
) -> BackgroundColorEstimate:
    return BackgroundColorEstimate(
        color=color,
        dominance_ratio=dominance_ratio,
        sampled_pixel_count=1000,
        method="test_background",
    )


def _span(
    *,
    text: str = "Texto de teste",
    color: Color | None = None,
    font_name: str = "Arial",
    page_number: int = 1,
) -> TextSpan:
    return TextSpan(
        text=text,
        bounding_box=BoundingBox(
            left=100.0,
            top=200.0,
            right=300.0,
            bottom=220.0,
        ),
        font=Font(
            name=font_name,
            size=10.0,
            color=(
                color
                or Color.from_hex("#000000")
            ),
        ),
        page_number=page_number,
    )


def _document(
    *spans: TextSpan,
) -> Document:
    return Document(
        pages=(
            Page(
                number=1,
                width=595.0,
                height=842.0,
                text_spans=tuple(spans),
            ),
        )
    )


def _gray_for_relative_luminance(
    luminance: float,
) -> Color:
    if luminance <= 0.0031308:
        channel = 12.92 * luminance
    else:
        channel = (
            1.055
            * (luminance ** (1.0 / 2.4))
            - 0.055
        )

    return Color(
        red=channel,
        green=channel,
        blue=channel,
    )


def test_white_on_white_should_be_extreme_low_contrast() -> None:
    white = Color.from_hex("#FFFFFF")
    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(white)
        )
    )

    findings = detector.detect(
        _document(
            _span(color=white)
        ),
        pdf_path="document.pdf",
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "low_contrast_text"
    assert finding.detector == "low_contrast_text_detector"
    assert finding.font_color_hex == "#FFFFFF"
    assert finding.background_color_hex == "#FFFFFF"
    assert finding.contrast_ratio == pytest.approx(1.0)
    assert finding.contrast_threshold == pytest.approx(2.0)
    assert finding.is_low_contrast is True
    assert finding.is_extreme_low_contrast is True
    assert finding.contrast_level == "extreme_low_contrast"
    assert "extreme_low_contrast" in finding.signals


def test_white_on_black_should_not_be_low_contrast() -> None:
    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(
                Color.from_hex("#000000")
            )
        )
    )

    findings = detector.detect(
        _document(
            _span(
                color=Color.from_hex("#FFFFFF")
            )
        ),
        pdf_path="document.pdf",
    )

    assert findings == []


def test_black_on_white_should_not_be_low_contrast() -> None:
    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(
                Color.from_hex("#FFFFFF")
            )
        )
    )

    findings = detector.detect(
        _document(
            _span(
                color=Color.from_hex("#000000")
            )
        ),
        pdf_path="document.pdf",
    )

    assert findings == []


def test_near_white_on_white_should_be_detected() -> None:
    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(
                Color.from_hex("#FFFFFF")
            )
        )
    )

    findings = detector.detect(
        _document(
            _span(
                color=Color.from_hex("#F5F5F5")
            )
        ),
        pdf_path="document.pdf",
    )

    assert len(findings) == 1
    assert findings[0].contrast_ratio < 1.2
    assert findings[0].is_extreme_low_contrast is True


def test_exactly_two_to_one_should_not_generate_finding() -> None:
    black = Color.from_hex("#000000")
    background = _gray_for_relative_luminance(
        0.05
    )

    assert black.contrast_ratio(
        background
    ) == pytest.approx(2.0)

    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(background)
        )
    )

    findings = detector.detect(
        _document(
            _span(color=black)
        ),
        pdf_path="document.pdf",
    )

    assert findings == []


def test_below_two_to_one_should_generate_finding() -> None:
    black = Color.from_hex("#000000")
    background = _gray_for_relative_luminance(
        0.049
    )

    assert black.contrast_ratio(
        background
    ) < 2.0

    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(background)
        )
    )

    findings = detector.detect(
        _document(
            _span(color=black)
        ),
        pdf_path="document.pdf",
    )

    assert len(findings) == 1
    assert findings[0].is_low_contrast is True


def test_exactly_one_point_five_should_not_be_extreme() -> None:
    black = Color.from_hex("#000000")
    background = _gray_for_relative_luminance(
        0.025
    )

    assert black.contrast_ratio(
        background
    ) == pytest.approx(1.5)

    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(background)
        )
    )

    finding = detector.detect(
        _document(
            _span(color=black)
        ),
        pdf_path="document.pdf",
    )[0]

    assert finding.is_low_contrast is True
    assert finding.is_extreme_low_contrast is False
    assert finding.contrast_level == "low_contrast"


def test_below_one_point_five_should_be_extreme() -> None:
    black = Color.from_hex("#000000")
    background = _gray_for_relative_luminance(
        0.024
    )

    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(background)
        )
    )

    finding = detector.detect(
        _document(
            _span(color=black)
        ),
        pdf_path="document.pdf",
    )[0]

    assert finding.contrast_ratio < 1.5
    assert finding.is_extreme_low_contrast is True


def test_should_preserve_page_and_bounding_box() -> None:
    white = Color.from_hex("#FFFFFF")
    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(white)
        )
    )
    span = _span(
        color=white,
        page_number=1,
    )

    finding = detector.detect(
        _document(span),
        pdf_path="document.pdf",
    )[0]

    assert finding.page_number == 1
    assert finding.bounding_box == span.bounding_box


def test_should_preserve_background_measurement_metadata() -> None:
    white = Color.from_hex("#FFFFFF")
    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(
                white,
                dominance_ratio=0.82,
            )
        )
    )

    finding = detector.detect(
        _document(
            _span(color=white)
        ),
        pdf_path="document.pdf",
    )[0]

    assert (
        finding.background_sampling_method
        == "test_background"
    )
    assert (
        finding.background_dominance_ratio
        == pytest.approx(0.82)
    )
    assert finding.font_relative_luminance == pytest.approx(1.0)
    assert finding.background_relative_luminance == pytest.approx(1.0)


def test_should_ignore_ocr_technical_span() -> None:
    white = Color.from_hex("#FFFFFF")
    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(white)
        )
    )

    findings = detector.detect(
        _document(
            _span(
                color=white,
                font_name="OCR_UNKNOWN",
            )
        ),
        pdf_path="document.pdf",
    )

    assert findings == []


def test_should_ignore_empty_text() -> None:
    white = Color.from_hex("#FFFFFF")
    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            _estimate(white)
        )
    )

    findings = detector.detect(
        _document(
            _span(
                text="   ",
                color=white,
            )
        ),
        pdf_path="document.pdf",
    )

    assert findings == []


def test_should_ignore_span_when_background_is_inconclusive() -> None:
    detector = LowContrastTextDetector(
        background_sampler=_FakeBackgroundSampler(
            None
        )
    )

    findings = detector.detect(
        _document(
            _span(
                color=Color.from_hex("#FFFFFF")
            )
        ),
        pdf_path="document.pdf",
    )

    assert findings == []


def test_should_reject_invalid_document() -> None:
    with pytest.raises(TypeError):
        LowContrastTextDetector(
            background_sampler=_FakeBackgroundSampler(
                None
            )
        ).detect(
            None,  # type: ignore[arg-type]
            pdf_path="document.pdf",
        )


def test_should_reject_invalid_thresholds() -> None:
    with pytest.raises(ValueError):
        LowContrastTextDetector(
            low_contrast_threshold=1.0,
        )

    with pytest.raises(ValueError):
        LowContrastTextDetector(
            low_contrast_threshold=2.0,
            extreme_low_contrast_threshold=2.0,
        )
