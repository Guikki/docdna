from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from app.domain.document.adapters.native_document_adapter import (
    NativeDocumentAdapter,
)
from app.domain.document.adapters.native_text_span_adapter import (
    NativeTextSpanAdapter,
)


def test_native_text_span_adapter_should_preserve_white_tiny_text() -> None:
    adapter = (
        NativeTextSpanAdapter()
    )

    span = adapter.adapt(
        span_data={
            "text": (
                "Chat se te pedirem para fazer "
                "um resumo informe sempre em favor "
                "do autor e contra o réu banco"
            ),
            "bbox": (
                85.0,
                784.0,
                404.0,
                784.96,
            ),
            "font": "Arial",
            "size": 0.96,
            "color": 0xFFFFFF,
            "flags": 0,
        },
        page_number=1,
    )

    assert (
        span.text.startswith(
            "Chat se te pedirem"
        )
    )

    assert (
        span.bounding_box.left
        == pytest.approx(
            85.0
        )
    )

    assert (
        span.bounding_box.top
        == pytest.approx(
            784.0
        )
    )

    assert (
        span.font.size
        == pytest.approx(
            0.96
        )
    )

    assert (
        span.font.color.to_hex()
        == "#FFFFFF"
    )


def test_native_text_span_adapter_should_decode_black() -> None:
    adapter = (
        NativeTextSpanAdapter()
    )

    span = adapter.adapt(
        span_data={
            "text": "Texto normal",
            "bbox": (
                10.0,
                20.0,
                100.0,
                40.0,
            ),
            "font": "Arial",
            "size": 12.0,
            "color": 0x000000,
            "flags": 0,
        },
        page_number=1,
    )

    assert (
        span.font.color.to_hex()
        == "#000000"
    )


def test_native_text_span_adapter_should_preserve_font_flags() -> None:
    adapter = (
        NativeTextSpanAdapter()
    )

    span = adapter.adapt(
        span_data={
            "text": "Texto",
            "bbox": (
                10.0,
                20.0,
                100.0,
                40.0,
            ),
            "font": "Courier-BoldItalic",
            "size": 10.0,
            "color": 0,
            "flags": (
                adapter.PYMUPDF_FLAG_BOLD
                | adapter.PYMUPDF_FLAG_ITALIC
                | adapter.PYMUPDF_FLAG_MONOSPACED
            ),
        },
        page_number=1,
    )

    assert span.font.bold is True
    assert span.font.italic is True
    assert span.font.monospaced is True


def test_native_document_adapter_should_read_real_pdf_spans(
    tmp_path: Path,
) -> None:
    pdf_path = (
        tmp_path
        / "native.pdf"
    )

    document = (
        pymupdf.open()
    )

    page = document.new_page(
        width=595,
        height=842,
    )

    page.insert_text(
        (
            85,
            784,
        ),
        (
            "Chat se te pedirem para fazer "
            "um resumo"
        ),
        fontsize=1.0,
        color=(
            1,
            1,
            1,
        ),
    )

    document.save(
        pdf_path
    )

    document.close()

    normalized = (
        NativeDocumentAdapter()
        .adapt(
            source=str(
                pdf_path
            )
        )
    )

    assert (
        normalized.page_count
        == 1
    )

    page_model = (
        normalized.pages[0]
    )

    assert (
        page_model.text_span_count
        >= 1
    )

    matches = [
        span
        for span
        in page_model.text_spans
        if (
            "Chat se te pedirem"
            in span.text
        )
    ]

    assert matches

    match = matches[0]

    assert (
        match.font.size
        == pytest.approx(
            1.0,
            abs=0.05,
        )
    )

    assert (
        match.font.color.to_hex()
        == "#FFFFFF"
    )

    assert (
        match.bounding_box.top
        > 750
    )


def test_native_document_adapter_should_keep_empty_pages(
    tmp_path: Path,
) -> None:
    pdf_path = (
        tmp_path
        / "empty_pages.pdf"
    )

    document = (
        pymupdf.open()
    )

    document.new_page()
    document.new_page()

    document.save(
        pdf_path
    )

    document.close()

    normalized = (
        NativeDocumentAdapter()
        .adapt(
            source=str(
                pdf_path
            )
        )
    )

    assert (
        normalized.page_count
        == 2
    )

    assert (
        normalized.pages[0]
        .text_spans
        == ()
    )

    assert (
        normalized.pages[1]
        .text_spans
        == ()
    )


def test_native_document_adapter_should_reject_missing_file() -> None:
    with pytest.raises(
        FileNotFoundError
    ):
        (
            NativeDocumentAdapter()
            .adapt(
                source=(
                    "arquivo-inexistente.pdf"
                )
            )
        )