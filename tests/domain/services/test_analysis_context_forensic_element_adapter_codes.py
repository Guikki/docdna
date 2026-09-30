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
from app.domain.services.canonical_forensic_index import (
    CanonicalForensicIndex,
)
from app.domain.services.forensic_canonicalizers import (
    canonicalize_compact_alphanumeric,
    canonicalize_trimmed,
)
from app.domain.services.forensic_element_catalog import (
    ForensicElementCatalog,
)


DOCUMENT_HASH = "a" * 64
BARCODE_IMAGE_HASH = "b" * 64


def create_location(
    *,
    page_number: int = 1,
):
    return SimpleNamespace(
        page_number=page_number,
        bounding_box=SimpleNamespace(
            x=10.0,
            y=20.0,
            width=120.0,
            height=60.0,
        ),
    )


def create_barcode(
    *,
    barcode_index: int = 1,
    page_number: int = 1,
    format: str = "ITF",
    content: str = "1234567890",
    location=None,
    image_hash: str | None = BARCODE_IMAGE_HASH,
):
    return SimpleNamespace(
        barcode_index=barcode_index,
        page_number=page_number,
        format=format,
        content=content,
        location=(
            location
            if location is not None
            else create_location(
                page_number=page_number
            )
        ),
        image_hash=image_hash,
        orientation=90.0,
        error_correction=None,
        content_type="text",
    )


def create_qrcode_fingerprint(
    *,
    value: str = "PIX|123456789",
    page_number: int = 1,
    image_hash: str | None = BARCODE_IMAGE_HASH,
):
    return SimpleNamespace(
        location=create_location(
            page_number=page_number
        ),
        confidence=SimpleNamespace(
            value=1.0
        ),
        value=value,
        encoding=None,
        version=None,
        error_correction="M",
        image_hash=image_hash,
        rotation=0.0,
    )


def create_context(
    *,
    document_id=None,
    barcodes=None,
    qrcode_fingerprints=None,
    printed_numeric_lines=None,
    numeric_line_validations=None,
    numeric_line_locations=None,
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
        sha256=DOCUMENT_HASH,
        images=[],
        image_fingerprints=[],
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


def test_should_create_barcode_element() -> None:
    context = create_context(
        barcodes=[
            create_barcode(
                format="ITF",
                content="1234567890",
            )
        ]
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    barcode = next(
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.BARCODE
        )
    )

    assert barcode.subtype == "itf"
    assert barcode.value == "1234567890"

    assert (
        barcode.provenance.layer
        is ForensicDataLayer.EXTRACTED
    )

    assert (
        barcode.provenance.producer
        == "BarcodeReader"
    )


def test_should_preserve_barcode_metadata() -> None:
    context = create_context(
        barcodes=[
            create_barcode(
                barcode_index=7,
                page_number=3,
            )
        ]
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    barcode = next(
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.BARCODE
        )
    )

    assert (
        barcode.metadata[
            "barcode_index"
        ]
        == 7
    )

    assert (
        barcode.metadata[
            "format"
        ]
        == "ITF"
    )

    assert (
        barcode.metadata[
            "orientation"
        ]
        == 90.0
    )

    assert (
        barcode.metadata[
            "image_hash"
        ]
        == BARCODE_IMAGE_HASH
    )

    assert barcode.page_number == 3


def test_should_preserve_barcode_location() -> None:
    context = create_context(
        barcodes=[
            create_barcode()
        ]
    )

    barcode = next(
        element
        for element in (
            AnalysisContextForensicElementAdapter()
            .build(
                context
            )
        )
        if (
            element.element_type
            is ForensicElementType.BARCODE
        )
    )

    location = (
        barcode.metadata[
            "location"
        ]
    )

    assert (
        location["page_number"]
        == 1
    )

    assert (
        location[
            "bounding_box"
        ]["x"]
        == 10.0
    )

    assert (
        location[
            "bounding_box"
        ]["width"]
        == 120.0
    )


def test_should_normalize_barcode_format_only_for_subtype() -> None:
    context = create_context(
        barcodes=[
            create_barcode(
                format=" QR_CODE ",
                content="PIX|123",
            )
        ],
        qrcode_fingerprints=[
            create_qrcode_fingerprint(
                value="PIX|123",
            )
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    barcode = next(
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.BARCODE
        )
    )

    assert (
        barcode.subtype
        == "qrcode"
    )

    assert (
        barcode.metadata["format"]
        == " QR_CODE "
    )


def test_should_create_qrcode_as_child_of_barcode() -> None:
    context = create_context(
        barcodes=[
            create_barcode(
                format="QRCode",
                content="PIX|123456789",
            )
        ],
        qrcode_fingerprints=[
            create_qrcode_fingerprint()
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    barcode = next(
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.BARCODE
        )
    )

    qrcode = next(
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.QRCODE
        )
    )

    assert (
        qrcode.parent_element_id
        == barcode.element_id
    )

    assert (
        qrcode.provenance.layer
        is ForensicDataLayer.DERIVED
    )

    assert (
        qrcode.provenance.producer
        == "QRCodeFingerprintProcessor"
    )


def test_should_preserve_qrcode_payload() -> None:
    payload = (
        "https://docdna.test/ABC?x=1"
    )

    context = create_context(
        barcodes=[
            create_barcode(
                format="QR Code",
                content=payload,
            )
        ],
        qrcode_fingerprints=[
            create_qrcode_fingerprint(
                value=payload,
            )
        ],
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    qrcode = next(
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.QRCODE
        )
    )

    assert qrcode.value == payload


def test_should_preserve_qrcode_metadata() -> None:
    context = create_context(
        barcodes=[
            create_barcode(
                format="QR",
                content="PIX|123456789",
            )
        ],
        qrcode_fingerprints=[
            create_qrcode_fingerprint()
        ],
    )

    qrcode = next(
        element
        for element in (
            AnalysisContextForensicElementAdapter()
            .build(
                context
            )
        )
        if (
            element.element_type
            is ForensicElementType.QRCODE
        )
    )

    assert (
        qrcode.metadata[
            "image_hash"
        ]
        == BARCODE_IMAGE_HASH
    )

    assert (
        qrcode.metadata[
            "error_correction"
        ]
        == "M"
    )

    assert (
        qrcode.metadata[
            "confidence"
        ]
        == 1.0
    )


def test_non_qr_barcode_should_not_create_qrcode() -> None:
    context = create_context(
        barcodes=[
            create_barcode(
                format="ITF",
            )
        ]
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    qrcodes = [
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.QRCODE
        )
    ]

    assert qrcodes == []


def test_qr_without_location_should_not_require_fingerprint() -> None:
    barcode = create_barcode(
        format="QR",
        content="PIX|123",
    )

    barcode.location = None

    context = create_context(
        barcodes=[
            barcode
        ]
    )

    elements = (
        AnalysisContextForensicElementAdapter()
        .build(
            context
        )
    )

    barcodes = [
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.BARCODE
        )
    ]

    qrcodes = [
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.QRCODE
        )
    ]

    assert len(barcodes) == 1
    assert qrcodes == []


def test_should_reject_qrcode_count_mismatch() -> None:
    context = create_context(
        barcodes=[
            create_barcode(
                format="QR",
                content="PIX|123",
            )
        ],
        qrcode_fingerprints=[],
    )

    with pytest.raises(
        ValueError,
        match="quantidade de QR Codes",
    ):
        (
            AnalysisContextForensicElementAdapter()
            .build(
                context
            )
        )


def test_should_reject_qrcode_content_mismatch() -> None:
    context = create_context(
        barcodes=[
            create_barcode(
                format="QR",
                content="PIX|ORIGINAL",
            )
        ],
        qrcode_fingerprints=[
            create_qrcode_fingerprint(
                value="PIX|DIFERENTE",
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="conteúdo do QR fingerprint",
    ):
        (
            AnalysisContextForensicElementAdapter()
            .build(
                context
            )
        )


def test_should_reject_qrcode_page_mismatch() -> None:
    context = create_context(
        barcodes=[
            create_barcode(
                format="QR",
                content="PIX|123",
                page_number=1,
            )
        ],
        qrcode_fingerprints=[
            create_qrcode_fingerprint(
                value="PIX|123",
                page_number=2,
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="página do QR fingerprint",
    ):
        (
            AnalysisContextForensicElementAdapter()
            .build(
                context
            )
        )


def test_barcode_ids_should_be_deterministic() -> None:
    document_id = uuid4()

    context = create_context(
        document_id=document_id,
        barcodes=[
            create_barcode(
                barcode_index=5,
            )
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

    first_barcode = next(
        element
        for element in first
        if (
            element.element_type
            is ForensicElementType.BARCODE
        )
    )

    second_barcode = next(
        element
        for element in second
        if (
            element.element_type
            is ForensicElementType.BARCODE
        )
    )

    assert (
        first_barcode.element_id
        == second_barcode.element_id
    )


def test_qrcode_ids_should_be_deterministic() -> None:
    document_id = uuid4()

    context = create_context(
        document_id=document_id,
        barcodes=[
            create_barcode(
                barcode_index=9,
                format="QR",
                content="PIX|123",
            )
        ],
        qrcode_fingerprints=[
            create_qrcode_fingerprint(
                value="PIX|123",
            )
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

    first_qr = next(
        element
        for element in first
        if (
            element.element_type
            is ForensicElementType.QRCODE
        )
    )

    second_qr = next(
        element
        for element in second
        if (
            element.element_type
            is ForensicElementType.QRCODE
        )
    )

    assert (
        first_qr.element_id
        == second_qr.element_id
    )


def test_should_add_barcode_and_qrcode_to_catalog() -> None:
    context = create_context(
        barcodes=[
            create_barcode(
                format="QR",
                content="PIX|123",
            )
        ],
        qrcode_fingerprints=[
            create_qrcode_fingerprint(
                value="PIX|123",
            )
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

    catalog.add_many(
        elements
    )

    assert len(
        catalog.by_type(
            ForensicElementType.BARCODE
        )
    ) == 1

    assert len(
        catalog.by_type(
            ForensicElementType.QRCODE
        )
    ) == 1


def test_barcode_canonical_index_should_group_formatted_content(
) -> None:
    first_context = create_context(
        document_id=uuid4(),
        barcodes=[
            create_barcode(
                format="ITF",
                content="1234 5678-90",
            )
        ],
    )

    second_context = create_context(
        document_id=uuid4(),
        barcodes=[
            create_barcode(
                format="ITF",
                content="1234567890",
            )
        ],
    )

    adapter = (
        AnalysisContextForensicElementAdapter()
    )

    elements = (
        adapter.build(
            first_context
        )
        + adapter.build(
            second_context
        )
    )

    barcode_elements = [
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.BARCODE
            and element.subtype
            == "itf"
        )
    ]

    index = CanonicalForensicIndex(
        key_type="itf_content",
        element_type=(
            ForensicElementType.BARCODE
        ),
        subtype="itf",
        canonicalizer=(
            canonicalize_compact_alphanumeric
        ),
    )

    index.add_many(
        barcode_elements
    )

    groups = (
        index.duplicate_groups(
            cross_document_only=True,
        )
    )

    assert len(groups) == 1

    assert (
        groups[0].element_count
        == 2
    )

    assert (
        groups[0]
        .cross_document_pairwise_relations
        == 1
    )


def test_qrcode_index_should_preserve_payload_semantics() -> None:
    payload = (
        "https://docdna.test/ABC"
    )

    first_context = create_context(
        document_id=uuid4(),
        barcodes=[
            create_barcode(
                format="QR",
                content=payload,
            )
        ],
        qrcode_fingerprints=[
            create_qrcode_fingerprint(
                value=payload,
            )
        ],
    )

    second_context = create_context(
        document_id=uuid4(),
        barcodes=[
            create_barcode(
                format="QR",
                content=f"  {payload}  ",
            )
        ],
        qrcode_fingerprints=[
            create_qrcode_fingerprint(
                value=f"  {payload}  ",
            )
        ],
    )

    adapter = (
        AnalysisContextForensicElementAdapter()
    )

    elements = (
        adapter.build(
            first_context
        )
        + adapter.build(
            second_context
        )
    )

    qrcodes = [
        element
        for element in elements
        if (
            element.element_type
            is ForensicElementType.QRCODE
        )
    ]

    index = CanonicalForensicIndex(
        key_type="qrcode_payload",
        element_type=(
            ForensicElementType.QRCODE
        ),
        subtype="qrcode",
        canonicalizer=(
            canonicalize_trimmed
        ),
    )

    index.add_many(
        qrcodes
    )

    groups = (
        index.duplicate_groups(
            cross_document_only=True,
        )
    )

    assert len(groups) == 1

    assert (
        groups[0].key_value
        == payload
    )