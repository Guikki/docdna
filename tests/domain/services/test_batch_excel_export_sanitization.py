from __future__ import annotations

from openpyxl import Workbook

from app.domain.services.batch_excel_export_service import (
    BatchExcelExportService,
)


def test_should_convert_illegal_excel_characters_to_visible_escape() -> None:
    raw_value = (
        "Texto"
        "\x00"
        "com"
        "\x0B"
        "controle"
        "\x1F"
        "interno"
    )

    sanitized = (
        BatchExcelExportService
        ._sanitize_excel_text(
            raw_value
        )
    )

    assert sanitized == (
        "Texto"
        "\\x00"
        "com"
        "\\x0B"
        "controle"
        "\\x1F"
        "interno"
    )


def test_should_preserve_allowed_whitespace_characters() -> None:
    raw_value = (
        "linha 1\n"
        "linha 2\t"
        "coluna\r"
        "fim"
    )

    sanitized = (
        BatchExcelExportService
        ._sanitize_excel_text(
            raw_value
        )
    )

    assert sanitized == raw_value


def test_should_sanitize_nested_export_payload() -> None:
    payload = {
        "prompt_injection": [
            {
                "original_excerpt": (
                    "ABC\x0BDEF"
                ),
                "confidence": 0.95,
            }
        ],
        "total": 1,
    }

    sanitized = (
        BatchExcelExportService
        ._sanitize_excel_payload(
            payload
        )
    )

    assert (
        sanitized[
            "prompt_injection"
        ][0][
            "original_excerpt"
        ]
        == "ABC\\x0BDEF"
    )

    assert (
        sanitized[
            "prompt_injection"
        ][0][
            "confidence"
        ]
        == 0.95
    )


def test_sanitized_text_should_be_accepted_by_openpyxl() -> None:
    raw_value = (
        "Trecho extraído "
        "\x0B"
        "do PDF"
    )

    sanitized = (
        BatchExcelExportService
        ._sanitize_excel_text(
            raw_value
        )
    )

    workbook = Workbook()
    worksheet = workbook.active

    worksheet.append(
        [
            sanitized,
        ]
    )

    assert (
        worksheet["A1"].value
        == "Trecho extraído \\x0Bdo PDF"
    )