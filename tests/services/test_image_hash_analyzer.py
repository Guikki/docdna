from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image

from app.domain.models.document_image import DocumentImage
from app.domain.models.image_hash_analysis import ImageHashAnalysis
from app.services.image_hash_analyzer import ImageHashAnalyzer


def create_document_image(
    image_path: Path,
    width: int = 100,
    height: int = 100,
) -> DocumentImage:
    return DocumentImage(
        image_index=1,
        page_number=1,
        xref=10,
        filename=image_path.name,
        saved_path=str(image_path),
        extension=image_path.suffix.removeprefix("."),
        width=width,
        height=height,
        size_bytes=image_path.stat().st_size,
    )


def test_should_analyze_image_hashes(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "sample.png"

    Image.new(
        mode="RGB",
        size=(100, 100),
        color=(255, 255, 255),
    ).save(image_path)

    document_image = create_document_image(image_path)
    analyzer = ImageHashAnalyzer()

    result = analyzer.analyze(document_image)

    expected_sha256 = hashlib.sha256(
        image_path.read_bytes()
    ).hexdigest()

    assert isinstance(result, ImageHashAnalysis)

    assert result.perceptual_hash
    assert result.average_hash
    assert result.difference_hash

    assert len(result.perceptual_hash) == 16
    assert len(result.average_hash) == 16
    assert len(result.difference_hash) == 16

    assert result.image_hash == expected_sha256
    assert len(result.image_hash) == 64


def test_should_generate_same_hashes_for_same_image(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "same-image.png"

    Image.new(
        mode="RGB",
        size=(80, 80),
        color=(50, 100, 150),
    ).save(image_path)

    document_image = create_document_image(
        image_path=image_path,
        width=80,
        height=80,
    )

    analyzer = ImageHashAnalyzer()

    first_result = analyzer.analyze(document_image)
    second_result = analyzer.analyze(document_image)

    assert first_result == second_result


def test_should_generate_different_sha256_for_different_files(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"

    Image.new(
        mode="RGB",
        size=(100, 100),
        color=(255, 255, 255),
    ).save(first_path)

    Image.new(
        mode="RGB",
        size=(100, 100),
        color=(0, 0, 0),
    ).save(second_path)

    first_image = create_document_image(first_path)
    second_image = create_document_image(second_path)

    analyzer = ImageHashAnalyzer()

    first_result = analyzer.analyze(first_image)
    second_result = analyzer.analyze(second_image)

    assert first_result.image_hash != second_result.image_hash


def test_should_raise_error_when_image_does_not_exist(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.png"

    document_image = DocumentImage(
        image_index=1,
        page_number=1,
        xref=10,
        filename=missing_path.name,
        saved_path=str(missing_path),
        extension="png",
        width=100,
        height=100,
        size_bytes=0,
    )

    analyzer = ImageHashAnalyzer()

    with pytest.raises(
        FileNotFoundError,
        match="Image file was not found",
    ):
        analyzer.analyze(document_image)


def test_should_raise_error_when_path_is_directory(
    tmp_path: Path,
) -> None:
    document_image = DocumentImage(
        image_index=1,
        page_number=1,
        xref=10,
        filename=tmp_path.name,
        saved_path=str(tmp_path),
        extension="",
        width=100,
        height=100,
        size_bytes=0,
    )

    analyzer = ImageHashAnalyzer()

    with pytest.raises(
        ValueError,
        match="Image path must point to a file",
    ):
        analyzer.analyze(document_image)


def test_should_raise_error_for_invalid_image_file(
    tmp_path: Path,
) -> None:
    invalid_path = tmp_path / "invalid.png"
    invalid_path.write_text(
        "this is not an image",
        encoding="utf-8",
    )

    document_image = create_document_image(invalid_path)
    analyzer = ImageHashAnalyzer()

    with pytest.raises(
        ValueError,
        match="File is not a valid image",
    ):
        analyzer.analyze(document_image)