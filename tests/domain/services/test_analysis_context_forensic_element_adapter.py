from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.models.forensic_data_layer import (
    ForensicDataLayer,
)
from app.domain.models.forensic_element_type import (
    ForensicElementType,
)
from app.domain.services.analysis_context_forensic_element_adapter import (
    AnalysisContextForensicElementAdapter,
)
from app.domain.services.forensic_element_catalog import (
    ForensicElementCatalog,
)
from app.domain.services.sha256_forensic_index import (
    Sha256ForensicIndex,
)


DOCUMENT_HASH = "a" * 64
IMAGE_HASH_A = "b" * 64
IMAGE_HASH_B = "c" * 64


def create_image(
    *,
    image_index: int = 1,
    page_number: int = 1,
    saved_path: str = "storage/image_1.png",
    filename: str = "image_1.png",
    xref: int = 10,
    width: int = 640,
    height: int = 480,
):
    return SimpleNamespace(
        image_index=image_index,
        page_number=page_number,
        saved_path=saved_path,
        filename=filename,
        xref=xref,
        width=width,
        height=height,
    )


def create_fingerprint(
    *,
    image_hash: str | None = IMAGE_HASH_A,
    perceptual_hash: str = "1111111111111111",
    average_hash: str | None = "2222222222222222",
    difference_hash: str | None = "3333333333333333",
    dpi: int | None = 300,
    mime_type: str | None = "image/png",
    description: str | None = "Imagem extraída",
):
    return SimpleNamespace(
        image_hash=image_hash,
        perceptual_hash=perceptual_hash,
        average_hash=average_hash,
        difference_hash=difference_hash,
        dpi=dpi,
        mime_type=mime_type,
        description=description,
        confidence=SimpleNamespace(
            value=1.0
        ),
    )


def create_context(
    *,
    images=None,
    image_fingerprints=None,
    barcodes=None,
    qrcode_fingerprints=None,
    document_id=None,
    printed_numeric_lines=None,
    numeric_line_validations=None,
    numeric_line_locations=None,
    sha256: str = DOCUMENT_HASH,
):
    return SimpleNamespace(
        document_id=(
            document_id or uuid4()
        ),
        original_filename="documento.pdf",
        stored_filename="stored.pdf",
        saved_path="storage/documento.pdf",
        extension=".pdf",
        mime_type="application/pdf",
        size_bytes=12345,
        sha256=sha256,
        images=(
            images
            if images is not None
            else []
        ),
        image_fingerprints=(
            image_fingerprints
            if image_fingerprints
            is not None
            else []
        ),
        barcodes=(
            barcodes
            if barcodes is not None
            else []
        ),
        qrcode_fingerprints=(
            qrcode_fingerprints
            if qrcode_fingerprints
            is not None
            else []
        ),
        printed_numeric_lines=(
            printed_numeric_lines
            if printed_numeric_lines
               is not None
            else []
        ),
        numeric_line_validations=(
            numeric_line_validations
            if numeric_line_validations
               is not None
            else []
        ),
        numeric_line_locations=(
            numeric_line_locations
            if numeric_line_locations
               is not None
            else []
        ),
    )


def test_should_create_document_and_sha256_elements() -> None:
    adapter = (
        AnalysisContextForensicElementAdapter()
    )

    context = create_context()

    elements = adapter.build(
        context
    )

    assert len(elements) == 2

    document = elements[0]
    document_hash = elements[1]

    assert (
        document.element_type
        is ForensicElementType.DOCUMENT
    )

    assert (
        document.provenance.layer
        is ForensicDataLayer.SOURCE
    )

    assert (
        document.subtype
        == "pdf_document"
    )

    assert (
        document.content_ref
        == "storage/documento.pdf"
    )

    assert (
        document_hash.element_type
        is ForensicElementType.HASH
    )

    assert (
        document_hash.subtype
        == "sha256"
    )

    assert (
        document_hash.value
        == DOCUMENT_HASH
    )


def test_document_hash_should_reference_document_element() -> None:
    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            create_context()
        )
    )

    document = elements[0]
    document_hash = elements[1]

    assert (
        document_hash.parent_element_id
        == document.element_id
    )


def test_should_create_image_and_all_hash_elements() -> None:
    context = create_context(
        images=[
            create_image()
        ],
        image_fingerprints=[
            create_fingerprint()
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    # Documento + SHA do documento
    # + imagem
    # + SHA/pHash/aHash/dHash da imagem.
    assert len(elements) == 7

    assert (
        elements[2].element_type
        is ForensicElementType.IMAGE
    )

    hash_subtypes = [
        element.subtype
        for element in elements
        if (
            element.element_type
            is ForensicElementType.HASH
        )
    ]

    assert hash_subtypes == [
        "sha256",
        "sha256",
        "phash",
        "ahash",
        "dhash",
    ]


def test_image_should_reference_document_element() -> None:
    context = create_context(
        images=[
            create_image()
        ],
        image_fingerprints=[
            create_fingerprint()
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    document = elements[0]
    image = elements[2]

    assert (
        image.parent_element_id
        == document.element_id
    )


def test_image_hashes_should_reference_image_element() -> None:
    context = create_context(
        images=[
            create_image()
        ],
        image_fingerprints=[
            create_fingerprint()
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    image = elements[2]

    image_hashes = elements[
        3:
    ]

    assert all(
        element.parent_element_id
        == image.element_id
        for element in image_hashes
    )


def test_should_preserve_image_content_reference() -> None:
    context = create_context(
        images=[
            create_image(
                saved_path=(
                    "storage/extracted/"
                    "image_42.png"
                )
            )
        ],
        image_fingerprints=[
            create_fingerprint()
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    image = elements[2]

    assert (
        image.content_ref
        == (
            "storage/extracted/"
            "image_42.png"
        )
    )


def test_should_preserve_image_metadata() -> None:
    context = create_context(
        images=[
            create_image(
                image_index=7,
                page_number=3,
                xref=99,
                width=1920,
                height=1080,
            )
        ],
        image_fingerprints=[
            create_fingerprint(
                dpi=300,
                mime_type="image/png",
                description="Imagem 7",
            )
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    image = elements[2]

    assert (
        image.metadata["image_index"]
        == 7
    )

    assert (
        image.metadata["xref"]
        == 99
    )

    assert (
        image.metadata["width"]
        == 1920
    )

    assert (
        image.metadata["height"]
        == 1080
    )

    assert (
        image.metadata["dpi"]
        == 300
    )

    assert (
        image.metadata["mime_type"]
        == "image/png"
    )

    assert (
        image.metadata["confidence"]
        == 1.0
    )


def test_should_preserve_image_page_number() -> None:
    context = create_context(
        images=[
            create_image(
                page_number=8,
            )
        ],
        image_fingerprints=[
            create_fingerprint()
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    image = elements[2]

    assert image.page_number == 8

    for element in elements[3:]:
        assert element.page_number == 8


def test_should_preserve_original_hash_values() -> None:
    original_phash = (
        "ABCDEF0123456789"
    )

    context = create_context(
        images=[
            create_image()
        ],
        image_fingerprints=[
            create_fingerprint(
                perceptual_hash=(
                    original_phash
                ),
            )
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    phash = next(
        element
        for element in elements
        if element.subtype == "phash"
    )

    assert (
        phash.value
        == original_phash
    )


def test_should_skip_optional_empty_hashes() -> None:
    context = create_context(
        images=[
            create_image()
        ],
        image_fingerprints=[
            create_fingerprint(
                image_hash=None,
                average_hash=None,
                difference_hash=None,
            )
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    # Documento + SHA do documento
    # + imagem + pHash.
    assert len(elements) == 4

    assert (
        elements[-1].subtype
        == "phash"
    )


def test_should_generate_same_ids_when_rebuilt() -> None:
    document_id = uuid4()

    context = create_context(
        document_id=document_id,
        images=[
            create_image(
                image_index=5,
            )
        ],
        image_fingerprints=[
            create_fingerprint()
        ],
    )

    adapter = (
        AnalysisContextForensicElementAdapter()
    )

    first = adapter.build(
        context
    )

    second = adapter.build(
        context
    )

    assert [
        element.element_id
        for element in first
    ] == [
        element.element_id
        for element in second
    ]


def test_different_images_should_have_different_ids() -> None:
    context = create_context(
        images=[
            create_image(
                image_index=1,
                saved_path="image_1.png",
            ),
            create_image(
                image_index=2,
                saved_path="image_2.png",
            ),
        ],
        image_fingerprints=[
            create_fingerprint(
                image_hash=IMAGE_HASH_A,
            ),
            create_fingerprint(
                image_hash=IMAGE_HASH_B,
            ),
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    images = [
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.IMAGE
        )
    ]

    assert len(images) == 2

    assert (
        images[0].element_id
        != images[1].element_id
    )


def test_should_reject_image_fingerprint_count_mismatch() -> None:
    context = create_context(
        images=[
            create_image(),
            create_image(
                image_index=2,
            ),
        ],
        image_fingerprints=[
            create_fingerprint(),
        ],
    )

    with pytest.raises(
        ValueError,
        match="quantidade de imagens",
    ):
        (
            AnalysisContextForensicElementAdapter()
            .build(
                context
            )
        )


def test_should_add_adapted_elements_to_catalog() -> None:
    context = create_context(
        images=[
            create_image()
        ],
        image_fingerprints=[
            create_fingerprint()
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    catalog = (
        ForensicElementCatalog()
    )

    added = catalog.add_many(
        elements
    )

    assert added == len(
        elements
    )

    assert len(catalog) == len(
        elements
    )

    assert len(
        catalog.by_type(
            ForensicElementType.IMAGE
        )
    ) == 1


def test_sha256_index_should_group_equal_image_hashes_without_pairs(
) -> None:
    context = create_context(
        images=[
            create_image(
                image_index=1,
                saved_path="image_1.png",
            ),
            create_image(
                image_index=2,
                saved_path="image_2.png",
            ),
        ],
        image_fingerprints=[
            create_fingerprint(
                image_hash=IMAGE_HASH_A,
            ),
            create_fingerprint(
                image_hash=IMAGE_HASH_A,
            ),
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    sha_elements = [
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.HASH
            and element.subtype
            == "sha256"
        )
    ]

    index = (
        Sha256ForensicIndex()
    )

    index.add_many(
        sha_elements
    )

    groups = (
        index.duplicate_groups()
    )

    assert len(groups) == 1

    group = groups[0]

    assert group.element_count == 2
    assert group.pairwise_relations == 1


def test_same_image_hash_in_same_document_should_not_be_cross_document(
) -> None:
    context = create_context(
        images=[
            create_image(
                image_index=1,
                saved_path="image_1.png",
            ),
            create_image(
                image_index=2,
                saved_path="image_2.png",
            ),
        ],
        image_fingerprints=[
            create_fingerprint(
                image_hash=IMAGE_HASH_A,
            ),
            create_fingerprint(
                image_hash=IMAGE_HASH_A,
            ),
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    sha_elements = [
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.HASH
            and element.subtype
            == "sha256"
        )
    ]

    index = (
        Sha256ForensicIndex()
    )

    index.add_many(
        sha_elements
    )

    assert (
        index.duplicate_groups(
            cross_document_only=True,
        )
        == ()
    )