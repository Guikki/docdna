from app.domain.fingerprints.image_fingerprint import ImageFingerprint
from app.domain.models.document_image import DocumentImage
from app.domain.models.image_hash_analysis import ImageHashAnalysis
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation
from app.services.image_fingerprint_builder import ImageFingerprintBuilder


def create_document_image() -> DocumentImage:
    return DocumentImage(
        image_index=1,
        page_number=2,
        xref=15,
        filename="image_1_xref_15.png",
        saved_path="temporary/image_1_xref_15.png",
        extension="png",
        width=640,
        height=480,
        size_bytes=2048,
    )


def create_document_location() -> DocumentLocation:
    return DocumentLocation(
        page_number=2,
        bounding_box=BoundingBox(
            x=10.0,
            y=20.0,
            width=640.0,
            height=480.0,
        ),
    )


def create_hash_analysis() -> ImageHashAnalysis:
    return ImageHashAnalysis(
        perceptual_hash="8000000000000000",
        average_hash="ffffffffffffffff",
        difference_hash="0000000000000000",
        image_hash="a" * 64,
    )


def test_should_build_image_fingerprint_from_analysis() -> None:
    image = create_document_image()
    location = create_document_location()
    confidence = ConfidenceScore(0.98)
    analysis = create_hash_analysis()

    builder = ImageFingerprintBuilder()

    result = builder.build_from_analysis(
        image=image,
        location=location,
        confidence=confidence,
        analysis=analysis,
        dpi=300,
        mime_type="image/png",
        description="Imagem extraída da segunda página.",
    )

    assert isinstance(result, ImageFingerprint)

    assert result.location == location
    assert result.confidence == confidence

    assert result.perceptual_hash == analysis.perceptual_hash
    assert result.average_hash == analysis.average_hash
    assert result.difference_hash == analysis.difference_hash
    assert result.image_hash == analysis.image_hash

    assert result.width == image.width
    assert result.height == image.height

    assert result.dpi == 300
    assert result.mime_type == "image/png"
    assert result.description == "Imagem extraída da segunda página."


def test_should_build_from_analysis_without_optional_metadata() -> None:
    image = create_document_image()
    location = create_document_location()
    confidence = ConfidenceScore(1.0)
    analysis = create_hash_analysis()

    builder = ImageFingerprintBuilder()

    result = builder.build_from_analysis(
        image=image,
        location=location,
        confidence=confidence,
        analysis=analysis,
    )

    assert result.dpi is None
    assert result.mime_type is None
    assert result.description is None


def test_build_from_analysis_should_preserve_image_dimensions() -> None:
    image = DocumentImage(
        image_index=3,
        page_number=4,
        xref=22,
        filename="image_3_xref_22.jpeg",
        saved_path="temporary/image_3_xref_22.jpeg",
        extension="jpeg",
        width=1920,
        height=1080,
        size_bytes=4096,
    )

    location = DocumentLocation(
        page_number=4,
        bounding_box=BoundingBox(
            x=0.0,
            y=0.0,
            width=1920.0,
            height=1080.0,
        ),
    )

    analysis = create_hash_analysis()

    builder = ImageFingerprintBuilder()

    result = builder.build_from_analysis(
        image=image,
        location=location,
        confidence=ConfidenceScore(0.95),
        analysis=analysis,
    )

    assert result.width == 1920
    assert result.height == 1080