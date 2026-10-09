from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.domain.concealment.services.visual_concealment_analysis_service import (
    VisualConcealmentAnalysisService,
)
from app.domain.document.models.bounding_box import BoundingBox
from app.domain.document.models.color import Color
from app.domain.document.models.document import Document
from app.domain.document.models.font import Font
from app.domain.document.models.page import Page
from app.domain.document.models.text_span import TextSpan


class _BackgroundSamplerStub:
    """
    Simula a estimativa de fundo sem depender de renderização real do PDF.

    O objetivo destes testes é validar exclusivamente a regra que decide se
    texto branco deve ou não ser promovido a achado de ocultação visual.
    """

    def __init__(
        self,
        background_color_hex: str | None,
    ) -> None:
        self._background_color_hex = (
            background_color_hex
        )

    def sample(
        self,
        *,
        pdf_path: str,
        span: TextSpan,
    ):
        if (
            self._background_color_hex
            is None
        ):
            return None

        return SimpleNamespace(
            color=Color.from_hex(
                self._background_color_hex
            ),
            dominance_ratio=0.95,
            sampled_pixel_count=100,
            method="test_background_sampler",
        )


def _span(
    *,
    text: str = "MARIA OLIVEIRA",
    color_hex: str = "#FFFFFF",
    size: float = 10.0,
) -> TextSpan:
    return TextSpan(
        text=text,
        bounding_box=BoundingBox(
            left=100.0,
            top=100.0,
            right=300.0,
            bottom=120.0,
        ),
        font=Font(
            name="Calibri",
            size=size,
            color=Color.from_hex(
                color_hex
            ),
        ),
        page_number=1,
    )


def _document(
    span: TextSpan,
) -> Document:
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


def _fake_pdf(
    tmp_path: Path,
) -> str:
    """
    Cria apenas um caminho físico para permitir a etapa de seleção.

    A leitura do conteúdo é interceptada pelo sampler de teste.
    """

    path = (
        tmp_path
        / "documento.pdf"
    )
    path.touch()

    return str(
        path
    )


def test_white_text_on_dark_background_should_not_be_concealment(
    tmp_path: Path,
) -> None:
    sampler = _BackgroundSamplerStub(
        "#101828"
    )

    result = VisualConcealmentAnalysisService(
        background_sampler=sampler,  # type: ignore[arg-type]
    ).analyze(
        _document(
            _span(
                text="MARIA OLIVEIRA",
            )
        ),
        pdf_path=_fake_pdf(
            tmp_path
        ),
    )

    assert result.white_text_count == 0
    assert result.low_contrast_text_count == 0
    assert result.has_findings is False


def test_white_text_on_white_background_should_remain_concealment(
    tmp_path: Path,
) -> None:
    sampler = _BackgroundSamplerStub(
        "#FFFFFF"
    )

    result = VisualConcealmentAnalysisService(
        background_sampler=sampler,  # type: ignore[arg-type]
    ).analyze(
        _document(
            _span(
                text="Texto visualmente oculto",
            )
        ),
        pdf_path=_fake_pdf(
            tmp_path
        ),
    )

    assert result.white_text_count == 1
    assert result.low_contrast_text_count == 1
    assert result.has_findings is True


def test_white_text_should_remain_when_background_is_indeterminate(
    tmp_path: Path,
) -> None:
    sampler = _BackgroundSamplerStub(
        None
    )

    result = VisualConcealmentAnalysisService(
        background_sampler=sampler,  # type: ignore[arg-type]
    ).analyze(
        _document(
            _span(
                text="Texto branco sem fundo determinável",
            )
        ),
        pdf_path=_fake_pdf(
            tmp_path
        ),
    )

    assert result.white_text_count == 1
    assert result.low_contrast_text_count == 0
    assert result.has_findings is True