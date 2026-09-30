from __future__ import annotations

from uuid import UUID

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
from app.domain.models.numeric_line_location import (
    NumericLineLocation,
)
from app.domain.models.numeric_line_validation import (
    NumericLineValidation,
)
from app.domain.models.printed_numeric_line import (
    PrintedNumericLine,
)
from app.domain.services.forensic_element_identity_factory import (
    ForensicElementIdentityFactory,
)


class NumericLineForensicElementAdapter:
    """
    Converte linhas numéricas, validações e localizações visuais
    em elementos pertencentes ao modelo forense canônico.

    Para cada ocorrência podem ser preservados quatro níveis:

    1. conteúdo bruto extraído;
    2. conteúdo numérico normalizado;
    3. resultado da validação estrutural;
    4. localização visual da ocorrência no documento.

    Nenhum desses níveis substitui o anterior.
    """

    VERSION = "1.0"

    def build(
        self,
        *,
        document_id: UUID,
        lines: list[PrintedNumericLine]
        | tuple[PrintedNumericLine, ...],
        validations: list[NumericLineValidation]
        | tuple[NumericLineValidation, ...],
        locations: (
            list[NumericLineLocation]
            | tuple[NumericLineLocation, ...]
            | None
        ) = None,
    ) -> tuple[ForensicElement, ...]:
        if not isinstance(
            document_id,
            UUID,
        ):
            raise TypeError(
                "document_id deve ser um UUID."
            )

        self._validate_alignment(
            lines=lines,
            validations=validations,
        )

        if locations is not None:
            self._validate_locations(
                lines=lines,
                locations=locations,
            )

        elements: list[
            ForensicElement
        ] = []

        for position, (
            line,
            validation,
        ) in enumerate(
            zip(
                lines,
                validations,
            )
        ):
            raw_element = (
                self._build_raw_element(
                    document_id=(
                        document_id
                    ),
                    line=line,
                )
            )

            normalized_element = (
                self._build_normalized_element(
                    document_id=(
                        document_id
                    ),
                    line=line,
                    parent_element_id=(
                        raw_element.element_id
                    ),
                )
            )

            validation_element = (
                self._build_validation_element(
                    document_id=(
                        document_id
                    ),
                    validation=validation,
                    parent_element_id=(
                        normalized_element.element_id
                    ),
                )
            )

            elements.extend(
                [
                    raw_element,
                    normalized_element,
                    validation_element,
                ]
            )

            if locations is not None:
                location = locations[
                    position
                ]

                elements.append(
                    self._build_location_element(
                        document_id=(
                            document_id
                        ),
                        location=location,
                        parent_element_id=(
                            raw_element.element_id
                        ),
                    )
                )

        return tuple(
            elements
        )

    def _build_raw_element(
        self,
        *,
        document_id: UUID,
        line: PrintedNumericLine,
    ) -> ForensicElement:
        return ForensicElement(
            element_id=(
                ForensicElementIdentityFactory
                .numeric_line(
                    document_id=document_id,
                    line_index=(
                        line.line_index
                    ),
                )
            ),
            element_type=(
                ForensicElementType.NUMERIC_LINE
            ),
            subtype="printed_numeric_line",
            value=line.raw_content,
            metadata={
                "line_index": (
                    line.line_index
                ),
                "source": (
                    line.source
                ),
                "digit_count": (
                    line.digit_count
                ),
            },
            provenance=ForensicProvenance(
                document_id=document_id,
                layer=(
                    ForensicDataLayer.EXTRACTED
                ),
                producer=(
                    "PrintedNumericLineReader"
                ),
                producer_version=(
                    self.VERSION
                ),
            ),
        )

    def _build_normalized_element(
        self,
        *,
        document_id: UUID,
        line: PrintedNumericLine,
        parent_element_id: UUID,
    ) -> ForensicElement:
        return ForensicElement(
            element_id=(
                ForensicElementIdentityFactory
                .normalized_numeric_line(
                    document_id=document_id,
                    line_index=(
                        line.line_index
                    ),
                )
            ),
            element_type=(
                ForensicElementType.NUMERIC_LINE
            ),
            subtype=(
                "normalized_numeric_line"
            ),
            value=(
                line.normalized_content
            ),
            metadata={
                "line_index": (
                    line.line_index
                ),
                "digit_count": (
                    line.digit_count
                ),
            },
            provenance=ForensicProvenance(
                document_id=document_id,
                layer=(
                    ForensicDataLayer.DERIVED
                ),
                producer=(
                    "PrintedNumericLineReader"
                ),
                producer_version=(
                    self.VERSION
                ),
                parent_element_id=(
                    parent_element_id
                ),
            ),
        )

    def _build_validation_element(
        self,
        *,
        document_id: UUID,
        validation: NumericLineValidation,
        parent_element_id: UUID,
    ) -> ForensicElement:
        return ForensicElement(
            element_id=(
                ForensicElementIdentityFactory
                .numeric_line_validation(
                    document_id=document_id,
                    line_index=(
                        validation.line_index
                    ),
                )
            ),
            element_type=(
                ForensicElementType.NUMERIC_LINE
            ),
            subtype=(
                "numeric_line_validation"
            ),
            metadata={
                "line_index": (
                    validation.line_index
                ),
                "normalized_content": (
                    validation
                    .normalized_content
                ),
                "line_type": (
                    validation.line_type.value
                ),
                "status": (
                    validation.status.value
                ),
                "digit_count": (
                    validation.digit_count
                ),
                "validation_method": (
                    validation
                    .validation_method
                ),
                "valid_check_digits": (
                    validation
                    .valid_check_digits
                ),
                "total_check_digits": (
                    validation
                    .total_check_digits
                ),
                "message": (
                    validation.message
                ),
            },
            provenance=ForensicProvenance(
                document_id=document_id,
                layer=(
                    ForensicDataLayer.ANALYTICAL
                ),
                producer=(
                    "NumericLineValidator"
                ),
                producer_version=(
                    self.VERSION
                ),
                parent_element_id=(
                    parent_element_id
                ),
            ),
        )

    def _build_location_element(
        self,
        *,
        document_id: UUID,
        location: NumericLineLocation,
        parent_element_id: UUID,
    ) -> ForensicElement:
        content_ref = (
            location.annotated_image_path
            or location.source_image_path
        )

        value = (
            location.matched_content
            if (
                isinstance(
                    location.matched_content,
                    str,
                )
                and location.matched_content.strip()
            )
            else None
        )

        return ForensicElement(
            element_id=(
                ForensicElementIdentityFactory
                .numeric_line_location(
                    document_id=document_id,
                    line_index=(
                        location.line_index
                    ),
                )
            ),
            element_type=(
                ForensicElementType.LOCATION
            ),
            subtype=(
                "numeric_line_location"
            ),
            value=value,
            content_ref=content_ref,
            metadata={
                "line_index": (
                    location.line_index
                ),
                "matched_content": (
                    location.matched_content
                ),
                "left": (
                    location.left
                ),
                "top": (
                    location.top
                ),
                "width": (
                    location.width
                ),
                "height": (
                    location.height
                ),
                "confidence": (
                    location.confidence
                ),
                "source_image_path": (
                    location.source_image_path
                ),
                "annotated_image_path": (
                    location.annotated_image_path
                ),
                "located": (
                    location.located
                ),
                "message": (
                    location.message
                ),
            },
            provenance=ForensicProvenance(
                document_id=document_id,
                layer=(
                    ForensicDataLayer.DERIVED
                ),
                producer=(
                    "NumericLineVisualEvidenceBuilder"
                ),
                producer_version=(
                    self.VERSION
                ),
                page_number=(
                    location.page_number
                ),
                parent_element_id=(
                    parent_element_id
                ),
            ),
        )

    @staticmethod
    def _validate_alignment(
        *,
        lines: list[PrintedNumericLine]
        | tuple[PrintedNumericLine, ...],
        validations: list[NumericLineValidation]
        | tuple[NumericLineValidation, ...],
    ) -> None:
        """
        Garante que cada validação corresponda exatamente à linha
        numérica que lhe deu origem.

        O vínculo não é inferido somente pela posição das listas:
        índice e conteúdo normalizado também precisam coincidir.
        """
        if not isinstance(
            lines,
            (list, tuple),
        ):
            raise TypeError(
                "lines deve ser uma lista ou tupla."
            )

        if not isinstance(
            validations,
            (list, tuple),
        ):
            raise TypeError(
                "validations deve ser uma lista ou tupla."
            )

        if len(lines) != len(
            validations
        ):
            raise ValueError(
                "A quantidade de linhas numéricas e "
                "validações deve ser a mesma."
            )

        for line, validation in zip(
            lines,
            validations,
        ):
            if not isinstance(
                line,
                PrintedNumericLine,
            ):
                raise TypeError(
                    "lines deve conter somente "
                    "PrintedNumericLine."
                )

            if not isinstance(
                validation,
                NumericLineValidation,
            ):
                raise TypeError(
                    "validations deve conter somente "
                    "NumericLineValidation."
                )

            if (
                line.line_index
                != validation.line_index
            ):
                raise ValueError(
                    "O line_index da validação não "
                    "corresponde à linha numérica."
                )

            if (
                line.normalized_content
                != validation.normalized_content
            ):
                raise ValueError(
                    "O conteúdo normalizado da validação não "
                    "corresponde à linha numérica."
                )

    @staticmethod
    def _validate_locations(
        *,
        lines: list[PrintedNumericLine]
        | tuple[PrintedNumericLine, ...],
        locations: list[NumericLineLocation]
        | tuple[NumericLineLocation, ...],
    ) -> None:
        """
        Confirma a correspondência entre cada ocorrência numérica
        e sua localização visual.

        A localização pode ser negativa, isto é, representar uma
        tentativa em que a ocorrência não foi encontrada visualmente.
        Esse resultado também é preservado.
        """
        if not isinstance(
            locations,
            (list, tuple),
        ):
            raise TypeError(
                "locations deve ser uma lista ou tupla."
            )

        if len(lines) != len(
            locations
        ):
            raise ValueError(
                "A quantidade de linhas numéricas e "
                "localizações deve ser a mesma."
            )

        for line, location in zip(
            lines,
            locations,
        ):
            if not isinstance(
                location,
                NumericLineLocation,
            ):
                raise TypeError(
                    "locations deve conter somente "
                    "NumericLineLocation."
                )

            if (
                line.line_index
                != location.line_index
            ):
                raise ValueError(
                    "O line_index da localização não "
                    "corresponde à linha numérica."
                )