from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from app.domain.fingerprints.image_fingerprint import ImageFingerprint
from app.domain.models.document_image import DocumentImage
from app.domain.models.image_hash_analysis import ImageHashAnalysis
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.processors.image_fingerprint_processor import (
    ImageFingerprintProcessor,
)


def create_document_image(
    image_index: int = 1,
    page_number: int = 2,
    xref: int = 15,
    filename: str = "image_1_xref_15.png",
    width: int = 640,
    height: int = 480,
) -> DocumentImage:
    return DocumentImage(
        image_index=image_index,
        page_number=page_number,
        xref=xref,
        filename=filename,
        saved_path=str(Path("temporary") / filename),
        extension=Path(filename).suffix.removeprefix("."),
        width=width,
        height=height,
        size_bytes=2048,
    )


def create_hash_analysis(
    marker: str = "a",
) -> ImageHashAnalysis:
    return ImageHashAnalysis(
        perceptual_hash=marker * 16,
        average_hash="b" * 16,
        difference_hash="c" * 16,
        image_hash="d" * 64,
    )


def test_should_process_document_images() -> None:
    image = create_document_image()
    analysis = create_hash_analysis()

    reader = Mock()
    reader.read.return_value = [image]

    analyzer = Mock()
    analyzer.analyze.return_value = analysis

    processor = ImageFingerprintProcessor(
        reader=reader,
        analyzer=analyzer,
    )

    result = processor.process("document.pdf")

    assert len(result) == 1
    assert isinstance(result[0], ImageFingerprint)

    fingerprint = result[0]

    assert fingerprint.perceptual_hash == analysis.perceptual_hash
    assert fingerprint.average_hash == analysis.average_hash
    assert fingerprint.difference_hash == analysis.difference_hash
    assert fingerprint.image_hash == analysis.image_hash

    assert fingerprint.width == 640
    assert fingerprint.height == 480
    assert fingerprint.location.page_number == 2

    assert fingerprint.location.bounding_box.x == 0.0
    assert fingerprint.location.bounding_box.y == 0.0
    assert fingerprint.location.bounding_box.width == 640.0
    assert fingerprint.location.bounding_box.height == 480.0

    assert fingerprint.confidence == ConfidenceScore(1.0)
    assert fingerprint.mime_type == "image/png"

    reader.read.assert_called_once_with("document.pdf")
    analyzer.analyze.assert_called_once_with(image)


def test_should_process_multiple_images() -> None:
    first_image = create_document_image(
        image_index=1,
        page_number=1,
        xref=10,
        filename="first.png",
        width=100,
        height=200,
    )

    second_image = create_document_image(
        image_index=2,
        page_number=3,
        xref=20,
        filename="second.jpeg",
        width=300,
        height=400,
    )

    first_analysis = create_hash_analysis("1")
    second_analysis = create_hash_analysis("2")

    reader = Mock()
    reader.read.return_value = [
        first_image,
        second_image,
    ]

    analyzer = Mock()
    analyzer.analyze.side_effect = [
        first_analysis,
        second_analysis,
    ]

    processor = ImageFingerprintProcessor(
        reader=reader,
        analyzer=analyzer,
    )

    result = processor.process("multiple-images.pdf")

    assert len(result) == 2

    assert result[0].perceptual_hash == "1" * 16
    assert result[0].location.page_number == 1
    assert result[0].mime_type == "image/png"

    assert result[1].perceptual_hash == "2" * 16
    assert result[1].location.page_number == 3
    assert result[1].mime_type == "image/jpeg"

    assert analyzer.analyze.call_count == 2


def test_should_return_empty_list_when_document_has_no_images() -> None:
    reader = Mock()
    reader.read.return_value = []

    analyzer = Mock()

    processor = ImageFingerprintProcessor(
        reader=reader,
        analyzer=analyzer,
    )

    result = processor.process("document-without-images.pdf")

    assert result == []

    reader.read.assert_called_once_with(
        "document-without-images.pdf"
    )
    analyzer.analyze.assert_not_called()


def test_should_use_informed_confidence() -> None:
    image = create_document_image()
    analysis = create_hash_analysis()

    reader = Mock()
    reader.read.return_value = [image]

    analyzer = Mock()
    analyzer.analyze.return_value = analysis

    processor = ImageFingerprintProcessor(
        reader=reader,
        analyzer=analyzer,
    )

    confidence = ConfidenceScore(0.87)

    result = processor.process(
        source="document.pdf",
        confidence=confidence,
    )

    assert result[0].confidence == confidence


def test_should_create_image_description() -> None:
    image = create_document_image(
        image_index=4,
        page_number=7,
        xref=92,
    )

    reader = Mock()
    reader.read.return_value = [image]

    analyzer = Mock()
    analyzer.analyze.return_value = create_hash_analysis()

    processor = ImageFingerprintProcessor(
        reader=reader,
        analyzer=analyzer,
    )

    result = processor.process("document.pdf")

    assert result[0].description == (
        "Imagem 4 extraída da página 7, xref 92."
    )


def test_should_preserve_processing_error() -> None:
    image = create_document_image()

    reader = Mock()
    reader.read.return_value = [image]

    analyzer = Mock()
    analyzer.analyze.side_effect = ValueError(
        "Image could not be processed."
    )

    processor = ImageFingerprintProcessor(
        reader=reader,
        analyzer=analyzer,
    )

    try:
        processor.process("invalid-document.pdf")
    except ValueError as error:
        assert str(error) == "Image could not be processed."
    else:
        raise AssertionError(
            "The analyzer error should have been propagated."
        )