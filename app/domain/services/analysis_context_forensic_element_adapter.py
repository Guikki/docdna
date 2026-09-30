from __future__ import annotations

from typing import Any
from uuid import UUID

from app.domain.models.analysis_context import (
    AnalysisContext,
)
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
from app.domain.services.forensic_element_identity_factory import (
    ForensicElementIdentityFactory,
)
from app.domain.services.numeric_line_forensic_element_adapter import (
    NumericLineForensicElementAdapter,
)

class AnalysisContextForensicElementAdapter:
    """
    Converte dados já produzidos pelo AnalysisContext em elementos
    pertencentes ao modelo forense canônico.

    Nesta etapa são adaptados:

    - documento de origem;
    - SHA-256 do documento;
    - imagens extraídas;
    - SHA-256 das imagens;
    - pHash;
    - aHash;
    - dHash;
    - códigos de barras;
    - QR Codes derivados dos códigos detectados.

    O adapter não recalcula hashes, não relê o documento e não
    realiza comparações.

    Sua responsabilidade é transformar fatos técnicos já existentes
    em ForensicElement, preservando identidade e proveniência.
    """

    VERSION = "1.0"

    QR_CODE_FORMATS = {
        "qr",
        "qrcode",
    }

    def build(
            self,
            context: AnalysisContext,
    ) -> tuple[ForensicElement, ...]:
        self._validate_image_alignment(
            context
        )

        qr_barcodes = (
            self._eligible_qr_barcodes(
                context
            )
        )

        self._validate_qrcode_alignment(
            context=context,
            qr_barcodes=qr_barcodes,
        )

        elements: list[
            ForensicElement
        ] = []

        document_element = (
            self._build_document_element(
                context
            )
        )

        elements.append(
            document_element
        )

        elements.append(
            self._build_document_sha256_element(
                context=context,
                parent_element_id=(
                    document_element.element_id
                ),
            )
        )

        for image, fingerprint in zip(
                context.images,
                context.image_fingerprints,
        ):
            image_element = (
                self._build_image_element(
                    context=context,
                    image=image,
                    fingerprint=fingerprint,
                    parent_element_id=(
                        document_element.element_id
                    ),
                )
            )

            elements.append(
                image_element
            )

            elements.extend(
                self._build_image_hash_elements(
                    context=context,
                    image=image,
                    fingerprint=fingerprint,
                    parent_element_id=(
                        image_element.element_id
                    ),
                )
            )

        barcode_elements: dict[
            int,
            ForensicElement,
        ] = {}

        for barcode in context.barcodes:
            barcode_element = (
                self._build_barcode_element(
                    context=context,
                    barcode=barcode,
                    parent_element_id=(
                        document_element.element_id
                    ),
                )
            )

            elements.append(
                barcode_element
            )

            barcode_elements[
                barcode.barcode_index
            ] = barcode_element

        for barcode, fingerprint in zip(
                qr_barcodes,
                context.qrcode_fingerprints,
        ):
            barcode_element = (
                barcode_elements[
                    barcode.barcode_index
                ]
            )

            elements.append(
                self._build_qrcode_element(
                    context=context,
                    barcode=barcode,
                    fingerprint=fingerprint,
                    parent_element_id=(
                        barcode_element.element_id
                    ),
                )
            )

        numeric_line_elements = (
            NumericLineForensicElementAdapter()
            .build(
                document_id=(
                    context.document_id
                ),
                lines=(
                    context
                    .printed_numeric_lines
                ),
                validations=(
                    context
                    .numeric_line_validations
                ),
                locations=(
                    context
                    .numeric_line_locations
                ),
            )
        )

        elements.extend(
            numeric_line_elements
        )

        return tuple(
            elements
        )

    def _build_document_element(
        self,
        context: AnalysisContext,
    ) -> ForensicElement:
        element_id = (
            ForensicElementIdentityFactory.create(
                document_id=(
                    context.document_id
                ),
                source_key="document:source",
            )
        )

        return ForensicElement(
            element_id=element_id,
            element_type=(
                ForensicElementType.DOCUMENT
            ),
            subtype="pdf_document",
            content_ref=context.saved_path,
            metadata={
                "original_filename": (
                    context.original_filename
                ),
                "stored_filename": (
                    context.stored_filename
                ),
                "extension": (
                    context.extension
                ),
                "mime_type": (
                    context.mime_type
                ),
                "size_bytes": (
                    context.size_bytes
                ),
            },
            provenance=ForensicProvenance(
                document_id=(
                    context.document_id
                ),
                layer=(
                    ForensicDataLayer.SOURCE
                ),
                producer="AnalysisContext",
                producer_version=(
                    self.VERSION
                ),
            ),
        )

    def _build_document_sha256_element(
        self,
        *,
        context: AnalysisContext,
        parent_element_id: UUID,
    ) -> ForensicElement:
        return ForensicElement(
            element_id=(
                ForensicElementIdentityFactory
                .document_sha256(
                    document_id=(
                        context.document_id
                    ),
                )
            ),
            element_type=(
                ForensicElementType.HASH
            ),
            subtype="sha256",
            value=context.sha256,
            metadata={
                "scope": "document",
            },
            provenance=ForensicProvenance(
                document_id=(
                    context.document_id
                ),
                layer=(
                    ForensicDataLayer.DERIVED
                ),
                producer=(
                    "AnalysisContextForensicElementAdapter"
                ),
                producer_version=(
                    self.VERSION
                ),
                parent_element_id=(
                    parent_element_id
                ),
            ),
        )

    def _build_image_element(
        self,
        *,
        context: AnalysisContext,
        image: Any,
        fingerprint: Any,
        parent_element_id: UUID,
    ) -> ForensicElement:
        image_index = (
            self._image_index(
                image
            )
        )

        metadata = {
            "image_index": image_index,
            "filename": image.filename,
            "xref": image.xref,
            "width": image.width,
            "height": image.height,
            "dpi": fingerprint.dpi,
            "mime_type": fingerprint.mime_type,
            "description": (
                fingerprint.description
            ),
        }

        confidence = (
            self._confidence_value(
                fingerprint
            )
        )

        if confidence is not None:
            metadata[
                "confidence"
            ] = confidence

        return ForensicElement(
            element_id=(
                ForensicElementIdentityFactory
                .image(
                    document_id=(
                        context.document_id
                    ),
                    image_index=(
                        image_index
                    ),
                )
            ),
            element_type=(
                ForensicElementType.IMAGE
            ),
            subtype="generic_image",
            content_ref=(
                image.saved_path
            ),
            metadata=metadata,
            provenance=ForensicProvenance(
                document_id=(
                    context.document_id
                ),
                layer=(
                    ForensicDataLayer.EXTRACTED
                ),
                producer="ImageReader",
                producer_version=(
                    self.VERSION
                ),
                page_number=(
                    image.page_number
                ),
                parent_element_id=(
                    parent_element_id
                ),
            ),
        )

    def _build_image_hash_elements(
        self,
        *,
        context: AnalysisContext,
        image: Any,
        fingerprint: Any,
        parent_element_id: UUID,
    ) -> list[ForensicElement]:
        image_index = (
            self._image_index(
                image
            )
        )

        hash_values = (
            (
                "sha256",
                fingerprint.image_hash,
            ),
            (
                "phash",
                fingerprint.perceptual_hash,
            ),
            (
                "ahash",
                fingerprint.average_hash,
            ),
            (
                "dhash",
                fingerprint.difference_hash,
            ),
        )

        elements: list[
            ForensicElement
        ] = []

        for (
            hash_type,
            hash_value,
        ) in hash_values:
            if not self._has_value(
                hash_value
            ):
                continue

            elements.append(
                ForensicElement(
                    element_id=(
                        ForensicElementIdentityFactory
                        .image_hash(
                            document_id=(
                                context.document_id
                            ),
                            image_index=(
                                image_index
                            ),
                            hash_type=(
                                hash_type
                            ),
                        )
                    ),
                    element_type=(
                        ForensicElementType.HASH
                    ),
                    subtype=hash_type,
                    value=hash_value,
                    metadata={
                        "scope": "image",
                        "image_index": (
                            image_index
                        ),
                    },
                    provenance=(
                        ForensicProvenance(
                            document_id=(
                                context.document_id
                            ),
                            layer=(
                                ForensicDataLayer.DERIVED
                            ),
                            producer=(
                                "ImageHashAnalyzer"
                            ),
                            producer_version=(
                                self.VERSION
                            ),
                            page_number=(
                                image.page_number
                            ),
                            parent_element_id=(
                                parent_element_id
                            ),
                        )
                    ),
                )
            )

        return elements

    def _build_barcode_element(
        self,
        *,
        context: AnalysisContext,
        barcode: Any,
        parent_element_id: UUID,
    ) -> ForensicElement:
        barcode_index = (
            self._barcode_index(
                barcode
            )
        )

        metadata: dict[
            str,
            Any,
        ] = {
            "barcode_index": (
                barcode_index
            ),
            "format": (
                barcode.format
            ),
            "orientation": (
                barcode.orientation
            ),
            "error_correction": (
                barcode.error_correction
            ),
            "content_type": (
                barcode.content_type
            ),
            "image_hash": (
                barcode.image_hash
            ),
        }

        location_metadata = (
            self._location_metadata(
                barcode.location
            )
        )

        if location_metadata:
            metadata[
                "location"
            ] = location_metadata

        return ForensicElement(
            element_id=(
                ForensicElementIdentityFactory
                .barcode(
                    document_id=(
                        context.document_id
                    ),
                    barcode_index=(
                        barcode_index
                    ),
                )
            ),
            element_type=(
                ForensicElementType.BARCODE
            ),
            subtype=(
                self._normalize_barcode_format(
                    barcode.format
                )
            ),
            value=barcode.content,
            metadata=metadata,
            provenance=ForensicProvenance(
                document_id=(
                    context.document_id
                ),
                layer=(
                    ForensicDataLayer.EXTRACTED
                ),
                producer="BarcodeReader",
                producer_version=(
                    self.VERSION
                ),
                page_number=(
                    barcode.page_number
                ),
                parent_element_id=(
                    parent_element_id
                ),
            ),
        )

    def _build_qrcode_element(
        self,
        *,
        context: AnalysisContext,
        barcode: Any,
        fingerprint: Any,
        parent_element_id: UUID,
    ) -> ForensicElement:
        barcode_index = (
            self._barcode_index(
                barcode
            )
        )

        metadata = {
            "barcode_index": (
                barcode_index
            ),
            "encoding": (
                fingerprint.encoding
            ),
            "version": (
                fingerprint.version
            ),
            "error_correction": (
                fingerprint.error_correction
            ),
            "image_hash": (
                fingerprint.image_hash
            ),
            "rotation": (
                fingerprint.rotation
            ),
        }

        confidence = (
            self._confidence_value(
                fingerprint
            )
        )

        if confidence is not None:
            metadata[
                "confidence"
            ] = confidence

        location_metadata = (
            self._location_metadata(
                fingerprint.location
            )
        )

        if location_metadata:
            metadata[
                "location"
            ] = location_metadata

        return ForensicElement(
            element_id=(
                ForensicElementIdentityFactory
                .qrcode(
                    document_id=(
                        context.document_id
                    ),
                    qrcode_index=(
                        barcode_index
                    ),
                )
            ),
            element_type=(
                ForensicElementType.QRCODE
            ),
            subtype="qrcode",
            value=fingerprint.value,
            metadata=metadata,
            provenance=ForensicProvenance(
                document_id=(
                    context.document_id
                ),
                layer=(
                    ForensicDataLayer.DERIVED
                ),
                producer=(
                    "QRCodeFingerprintProcessor"
                ),
                producer_version=(
                    self.VERSION
                ),
                page_number=(
                    fingerprint.location.page_number
                ),
                parent_element_id=(
                    parent_element_id
                ),
            ),
        )

    def _eligible_qr_barcodes(
        self,
        context: AnalysisContext,
    ) -> list[Any]:
        """
        Reproduz somente a regra estrutural usada pelo processor
        para identificar quais Barcodes originaram QR fingerprints.

        Não há nova detecção ou releitura do PDF nesta etapa.
        """
        return [
            barcode
            for barcode in context.barcodes
            if (
                self._is_qrcode_format(
                    barcode.format
                )
                and barcode.location
                is not None
            )
        ]

    def _validate_qrcode_alignment(
        self,
        *,
        context: AnalysisContext,
        qr_barcodes: list[Any],
    ) -> None:
        """
        Garante que cada QR fingerprint possa ser ligado com segurança
        ao Barcode que lhe deu origem.

        Divergências interrompem a adaptação para evitar a criação
        de uma linhagem incorreta.
        """
        if (
            len(qr_barcodes)
            != len(
                context.qrcode_fingerprints
            )
        ):
            raise ValueError(
                "A quantidade de QR Codes elegíveis e "
                "QR fingerprints deve ser a mesma."
            )

        for barcode, fingerprint in zip(
            qr_barcodes,
            context.qrcode_fingerprints,
        ):
            if (
                barcode.content
                != fingerprint.value
            ):
                raise ValueError(
                    "O conteúdo do QR fingerprint não "
                    "corresponde ao Barcode de origem."
                )

            barcode_page = (
                barcode.page_number
            )

            fingerprint_page = (
                fingerprint.location.page_number
            )

            if (
                barcode_page
                != fingerprint_page
            ):
                raise ValueError(
                    "A página do QR fingerprint não "
                    "corresponde ao Barcode de origem."
                )

    @staticmethod
    def _validate_image_alignment(
        context: AnalysisContext,
    ) -> None:
        """
        Impede a associação silenciosa entre uma imagem e um
        fingerprint que não corresponda à mesma posição.

        Nesta etapa, a pipeline produz as duas coleções na mesma ordem.
        Se as quantidades divergirem, é mais seguro interromper a
        adaptação do que criar uma proveniência incorreta.
        """
        image_count = len(
            context.images
        )

        fingerprint_count = len(
            context.image_fingerprints
        )

        if (
            image_count
            != fingerprint_count
        ):
            raise ValueError(
                "A quantidade de imagens e fingerprints "
                "de imagem deve ser a mesma."
            )

    @staticmethod
    def _image_index(
        image: Any,
    ) -> int:
        image_index = (
            image.image_index
        )

        if (
            not isinstance(
                image_index,
                int,
            )
            or isinstance(
                image_index,
                bool,
            )
        ):
            raise TypeError(
                "image_index deve ser um inteiro."
            )

        if image_index < 0:
            raise ValueError(
                "image_index deve ser maior "
                "ou igual a zero."
            )

        return image_index

    @staticmethod
    def _barcode_index(
        barcode: Any,
    ) -> int:
        barcode_index = (
            barcode.barcode_index
        )

        if (
            not isinstance(
                barcode_index,
                int,
            )
            or isinstance(
                barcode_index,
                bool,
            )
        ):
            raise TypeError(
                "barcode_index deve ser um inteiro."
            )

        if barcode_index < 0:
            raise ValueError(
                "barcode_index deve ser maior "
                "ou igual a zero."
            )

        return barcode_index

    @staticmethod
    def _confidence_value(
        fingerprint: Any,
    ) -> float | None:
        confidence = getattr(
            fingerprint,
            "confidence",
            None,
        )

        if confidence is None:
            return None

        value = getattr(
            confidence,
            "value",
            None,
        )

        if value is None:
            return None

        return float(
            value
        )

    @classmethod
    def _is_qrcode_format(
        cls,
        value: str,
    ) -> bool:
        return (
            cls._normalize_barcode_format(
                value
            )
            in cls.QR_CODE_FORMATS
        )

    @staticmethod
    def _normalize_barcode_format(
        value: Any,
    ) -> str:
        normalized = (
            str(
                value or ""
            )
            .strip()
            .casefold()
            .replace(
                "-",
                "",
            )
            .replace(
                "_",
                "",
            )
            .replace(
                " ",
                "",
            )
        )

        if not normalized:
            return "unknown"

        return normalized

    @staticmethod
    def _location_metadata(
        location: Any,
    ) -> dict[str, Any]:
        if location is None:
            return {}

        bounding_box = getattr(
            location,
            "bounding_box",
            None,
        )

        metadata: dict[
            str,
            Any,
        ] = {
            "page_number": getattr(
                location,
                "page_number",
                None,
            ),
        }

        if bounding_box is not None:
            metadata[
                "bounding_box"
            ] = {
                "x": getattr(
                    bounding_box,
                    "x",
                    None,
                ),
                "y": getattr(
                    bounding_box,
                    "y",
                    None,
                ),
                "width": getattr(
                    bounding_box,
                    "width",
                    None,
                ),
                "height": getattr(
                    bounding_box,
                    "height",
                    None,
                ),
            }

        return metadata

    @staticmethod
    def _has_value(
        value: Any,
    ) -> bool:
        return (
            isinstance(
                value,
                str,
            )
            and bool(
                value.strip()
            )
        )