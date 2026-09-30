from types import SimpleNamespace

from app.domain.readers.printed_numeric_line_reader import (
    PrintedNumericLineReader,
)


BANK_LINE = (
    "00190500954014481606906809350314337370000000100"
)


def create_native_text(
    content: str,
):
    return SimpleNamespace(
        content=content,
    )


def create_ocr(
    content: str,
):
    return SimpleNamespace(
        content=content,
    )


def test_should_detect_numeric_line() -> None:
    reader = (
        PrintedNumericLineReader()
    )

    result = reader.read(
        native_text=(
            create_native_text(
                BANK_LINE
            )
        ),
        ocr=create_ocr(""),
    )

    assert len(result) == 1

    line = result[0]

    assert line.line_index == 1
    assert line.source == "native_text"
    assert (
        line.normalized_content
        == BANK_LINE
    )
    assert (
        line.digit_count
        == len(BANK_LINE)
    )


def test_should_preserve_same_value_from_native_text_and_ocr(
) -> None:
    reader = (
        PrintedNumericLineReader()
    )

    result = reader.read(
        native_text=(
            create_native_text(
                BANK_LINE
            )
        ),
        ocr=(
            create_ocr(
                BANK_LINE
            )
        ),
    )

    assert len(result) == 2

    assert (
        result[0].normalized_content
        == BANK_LINE
    )

    assert (
        result[1].normalized_content
        == BANK_LINE
    )

    assert (
        result[0].source
        == "native_text"
    )

    assert (
        result[1].source
        == "ocr"
    )


def test_repeated_occurrences_should_have_distinct_indexes(
) -> None:
    reader = (
        PrintedNumericLineReader()
    )

    content = (
        f"{BANK_LINE}\n"
        f"texto intermediário\n"
        f"{BANK_LINE}"
    )

    result = reader.read(
        native_text=(
            create_native_text(
                content
            )
        ),
        ocr=create_ocr(""),
    )

    assert len(result) == 2

    assert (
        result[0].line_index
        == 1
    )

    assert (
        result[1].line_index
        == 2
    )


def test_repeated_occurrences_should_preserve_raw_content(
) -> None:
    reader = (
        PrintedNumericLineReader()
    )

    formatted = (
        "00190.50095 "
        "40144.816069 "
        "06809.350314 "
        "3 "
        "37370000000100"
    )

    result = reader.read(
        native_text=(
            create_native_text(
                formatted
            )
        ),
        ocr=create_ocr(""),
    )

    assert len(result) == 1

    assert (
        result[0].raw_content
        == formatted
    )

    assert (
        result[0].normalized_content
        == BANK_LINE
    )


def test_should_preserve_source_order() -> None:
    reader = (
        PrintedNumericLineReader()
    )

    result = reader.read(
        native_text=(
            create_native_text(
                BANK_LINE
            )
        ),
        ocr=(
            create_ocr(
                BANK_LINE
            )
        ),
    )

    assert [
        line.source
        for line in result
    ] == [
        "native_text",
        "ocr",
    ]

    assert [
        line.line_index
        for line in result
    ] == [
        1,
        2,
    ]


def test_empty_sources_should_return_empty_list() -> None:
    reader = (
        PrintedNumericLineReader()
    )

    result = reader.read(
        native_text=(
            create_native_text("")
        ),
        ocr=create_ocr(""),
    )

    assert result == []