from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from app.domain.concealment.services.local_background_color_sampler import (
    LocalBackgroundColorSampler,
)
from app.domain.document.models.bounding_box import BoundingBox
from app.domain.document.models.color import Color
from app.domain.document.models.font import Font
from app.domain.document.models.text_span import TextSpan


def _span(
    *,
    left: float = 100.0,
    top: float = 100.0,
    right: float = 300.0,
    bottom: float = 140.0,
) -> TextSpan:
    return TextSpan(
        text="Texto de teste",
        bounding_box=BoundingBox(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        ),
        font=Font(
            name="Arial",
            size=10.0,
            color=Color.from_hex("#000000"),
        ),
        page_number=1,
    )


def _create_solid_region_pdf(
    path: Path,
    *,
    fill: tuple[float, float, float],
) -> None:
    document = pymupdf.open()
    page = document.new_page(
        width=595.0,
        height=842.0,
    )
    page.draw_rect(
        pymupdf.Rect(
            80.0,
            80.0,
            320.0,
            160.0,
        ),
        color=None,
        fill=fill,
    )
    document.save(path)
    document.close()


def _create_split_region_pdf(
    path: Path,
) -> None:
    document = pymupdf.open()
    page = document.new_page(
        width=595.0,
        height=842.0,
    )
    page.draw_rect(
        pymupdf.Rect(
            100.0,
            100.0,
            200.0,
            140.0,
        ),
        color=None,
        fill=(0.0, 0.0, 0.0),
    )
    page.draw_rect(
        pymupdf.Rect(
            200.0,
            100.0,
            300.0,
            140.0,
        ),
        color=None,
        fill=(1.0, 1.0, 1.0),
    )
    document.save(path)
    document.close()


def test_should_estimate_white_background(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "white.pdf"
    _create_solid_region_pdf(
        pdf_path,
        fill=(1.0, 1.0, 1.0),
    )

    estimate = LocalBackgroundColorSampler().sample(
        pdf_path=str(pdf_path),
        span=_span(),
    )

    assert estimate is not None
    assert estimate.color.to_hex() == "#FFFFFF"
    assert estimate.dominance_ratio >= 0.99
    assert estimate.sampled_pixel_count > 0
    assert (
        estimate.method
        == "dominant_quantized_bbox_color"
    )


def test_should_estimate_black_background(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "black.pdf"
    _create_solid_region_pdf(
        pdf_path,
        fill=(0.0, 0.0, 0.0),
    )

    estimate = LocalBackgroundColorSampler().sample(
        pdf_path=str(pdf_path),
        span=_span(),
    )

    assert estimate is not None
    assert estimate.color.to_hex() == "#000000"
    assert estimate.dominance_ratio >= 0.99


def test_should_return_none_for_ambiguous_region(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "split.pdf"
    _create_split_region_pdf(pdf_path)

    estimate = LocalBackgroundColorSampler().sample(
        pdf_path=str(pdf_path),
        span=_span(),
    )

    assert estimate is None


def test_should_reject_missing_pdf() -> None:
    with pytest.raises(FileNotFoundError):
        LocalBackgroundColorSampler().sample(
            pdf_path="arquivo-inexistente.pdf",
            span=_span(),
        )


def test_should_reject_invalid_span(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "document.pdf"
    _create_solid_region_pdf(
        pdf_path,
        fill=(1.0, 1.0, 1.0),
    )

    with pytest.raises(TypeError):
        LocalBackgroundColorSampler().sample(
            pdf_path=str(pdf_path),
            span=None,  # type: ignore[arg-type]
        )


def test_should_validate_configuration() -> None:
    with pytest.raises(ValueError):
        LocalBackgroundColorSampler(
            render_scale=0.0,
        )

    with pytest.raises(ValueError):
        LocalBackgroundColorSampler(
            bucket_size=0,
        )

    with pytest.raises(ValueError):
        LocalBackgroundColorSampler(
            minimum_dominance_ratio=0.0,
        )


def test_should_render_same_page_only_once_for_multiple_spans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = tmp_path / "cached.pdf"
    _create_solid_region_pdf(
        pdf_path,
        fill=(1.0, 1.0, 1.0),
    )

    sampler = LocalBackgroundColorSampler()
    original_render_page = sampler._render_page
    render_calls = 0

    def _counting_render_page(
        *,
        pdf_path: str,
        page_number: int,
    ):
        nonlocal render_calls
        render_calls += 1
        return original_render_page(
            pdf_path=pdf_path,
            page_number=page_number,
        )

    monkeypatch.setattr(
        sampler,
        "_render_page",
        _counting_render_page,
    )

    first = _span(
        left=100.0,
        top=100.0,
        right=180.0,
        bottom=140.0,
    )
    second = _span(
        left=220.0,
        top=100.0,
        right=300.0,
        bottom=140.0,
    )

    assert sampler.sample(
        pdf_path=str(pdf_path),
        span=first,
    ) is not None
    assert sampler.sample(
        pdf_path=str(pdf_path),
        span=second,
    ) is not None

    assert render_calls == 1

    sampler.clear_cache()
