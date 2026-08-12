import re
from datetime import datetime, timedelta, timezone
from typing import Any


BRASILIA_TIMEZONE = timezone(
    timedelta(hours=-3),
    name="Horário de Brasília",
)


class AnalysisViewBuilder:

    def build(
        self,
        analysis_data: dict[str, Any],
    ) -> dict[str, Any]:
        pdf_info = analysis_data[
            "pdf_info"
        ]

        native_text = analysis_data[
            "native_text"
        ]

        ocr = analysis_data[
            "ocr"
        ]

        normalized_document = (
            analysis_data.get(
                "normalized_document"
            )
        )

        image_fingerprints = (
            analysis_data.get(
                "image_fingerprints",
                [],
            )
        )

        images = analysis_data[
            "images"
        ]

        barcodes = analysis_data[
            "barcodes"
        ]

        printed_numeric_lines = (
            analysis_data[
                "printed_numeric_lines"
            ]
        )

        numeric_line_validations = (
            analysis_data[
                "numeric_line_validations"
            ]
        )

        barcode_line_comparisons = (
            analysis_data[
                "barcode_line_comparisons"
            ]
        )

        numeric_line_locations = (
            analysis_data[
                "numeric_line_locations"
            ]
        )

        evidences = analysis_data[
            "evidences"
        ]

        prompt_injection_assessment = (
            analysis_data.get(
                "prompt_injection_assessment"
            )
        )

        formatted_evidences = [
            {
                "code": evidence.code,
                "title": evidence.title,
                "description": (
                    evidence.description
                ),
                "severity": (
                    evidence.severity.value
                ),
                "detector": (
                    evidence.detector
                ),
                "confidence": (
                    evidence.confidence
                ),
            }
            for evidence in evidences
        ]

        formatted_prompt_injection_evidences = (
            self._build_prompt_injection_evidences(
                prompt_injection_assessment
            )
        )

        formatted_numeric_line_validations = [
            {
                "line_index": (
                    validation.line_index
                ),
                "normalized_content": (
                    validation
                    .normalized_content
                ),
                "line_type": (
                    validation
                    .line_type
                    .value
                ),
                "line_type_label": (
                    self
                    ._translate_numeric_line_type(
                        validation
                        .line_type
                        .value
                    )
                ),
                "status": (
                    validation
                    .status
                    .value
                ),
                "status_label": (
                    self
                    ._translate_validation_status(
                        validation
                        .status
                        .value
                    )
                ),
                "validation_method": (
                    validation
                    .validation_method
                ),
                "validation_method_label": (
                    self
                    ._translate_validation_method(
                        validation
                        .validation_method
                    )
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
            }
            for validation
            in numeric_line_validations
        ]

        formatted_barcode_line_comparisons = [
            {
                "line_index": (
                    comparison.line_index
                ),
                "barcode_index": (
                    comparison.barcode_index
                ),
                "line_type": (
                    comparison.line_type
                ),
                "line_type_label": (
                    self
                    ._translate_numeric_line_type(
                        comparison.line_type
                    )
                ),
                "printed_numeric_line": (
                    comparison
                    .printed_numeric_line
                ),
                "converted_barcode": (
                    comparison
                    .converted_barcode
                ),
                "detected_barcode": (
                    comparison
                    .detected_barcode
                ),
                "status": (
                    comparison
                    .status
                    .value
                ),
                "status_label": (
                    self
                    ._translate_comparison_status(
                        comparison
                        .status
                        .value
                    )
                ),
                "message": (
                    comparison.message
                ),
            }
            for comparison
            in barcode_line_comparisons
        ]

        barcode_formats = sorted(
            {
                barcode.format
                for barcode
                in barcodes
                if barcode.format
            }
        )

        barcode_pages = sorted(
            {
                barcode.page_number
                for barcode
                in barcodes
            }
        )

        numeric_line_sources = sorted(
            {
                line.source
                for line
                in printed_numeric_lines
            }
        )

        formatted_normalized_pages = (
            self._build_normalized_pages(
                normalized_document
            )
        )

        formatted_image_fingerprints = (
            self._build_image_fingerprints(
                image_fingerprints
            )
        )

        formatted_numeric_line_locations = [
            {
                "line_index": (
                    location.line_index
                ),
                "page_number": (
                    location.page_number
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
                "confidence_label": (
                    self._format_confidence(
                        location.confidence
                    )
                ),
                "source_image_url": (
                    self
                    ._build_extracted_file_url(
                        location
                        .source_image_path
                    )
                ),
                "annotated_image_url": (
                    self
                    ._build_extracted_file_url(
                        location
                        .annotated_image_path
                    )
                ),
                "located": (
                    location.located
                ),
                "message": (
                    location.message
                ),
            }
            for location
            in numeric_line_locations
        ]

        prompt_injection_categories = (
            self
            ._prompt_injection_metadata_list(
                prompt_injection_assessment,
                "categories",
            )
        )

        prompt_injection_languages = (
            self
            ._prompt_injection_languages(
                prompt_injection_assessment
            )
        )

        prompt_injection_detectors = (
            self
            ._prompt_injection_detectors(
                prompt_injection_assessment
            )
        )

        prompt_injection_strong_categories = (
            self
            ._prompt_injection_metadata_list(
                prompt_injection_assessment,
                "strong_categories",
            )
        )

        return {
            "id": (
                analysis_data[
                    "id"
                ]
            ),

            "filename": (
                analysis_data[
                    "original_filename"
                ]
            ),

            "uploaded_at": (
                self._format_datetime(
                    analysis_data[
                        "uploaded_at"
                    ]
                )
            ),

            "size_bytes": (
                analysis_data[
                    "size_bytes"
                ]
            ),

            "formatted_size": (
                self._format_file_size(
                    analysis_data[
                        "size_bytes"
                    ]
                )
            ),

            "sha256": (
                analysis_data[
                    "sha256"
                ]
            ),

            # Informações estruturais do PDF
            "page_count": (
                pdf_info.page_count
            ),

            "pdf_title": (
                pdf_info.title
                or "Não informado"
            ),

            "pdf_author": (
                pdf_info.author
                or "Não informado"
            ),

            "pdf_creator": (
                pdf_info.creator
                or "Não informado"
            ),

            "pdf_producer": (
                pdf_info.producer
                or "Não informado"
            ),

            "pdf_creation_date": (
                self._format_pdf_datetime(
                    pdf_info.creation_date
                )
            ),

            "pdf_modification_date": (
                self._format_pdf_datetime(
                    pdf_info
                    .modification_date
                )
            ),

            "pdf_creation_date_raw": (
                pdf_info.creation_date
                or "Não informada"
            ),

            "pdf_modification_date_raw": (
                pdf_info.modification_date
                or "Não informada"
            ),

            "pdf_version": (
                pdf_info.pdf_version
                or "Não identificada"
            ),

            "has_native_text": (
                pdf_info.has_text
            ),

            "has_images": (
                pdf_info.has_images
            ),

            # Texto nativo
            "native_text_message": (
                self
                ._build_native_text_message(
                    native_text
                    .pages_with_text
                )
            ),

            "native_text_content": (
                native_text.content
            ),

            "native_text_character_count": (
                native_text
                .character_count
            ),

            "native_text_pages": (
                native_text
                .pages_with_text
            ),

            # OCR
            "ocr_message": (
                self._build_ocr_message(
                    ocr.pages_processed,
                    ocr.pages_with_text,
                )
            ),

            "ocr_content": (
                ocr.content
            ),

            "ocr_character_count": (
                ocr.character_count
            ),

            "ocr_pages_processed": (
                ocr.pages_processed
            ),

            "ocr_pages_with_text": (
                ocr.pages_with_text
            ),

            "ocr_language": (
                ocr.language
            ),

            # Documento normalizado
            "has_normalized_document": (
                normalized_document
                is not None
            ),

            "normalized_document_page_count": (
                normalized_document
                .page_count
                if normalized_document
                else 0
            ),

            "normalized_document_text_span_count": (
                normalized_document
                .text_span_count
                if normalized_document
                else 0
            ),

            "normalized_document_word_count": (
                normalized_document
                .word_count
                if normalized_document
                else 0
            ),

            "normalized_document_character_count": (
                normalized_document
                .character_count
                if normalized_document
                else 0
            ),

            "normalized_document_normalized_character_count": (
                normalized_document
                .normalized_character_count
                if normalized_document
                else 0
            ),

            "normalized_document_pages_with_text": (
                len(
                    normalized_document
                    .pages_with_visible_text()
                )
                if normalized_document
                else 0
            ),

            "normalized_document_text": (
                normalized_document
                .normalized_text
                if normalized_document
                else ""
            ),

            "normalized_pages": (
                formatted_normalized_pages
            ),

            # Imagens
            "images": (
                images
            ),

            "image_count": (
                len(images)
            ),

            "image_message": (
                self._build_image_message(
                    len(images)
                )
            ),

            "image_fingerprints": (
                formatted_image_fingerprints
            ),

            "image_fingerprint_count": (
                len(
                    formatted_image_fingerprints
                )
            ),

            "image_fingerprint_message": (
                self
                ._build_image_fingerprint_message(
                    len(
                        formatted_image_fingerprints
                    )
                )
            ),

            # Códigos
            "barcodes": (
                barcodes
            ),

            "barcode_count": (
                len(barcodes)
            ),

            "barcode_message": (
                self._build_barcode_message(
                    len(barcodes)
                )
            ),

            "barcode_formats": (
                ", ".join(
                    barcode_formats
                )
                if barcode_formats
                else "Nenhum"
            ),

            "barcode_pages": (
                ", ".join(
                    str(page)
                    for page
                    in barcode_pages
                )
                if barcode_pages
                else "Nenhuma"
            ),

            # Sequências numéricas
            "printed_numeric_lines": (
                printed_numeric_lines
            ),

            "printed_numeric_line_count": (
                len(
                    printed_numeric_lines
                )
            ),

            "printed_numeric_line_message": (
                self
                ._build_printed_numeric_line_message(
                    len(
                        printed_numeric_lines
                    )
                )
            ),

            "printed_numeric_line_sources": (
                ", ".join(
                    self._translate_source(
                        source
                    )
                    for source
                    in numeric_line_sources
                )
                if numeric_line_sources
                else "Nenhuma"
            ),

            "printed_numeric_digit_total": (
                sum(
                    line.digit_count
                    for line
                    in printed_numeric_lines
                )
            ),

            # Validação estrutural
            "numeric_line_validations": (
                formatted_numeric_line_validations
            ),

            "valid_numeric_line_count": (
                sum(
                    validation
                    .status
                    .value
                    == "valid"
                    for validation
                    in numeric_line_validations
                )
            ),

            "invalid_numeric_line_count": (
                sum(
                    validation
                    .status
                    .value
                    == "invalid"
                    for validation
                    in numeric_line_validations
                )
            ),

            "inconclusive_numeric_line_count": (
                sum(
                    validation
                    .status
                    .value
                    == "inconclusive"
                    for validation
                    in numeric_line_validations
                )
            ),

            # Comparação entre linha digitável
            # e código de barras
            "barcode_line_comparisons": (
                formatted_barcode_line_comparisons
            ),

            "barcode_line_match_count": (
                sum(
                    comparison
                    .status
                    .value
                    == "match"
                    for comparison
                    in barcode_line_comparisons
                )
            ),

            "barcode_line_mismatch_count": (
                sum(
                    comparison
                    .status
                    .value
                    == "mismatch"
                    for comparison
                    in barcode_line_comparisons
                )
            ),

            "barcode_line_inconclusive_count": (
                sum(
                    comparison
                    .status
                    .value
                    == "inconclusive"
                    for comparison
                    in barcode_line_comparisons
                )
            ),

            # Localização visual
            # das sequências
            "numeric_line_locations": (
                formatted_numeric_line_locations
            ),

            "located_numeric_line_count": (
                sum(
                    location.located
                    for location
                    in numeric_line_locations
                )
            ),

            "unlocated_numeric_line_count": (
                sum(
                    not location.located
                    for location
                    in numeric_line_locations
                )
            ),

            # IA e segurança
            # Prompt Injection
            "has_prompt_injection_assessment": (
                prompt_injection_assessment
                is not None
            ),

            "prompt_injection_score": (
                prompt_injection_assessment
                .score
                if prompt_injection_assessment
                is not None
                else 0.0
            ),

            "prompt_injection_score_label": (
                self
                ._format_ratio_as_percentage(
                    prompt_injection_assessment
                    .score
                )
                if prompt_injection_assessment
                is not None
                else "0.0%"
            ),

            "prompt_injection_risk_level": (
                prompt_injection_assessment
                .risk_level
                .value
                if prompt_injection_assessment
                is not None
                else "none"
            ),

            "prompt_injection_risk_label": (
                self
                ._translate_prompt_injection_risk_level(
                    prompt_injection_assessment
                    .risk_level
                    .value
                )
                if prompt_injection_assessment
                is not None
                else "Nenhum"
            ),

            "prompt_injection_summary": (
                prompt_injection_assessment
                .summary
                if (
                    prompt_injection_assessment
                    is not None
                    and prompt_injection_assessment
                    .summary
                )
                else (
                    "O verificador textual de "
                    "Prompt Injection não produziu "
                    "uma avaliação disponível."
                )
            ),

            "prompt_injection_evidences": (
                formatted_prompt_injection_evidences
            ),

            "prompt_injection_evidence_count": (
                prompt_injection_assessment
                .evidence_count
                if prompt_injection_assessment
                is not None
                else 0
            ),

            "prompt_injection_has_evidences": (
                prompt_injection_assessment
                .has_evidences
                if prompt_injection_assessment
                is not None
                else False
            ),

            "prompt_injection_categories": (
                prompt_injection_categories
            ),

            "prompt_injection_category_labels": (
                [
                    self
                    ._translate_prompt_injection_category(
                        category
                    )
                    for category
                    in prompt_injection_categories
                ]
            ),

            "prompt_injection_category_count": (
                len(
                    prompt_injection_categories
                )
            ),

            "prompt_injection_languages": (
                prompt_injection_languages
            ),

            "prompt_injection_language_count": (
                len(
                    prompt_injection_languages
                )
            ),

            "prompt_injection_detectors": (
                prompt_injection_detectors
            ),

            "prompt_injection_detector_count": (
                len(
                    prompt_injection_detectors
                )
            ),

            "prompt_injection_strong_categories": (
                prompt_injection_strong_categories
            ),

            "prompt_injection_strong_category_labels": (
                [
                    self
                    ._translate_prompt_injection_category(
                        category
                    )
                    for category
                    in (
                        prompt_injection_strong_categories
                    )
                ]
            ),

            "prompt_injection_strong_category_count": (
                len(
                    prompt_injection_strong_categories
                )
            ),

            # Evidências
            "evidences": (
                formatted_evidences
            ),

            "evidence_count": (
                len(
                    formatted_evidences
                )
            ),
        }

    def _format_datetime(
        self,
        value: datetime,
    ) -> str:
        return value.strftime(
            "%d/%m/%Y às %H:%M:%S"
        )

    def _format_file_size(
        self,
        size_bytes: int,
    ) -> str:
        if size_bytes < 1024:
            return (
                f"{size_bytes} bytes"
            )

        size_kb = (
            size_bytes
            / 1024
        )

        if size_kb < 1024:
            return (
                f"{size_kb:.2f} KB"
            )

        size_mb = (
            size_kb
            / 1024
        )

        return (
            f"{size_mb:.2f} MB"
        )

    def _translate_source(
            self,
            source: str,
    ) -> str:
        labels = {
            "ocr": (
                "OCR"
            ),
            "native_text": (
                "Texto nativo"
            ),
            "normalized_document": (
                "Documento normalizado"
            ),
            "normalized_document_visual": (
                "Análise tipográfica"
            ),
        }

        return labels.get(
            source,
            source,
        )

    def _build_native_text_message(
        self,
        pages_with_text: int,
    ) -> str:
        if pages_with_text == 0:
            return (
                "Não foi encontrada camada "
                "de texto nativo."
            )

        if pages_with_text == 1:
            return (
                "Foi encontrada camada de "
                "texto nativo em 1 página."
            )

        return (
            "Foi encontrada camada de texto "
            f"nativo em {pages_with_text} páginas."
        )

    def _build_ocr_message(
        self,
        pages_processed: int,
        pages_with_text: int,
    ) -> str:
        if pages_with_text == 0:
            return (
                f"O OCR processou "
                f"{pages_processed} página(s), "
                "mas não identificou "
                "texto legível."
            )

        return (
            f"O OCR processou "
            f"{pages_processed} página(s) "
            f"e encontrou texto em "
            f"{pages_with_text} página(s)."
        )

    def _build_image_message(
        self,
        image_count: int,
    ) -> str:
        if image_count == 0:
            return (
                "Nenhuma imagem interna "
                "foi extraída."
            )

        if image_count == 1:
            return (
                "Foi extraída 1 "
                "imagem interna."
            )

        return (
            f"Foram extraídas "
            f"{image_count} imagens internas."
        )

    def _build_barcode_message(
        self,
        barcode_count: int,
    ) -> str:
        if barcode_count == 0:
            return (
                "Nenhum código foi "
                "lido automaticamente."
            )

        if barcode_count == 1:
            return (
                "Foi encontrado 1 "
                "código no documento."
            )

        return (
            f"Foram encontrados "
            f"{barcode_count} códigos "
            "no documento."
        )

    def _build_printed_numeric_line_message(
        self,
        line_count: int,
    ) -> str:
        if line_count == 0:
            return (
                "Nenhuma sequência numérica "
                "compatível com uma possível "
                "linha digitável foi localizada."
            )

        if line_count == 1:
            return (
                "Foi localizada 1 sequência "
                "numérica que pode corresponder "
                "à linha digitável. O resultado "
                "da validação estrutural está "
                "disponível abaixo."
            )

        return (
            f"Foram localizadas "
            f"{line_count} sequências numéricas "
            "que podem corresponder a linhas "
            "digitáveis. Os resultados das "
            "validações estruturais estão "
            "disponíveis abaixo."
        )

    def _translate_numeric_line_type(
        self,
        line_type: str,
    ) -> str:
        labels = {
            "bank_slip": (
                "Boleto bancário"
            ),
            "collection": (
                "Arrecadação ou concessionária"
            ),
            "unknown": (
                "Formato não reconhecido"
            ),
        }

        return labels.get(
            line_type,
            line_type,
        )

    def _translate_validation_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "valid": "Válida",
            "invalid": "Inválida",
            "inconclusive": (
                "Inconclusiva"
            ),
        }

        return labels.get(
            status,
            status,
        )

    def _translate_comparison_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "match": (
                "Correspondência confirmada"
            ),
            "mismatch": (
                "Divergência identificada"
            ),
            "inconclusive": (
                "Comparação inconclusiva"
            ),
        }

        return labels.get(
            status,
            status,
        )

    def _translate_validation_method(
        self,
        validation_method: str | None,
    ) -> str:
        labels = {
            "modulo_10": (
                "Módulo 10"
            ),
            "modulo_11_collection": (
                "Módulo 11"
            ),
            None: (
                "Não aplicável"
            ),
        }

        return labels.get(
            validation_method,
            str(
                validation_method
            ),
        )

    def _format_pdf_datetime(
        self,
        value: str | None,
    ) -> str:
        if not value:
            return "Não informada"

        pattern = re.compile(
            r"^D:"
            r"(?P<year>\d{4})"
            r"(?P<month>\d{2})?"
            r"(?P<day>\d{2})?"
            r"(?P<hour>\d{2})?"
            r"(?P<minute>\d{2})?"
            r"(?P<second>\d{2})?"
            r"(?P<offset_sign>[+\-Z])?"
            r"(?P<offset_hour>\d{2})?"
            r"'?"
            r"(?P<offset_minute>\d{2})?"
            r"'?"
            r"$"
        )

        match = pattern.match(
            value.strip()
        )

        if not match:
            return value

        values = (
            match.groupdict()
        )

        try:
            year = int(
                values[
                    "year"
                ]
            )

            month = int(
                values[
                    "month"
                ]
                or 1
            )

            day = int(
                values[
                    "day"
                ]
                or 1
            )

            hour = int(
                values[
                    "hour"
                ]
                or 0
            )

            minute = int(
                values[
                    "minute"
                ]
                or 0
            )

            second = int(
                values[
                    "second"
                ]
                or 0
            )

            source_timezone = (
                self._build_pdf_timezone(
                    sign=(
                        values[
                            "offset_sign"
                        ]
                    ),
                    hour=(
                        values[
                            "offset_hour"
                        ]
                    ),
                    minute=(
                        values[
                            "offset_minute"
                        ]
                    ),
                )
            )

            pdf_datetime = datetime(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                second=second,
                tzinfo=(
                    source_timezone
                ),
            )

            brasilia_datetime = (
                pdf_datetime.astimezone(
                    BRASILIA_TIMEZONE
                )
            )

            formatted_datetime = (
                brasilia_datetime.strftime(
                    "%d/%m/%Y às %H:%M:%S"
                )
            )

            return (
                f"{formatted_datetime} — "
                "horário de Brasília "
                "(UTC−3)"
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return value

    def _build_pdf_timezone(
        self,
        sign: str | None,
        hour: str | None,
        minute: str | None,
    ) -> timezone:
        if sign == "Z":
            return timezone.utc

        if sign in {
            "+",
            "-",
        }:
            offset_hours = int(
                hour
                or 0
            )

            offset_minutes = int(
                minute
                or 0
            )

            offset = timedelta(
                hours=offset_hours,
                minutes=offset_minutes,
            )

            if sign == "-":
                offset = (
                    -offset
                )

            return timezone(
                offset
            )

        return (
            BRASILIA_TIMEZONE
        )

    def _format_confidence(
        self,
        confidence: float | None,
    ) -> str:
        if confidence is None:
            return (
                "Não informada"
            )

        return (
            f"{confidence:.1f}%"
        )

    def _build_normalized_pages(
        self,
        document: Any,
    ) -> list[
        dict[str, Any]
    ]:
        if document is None:
            return []

        result = []

        for page in document.pages:
            box = (
                page.text_bounding_box
            )

            result.append(
                {
                    "number": (
                        page.number
                    ),

                    "width": (
                        self._format_decimal(
                            page.width
                        )
                    ),

                    "height": (
                        self._format_decimal(
                            page.height
                        )
                    ),

                    "area": (
                        self._format_decimal(
                            page.area
                        )
                    ),

                    "aspect_ratio": (
                        self._format_decimal(
                            page.aspect_ratio,
                            decimals=3,
                        )
                    ),

                    "text_span_count": (
                        page.text_span_count
                    ),

                    "word_count": (
                        page.word_count
                    ),

                    "character_count": (
                        page.character_count
                    ),

                    "has_visible_text": (
                        page.has_visible_text
                    ),

                    "text_bounding_box": (
                        None
                        if box is None
                        else {
                            "left": (
                                self
                                ._format_decimal(
                                    box.left
                                )
                            ),

                            "top": (
                                self
                                ._format_decimal(
                                    box.top
                                )
                            ),

                            "width": (
                                self
                                ._format_decimal(
                                    box.width
                                )
                            ),

                            "height": (
                                self
                                ._format_decimal(
                                    box.height
                                )
                            ),
                        }
                    ),

                    "sample_spans": [
                        {
                            "normalized_text": (
                                span
                                .normalized_text
                            ),

                            "font_name": (
                                span
                                .font
                                .name
                            ),

                            "font_size": (
                                self
                                ._format_decimal(
                                    span
                                    .font
                                    .size
                                )
                            ),

                            "left": (
                                self
                                ._format_decimal(
                                    span
                                    .bounding_box
                                    .left
                                )
                            ),

                            "top": (
                                self
                                ._format_decimal(
                                    span
                                    .bounding_box
                                    .top
                                )
                            ),

                            "width": (
                                self
                                ._format_decimal(
                                    span
                                    .bounding_box
                                    .width
                                )
                            ),

                            "height": (
                                self
                                ._format_decimal(
                                    span
                                    .bounding_box
                                    .height
                                )
                            ),
                        }
                        for span
                        in page.text_spans[
                            :8
                        ]
                    ],
                }
            )

        return result

    def _build_image_fingerprints(
        self,
        fingerprints: list[Any],
    ) -> list[
        dict[str, Any]
    ]:
        result = []

        for (
            index,
            fingerprint,
        ) in enumerate(
            fingerprints,
            start=1,
        ):
            location = getattr(
                fingerprint,
                "location",
                None,
            )

            box = getattr(
                location,
                "bounding_box",
                None,
            )

            confidence = getattr(
                fingerprint,
                "confidence",
                None,
            )

            confidence_value = getattr(
                confidence,
                "value",
                confidence,
            )

            result.append(
                {
                    "index": (
                        index
                    ),

                    "page_number": (
                        getattr(
                            location,
                            "page_number",
                            None,
                        )
                    ),

                    "width": (
                        getattr(
                            fingerprint,
                            "width",
                            None,
                        )
                    ),

                    "height": (
                        getattr(
                            fingerprint,
                            "height",
                            None,
                        )
                    ),

                    "mime_type": (
                        getattr(
                            fingerprint,
                            "mime_type",
                            None,
                        )
                        or (
                            "Não identificado"
                        )
                    ),

                    "dpi": (
                        getattr(
                            fingerprint,
                            "dpi",
                            None,
                        )
                    ),

                    "description": (
                        getattr(
                            fingerprint,
                            "description",
                            None,
                        )
                        or (
                            "Sem descrição técnica."
                        )
                    ),

                    "confidence": (
                        self
                        ._format_ratio_as_percentage(
                            confidence_value
                        )
                    ),

                    "image_hash": (
                        getattr(
                            fingerprint,
                            "image_hash",
                            None,
                        )
                    ),

                    "perceptual_hash": (
                        getattr(
                            fingerprint,
                            "perceptual_hash",
                            None,
                        )
                    ),

                    "average_hash": (
                        getattr(
                            fingerprint,
                            "average_hash",
                            None,
                        )
                    ),

                    "difference_hash": (
                        getattr(
                            fingerprint,
                            "difference_hash",
                            None,
                        )
                    ),

                    "location": (
                        None
                        if box is None
                        else {
                            "x": (
                                self
                                ._format_decimal(
                                    getattr(
                                        box,
                                        "x",
                                        0.0,
                                    )
                                )
                            ),

                            "y": (
                                self
                                ._format_decimal(
                                    getattr(
                                        box,
                                        "y",
                                        0.0,
                                    )
                                )
                            ),

                            "width": (
                                self
                                ._format_decimal(
                                    getattr(
                                        box,
                                        "width",
                                        0.0,
                                    )
                                )
                            ),

                            "height": (
                                self
                                ._format_decimal(
                                    getattr(
                                        box,
                                        "height",
                                        0.0,
                                    )
                                )
                            ),
                        }
                    ),
                }
            )

        return result

    def _build_image_fingerprint_message(
        self,
        count: int,
    ) -> str:
        if count == 0:
            return (
                "Nenhum fingerprint "
                "de imagem foi produzido."
            )

        if count == 1:
            return (
                "Foi produzido 1 fingerprint "
                "técnico de imagem."
            )

        return (
            f"Foram produzidos {count} "
            "fingerprints técnicos de imagem."
        )

    def _build_prompt_injection_evidences(
        self,
        assessment: Any,
    ) -> list[
        dict[str, Any]
    ]:
        if assessment is None:
            return []

        result = []

        for evidence in (
            assessment.evidences
        ):
            metadata = getattr(
                evidence,
                "metadata",
                {},
            )

            result.append(
                {
                    "code": (
                        evidence.code
                    ),

                    "detector": (
                        evidence.detector
                    ),

                    "description": (
                        evidence.description
                    ),

                    "confidence": (
                        evidence.confidence
                    ),

                    "confidence_label": (
                        self
                        ._format_ratio_as_percentage(
                            evidence
                            .confidence
                        )
                    ),

                    "weight": (
                        evidence.weight
                    ),

                    "weight_label": (
                        self
                        ._format_ratio_as_percentage(
                            evidence.weight
                        )
                    ),

                    "weighted_score": (
                        evidence.weighted_score
                    ),

                    "weighted_score_label": (
                        self
                        ._format_ratio_as_percentage(
                            evidence
                            .weighted_score
                        )
                    ),

                    "page_number": (
                        evidence.page_number
                    ),

                    "original_excerpt": (
                        evidence
                        .original_excerpt
                    ),

                    "normalized_excerpt": (
                        evidence
                        .normalized_excerpt
                    ),

                    "language": (
                        evidence.language
                        or "Não identificado"
                    ),

                    "category": (
                        evidence.category
                        or "unknown"
                    ),

                    "category_label": (
                        self
                        ._translate_prompt_injection_category(
                            evidence.category
                        )
                    ),

                    "start_index": (
                        evidence.start_index
                    ),

                    "end_index": (
                        evidence.end_index
                    ),

                    "matched_rule": (
                        metadata.get(
                            "matched_rule"
                        )
                    ),

                    "source": (
                        metadata.get(
                            "source"
                        )
                    ),

                    "source_label": (
                        self._translate_source(
                            metadata.get(
                                "source",
                                "unknown",
                            )
                        )
                        if metadata.get(
                            "source"
                        )
                        else (
                            "Não informada"
                        )
                    ),

                    "font_size": (
                        metadata.get(
                            "font_size"
                        )
                    ),

                    "font_name": (
                        metadata.get(
                            "font_name"
                        )
                    ),

                    "font_color": (
                        metadata.get(
                            "font_color"
                        )
                    ),

                    "maximum_font_size": (
                        metadata.get(
                            "maximum_font_size"
                        )
                    ),

                    "analysis_method": (
                        metadata.get(
                            "analysis_method"
                        )
                    ),

                    "signal_groups": (
                        list(
                            metadata.get(
                                "signal_groups",
                                (),
                            )
                        )
                    ),

                    "matched_signals": (
                        metadata.get(
                            "matched_signals",
                            {},
                        )
                    ),
                }
            )

        return result

    def _prompt_injection_metadata_list(
        self,
        assessment: Any,
        key: str,
    ) -> list[str]:
        if assessment is None:
            return []

        metadata = getattr(
            assessment,
            "metadata",
            {},
        )

        values = metadata.get(
            key,
            (),
        )

        if not values:
            return []

        return [
            str(value)
            for value
            in values
        ]

    def _prompt_injection_languages(
        self,
        assessment: Any,
    ) -> list[str]:
        if assessment is None:
            return []

        languages = getattr(
            assessment,
            "languages_detected",
            (),
        )

        return [
            str(language)
            for language
            in languages
        ]

    def _prompt_injection_detectors(
        self,
        assessment: Any,
    ) -> list[str]:
        if assessment is None:
            return []

        detectors = getattr(
            assessment,
            "detectors",
            (),
        )

        return [
            str(detector)
            for detector
            in detectors
        ]

    def _translate_prompt_injection_risk_level(
        self,
        risk_level: str,
    ) -> str:
        labels = {
            "none": (
                "Nenhum"
            ),
            "low": (
                "Baixo"
            ),
            "medium": (
                "Médio"
            ),
            "high": (
                "Alto"
            ),
            "critical": (
                "Crítico"
            ),
        }

        return labels.get(
            risk_level,
            risk_level,
        )

    def _translate_prompt_injection_category(
            self,
            category: str | None,
    ) -> str:
        if category is None:
            return (
                "Não categorizada"
            )

        labels = {
            "instruction_override": (
                "Substituição de instruções"
            ),

            "ai_targeting": (
                "Direcionamento a IA"
            ),

            "role_manipulation": (
                "Manipulação de papel"
            ),

            "system_prompt_extraction": (
                "Tentativa de extração "
                "do prompt de sistema"
            ),

            "response_control": (
                "Controle da resposta"
            ),

            "tool_manipulation": (
                "Manipulação de ferramentas"
            ),

            "prompt_structure": (
                "Estrutura semelhante a prompt"
            ),

            "instruction_intent": (
                "Instrução direcionada a sistema de IA"
            ),

            "visual_concealment": (
                "Possível ocultação tipográfica"
            ),
        }

        return labels.get(
            category,
            category,
        )

    def _format_decimal(
        self,
        value: Any,
        *,
        decimals: int = 2,
    ) -> str:
        try:
            return (
                f"{float(value):.{decimals}f}"
            )

        except (
            TypeError,
            ValueError,
        ):
            return (
                "Não informado"
            )

    def _format_ratio_as_percentage(
        self,
        value: Any,
    ) -> str:
        try:
            number = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return (
                "Não informada"
            )

        if (
            0.0
            <= number
            <= 1.0
        ):
            number *= 100.0

        return (
            f"{number:.1f}%"
        )

    def _build_extracted_file_url(
        self,
        file_path: str | None,
    ) -> str | None:
        if not file_path:
            return None

        normalized_path = (
            file_path.replace(
                "\\",
                "/",
            )
        )

        marker = (
            "/extracted/"
        )

        if marker not in normalized_path:
            return None

        relative_path = (
            normalized_path.split(
                marker,
                maxsplit=1,
            )[1]
        )

        return (
            f"/extracted/"
            f"{relative_path}"
        )