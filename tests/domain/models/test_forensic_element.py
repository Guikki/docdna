from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.models.forensic_data_layer import (
    ForensicDataLayer,
)
from app.domain.models.forensic_element import (
    ForensicElement,
)
from app.domain.models.forensic_element_type import (
    ForensicElementType,
)
from app.domain.models.forensic_provenance import (
    ForensicProvenance,
)


def _provenance(
    *,
    layer: ForensicDataLayer = ForensicDataLayer.EXTRACTED,
    page_number: int | None = 1,
    parent_element_id=None,
) -> ForensicProvenance:
    return ForensicProvenance(
        document_id=uuid4(),
        layer=layer,
        producer="OcrReader",
        producer_version="1.0",
        page_number=page_number,
        parent_element_id=parent_element_id,
    )


def test_should_create_forensic_element() -> None:
    provenance = _provenance()

    element = ForensicElement(
        element_type=ForensicElementType.TEXT,
        subtype="ocr_text",
        value="Texto extraído",
        provenance=provenance,
    )

    assert element.element_type is ForensicElementType.TEXT
    assert element.subtype == "ocr_text"
    assert element.value == "Texto extraído"
    assert element.document_id == provenance.document_id
    assert element.page_number == 1


def test_should_generate_element_id_automatically() -> None:
    first = ForensicElement(
        element_type=ForensicElementType.TEXT,
        value="A",
        provenance=_provenance(),
    )

    second = ForensicElement(
        element_type=ForensicElementType.TEXT,
        value="B",
        provenance=_provenance(),
    )

    assert first.element_id != second.element_id


def test_should_preserve_original_value_whitespace() -> None:
    original = "  R$ 1.250,OO  "

    element = ForensicElement(
        element_type=ForensicElementType.TEXT,
        subtype="ocr_text",
        value=original,
        provenance=_provenance(),
    )

    assert element.value == original


def test_should_support_derived_element_lineage() -> None:
    original_element_id = uuid4()

    provenance = _provenance(
        layer=ForensicDataLayer.DERIVED,
        parent_element_id=original_element_id,
    )

    element = ForensicElement(
        element_type=ForensicElementType.TEXT,
        subtype="money",
        value="1250.00",
        provenance=provenance,
    )

    assert element.parent_element_id == original_element_id
    assert element.provenance.layer is ForensicDataLayer.DERIVED


def test_should_support_hash_as_derived_data() -> None:
    image_element_id = uuid4()

    element = ForensicElement(
        element_type=ForensicElementType.HASH,
        subtype="sha256",
        value="a" * 64,
        provenance=_provenance(
            layer=ForensicDataLayer.DERIVED,
            parent_element_id=image_element_id,
        ),
    )

    assert element.element_type is ForensicElementType.HASH
    assert element.subtype == "sha256"
    assert element.parent_element_id == image_element_id


def test_should_support_binary_content_reference() -> None:
    element = ForensicElement(
        element_type=ForensicElementType.IMAGE,
        subtype="generic_image",
        content_ref="storage/extracted/image_001.png",
        provenance=_provenance(),
        metadata={
            "width": 640,
            "height": 480,
        },
    )

    assert (
        element.content_ref
        == "storage/extracted/image_001.png"
    )
    assert element.metadata["width"] == 640
    assert element.metadata["height"] == 480


def test_should_copy_metadata_on_creation() -> None:
    source_metadata = {
        "width": 640,
    }

    element = ForensicElement(
        element_type=ForensicElementType.IMAGE,
        provenance=_provenance(),
        metadata=source_metadata,
    )

    source_metadata["width"] = 1920

    assert element.metadata["width"] == 640


def test_metadata_should_be_read_only() -> None:
    element = ForensicElement(
        element_type=ForensicElementType.IMAGE,
        provenance=_provenance(),
        metadata={
            "width": 640,
        },
    )

    with pytest.raises(TypeError):
        element.metadata["width"] = 1920  # type: ignore[index]


def test_should_require_some_element_content() -> None:
    with pytest.raises(
        ValueError,
        match="must contain value, content_ref or metadata",
    ):
        ForensicElement(
            element_type=ForensicElementType.TEXT,
            provenance=_provenance(),
        )


def test_should_reject_invalid_element_type() -> None:
    with pytest.raises(TypeError):
        ForensicElement(
            element_type="text",  # type: ignore[arg-type]
            value="Texto",
            provenance=_provenance(),
        )


def test_should_reject_invalid_provenance() -> None:
    with pytest.raises(TypeError):
        ForensicElement(
            element_type=ForensicElementType.TEXT,
            value="Texto",
            provenance=None,  # type: ignore[arg-type]
        )


def test_should_trim_producer_and_version() -> None:
    provenance = ForensicProvenance(
        document_id=uuid4(),
        layer=ForensicDataLayer.EXTRACTED,
        producer="  OcrReader  ",
        producer_version="  1.0  ",
        page_number=1,
    )

    assert provenance.producer == "OcrReader"
    assert provenance.producer_version == "1.0"


@pytest.mark.parametrize(
    "page_number",
    [
        0,
        -1,
        -10,
    ],
)
def test_should_reject_invalid_page_number(
    page_number: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="page_number",
    ):
        ForensicProvenance(
            document_id=uuid4(),
            layer=ForensicDataLayer.EXTRACTED,
            producer="OcrReader",
            producer_version="1.0",
            page_number=page_number,
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_should_reject_empty_producer(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        ForensicProvenance(
            document_id=uuid4(),
            layer=ForensicDataLayer.EXTRACTED,
            producer=value,
            producer_version="1.0",
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_should_reject_empty_producer_version(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        ForensicProvenance(
            document_id=uuid4(),
            layer=ForensicDataLayer.EXTRACTED,
            producer="OcrReader",
            producer_version=value,
        )