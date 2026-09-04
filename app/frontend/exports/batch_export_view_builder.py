from __future__ import annotations

from typing import Any

from app.domain.models.batch import Batch
from app.domain.models.batch_finding_summary import (
    BatchFindingSummary,
)
from app.frontend.investigations.models.investigation_status import (
    InvestigationStatus,
)
from app.frontend.view_models.batch_view_builder import (
    BatchViewBuilder,
)


class BatchExportViewBuilder:
    """
    Prepara os dados consolidados de um lote para exportação.

    Este builder não cria arquivos Excel.

    Sua responsabilidade é produzir uma estrutura estável,
    independente do formato final de exportação.

    A mesma estrutura poderá futuramente alimentar:

    - XLSX;
    - HTML;
    - PDF;
    - CSV;
    - APIs de relatório.

    As regras de status analítico permanecem centralizadas
    no BatchViewBuilder e no InvestigationStatusResolver.

    As análises individuais já devem chegar previamente
    transformadas pelo AnalysisViewBuilder.
    """

    def __init__(self) -> None:
        self._batch_view_builder = (
            BatchViewBuilder()
        )

    def build(
        self,
        *,
        batch: Batch,
        finding_summaries: list[
            BatchFindingSummary
        ] | None = None,
        document_analytical_statuses: dict[
            str,
            InvestigationStatus,
        ] | None = None,
        analysis_views: list[
            dict[str, Any]
        ] | None = None,
    ) -> dict[str, Any]:
        normalized_analysis_views = (
            analysis_views or []
        )

        batch_view = (
            self._batch_view_builder.build(
                batch=batch,
                finding_summaries=(
                    finding_summaries
                ),
                document_analytical_statuses=(
                    document_analytical_statuses
                ),
            )
        )

        return {
            "summary": (
                self._build_summary(
                    batch_view
                )
            ),

            "documents": (
                self._build_documents(
                    batch_view
                )
            ),

            "findings_by_type": (
                self._build_findings_by_type(
                    batch_view
                )
            ),

            "financial": (
                self._build_financial(
                    normalized_analysis_views
                )
            ),

            "prompt_injection": (
                self._build_prompt_injection(
                    normalized_analysis_views
                )
            ),

            "concealment": (
                self._build_concealment(
                    normalized_analysis_views
                )
            ),

            "locations": (
                self._build_locations(
                    normalized_analysis_views
                )
            ),

            "technical_data": (
                self._build_technical_data(
                    normalized_analysis_views
                )
            ),

            "images": (
                self._build_images(
                    normalized_analysis_views
                )
            ),
        }

    def _build_summary(
        self,
        batch_view: dict[str, Any],
    ) -> dict[str, Any]:
        analytical_summary = (
            batch_view[
                "analytical_summary"
            ]
        )

        result = batch_view[
            "result"
        ]

        return {
            "batch_id": (
                batch_view["id"]
            ),

            "processing_status": (
                batch_view["status"]
            ),

            "processing_status_label": (
                batch_view[
                    "status_label"
                ]
            ),

            "analytical_status": (
                batch_view[
                    "analytical_status"
                ]
            ),

            "analytical_status_label": (
                batch_view[
                    "analytical_status_label"
                ]
            ),

            "created_at": (
                batch_view["created_at"]
            ),

            "started_at": (
                batch_view["started_at"]
            ),

            "finished_at": (
                batch_view["finished_at"]
            ),

            "total_documents": (
                result[
                    "total_documents"
                ]
            ),

            "completed_documents": (
                result[
                    "completed_documents"
                ]
            ),

            "failed_documents": (
                result[
                    "failed_documents"
                ]
            ),

            "pending_documents": (
                result[
                    "pending_documents"
                ]
            ),

            "processing_documents": (
                result[
                    "processing_documents"
                ]
            ),

            "progress_percentage": (
                result[
                    "progress_percentage"
                ]
            ),

            "progress_label": (
                result[
                    "progress_label"
                ]
            ),

            "alert_documents": (
                analytical_summary[
                    "alert_documents"
                ]
            ),

            "attention_documents": (
                analytical_summary[
                    "attention_documents"
                ]
            ),

            "clear_documents": (
                analytical_summary[
                    "clear_documents"
                ]
            ),

            "not_executed_documents": (
                analytical_summary[
                    "not_executed_documents"
                ]
            ),

            "classified_documents": (
                analytical_summary[
                    "classified_documents"
                ]
            ),

            "finding_type_count": (
                batch_view[
                    "individual_finding_type_count"
                ]
            ),

            "has_findings": (
                batch_view[
                    "has_individual_findings"
                ]
            ),
        }

    def _build_documents(
        self,
        batch_view: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            {
                "document_id": (
                    document[
                        "document_id"
                    ]
                ),

                "filename": (
                    document[
                        "original_filename"
                    ]
                ),

                "analysis_id": (
                    document[
                        "analysis_id"
                    ]
                ),

                "processing_status": (
                    document[
                        "status"
                    ]
                ),

                "processing_status_label": (
                    document[
                        "status_label"
                    ]
                ),

                "analytical_status": (
                    document[
                        "analytical_status"
                    ]
                ),

                "analytical_status_label": (
                    document[
                        "analytical_status_label"
                    ]
                ),

                "analysis_url": (
                    document[
                        "analysis_url"
                    ]
                ),

                "error_message": (
                    document[
                        "error_message"
                    ]
                ),
            }
            for document
            in batch_view[
                "documents"
            ]
        ]

    def _build_findings_by_type(
        self,
        batch_view: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            {
                "code": (
                    finding[
                        "code"
                    ]
                ),

                "title": (
                    finding[
                        "title"
                    ]
                ),

                "affected_documents": (
                    finding[
                        "affected_documents"
                    ]
                ),

                "total_documents": (
                    finding[
                        "total_documents"
                    ]
                ),

                "occurrence_count": (
                    finding[
                        "occurrence_count"
                    ]
                ),

                "prevalence_percentage": (
                    finding[
                        "prevalence_percentage"
                    ]
                ),

                "prevalence_ratio": (
                    finding[
                        "prevalence_percentage"
                    ]
                    / 100
                ),

                "prevalence_label": (
                    finding[
                        "prevalence_label"
                    ]
                ),

                "fraction_label": (
                    finding[
                        "fraction_label"
                    ]
                ),

                "highest_confidence": (
                    finding[
                        "highest_confidence"
                    ]
                ),

                "highest_confidence_label": (
                    finding[
                        "highest_confidence_label"
                    ]
                ),

                "affected_document_ids": (
                    list(
                        finding[
                            "affected_document_ids"
                        ]
                    )
                ),
            }
            for finding
            in batch_view[
                "individual_findings"
            ]
        ]

    def _build_financial(
        self,
        analysis_views: list[
            dict[str, Any]
        ],
    ) -> list[dict[str, Any]]:
        result: list[
            dict[str, Any]
        ] = []

        for analysis in analysis_views:
            analysis_id = self._string_value(
                analysis.get(
                    "id"
                )
            )

            filename = self._string_value(
                analysis.get(
                    "filename"
                )
            )

            validations = (
                analysis.get(
                    "numeric_line_validations",
                    [],
                )
                or []
            )

            for validation in validations:
                result.append(
                    {
                        "record_type": (
                            "validation"
                        ),

                        "record_type_label": (
                            "Validação estrutural"
                        ),

                        "analysis_id": (
                            analysis_id
                        ),

                        "filename": (
                            filename
                        ),

                        "line_index": (
                            validation.get(
                                "line_index"
                            )
                        ),

                        "barcode_index": None,

                        "numeric_line": (
                            validation.get(
                                "normalized_content"
                            )
                        ),

                        "line_type": (
                            validation.get(
                                "line_type"
                            )
                        ),

                        "line_type_label": (
                            validation.get(
                                "line_type_label"
                            )
                        ),

                        "status": (
                            validation.get(
                                "status"
                            )
                        ),

                        "status_label": (
                            validation.get(
                                "status_label"
                            )
                        ),

                        "validation_method": (
                            validation.get(
                                "validation_method"
                            )
                        ),

                        "validation_method_label": (
                            validation.get(
                                "validation_method_label"
                            )
                        ),

                        "valid_check_digits": (
                            validation.get(
                                "valid_check_digits"
                            )
                        ),

                        "total_check_digits": (
                            validation.get(
                                "total_check_digits"
                            )
                        ),

                        "converted_barcode": None,

                        "detected_barcode": None,

                        "message": (
                            validation.get(
                                "message"
                            )
                        ),
                    }
                )

            comparisons = (
                analysis.get(
                    "barcode_line_comparisons",
                    [],
                )
                or []
            )

            for comparison in comparisons:
                result.append(
                    {
                        "record_type": (
                            "comparison"
                        ),

                        "record_type_label": (
                            "Comparação linha × código"
                        ),

                        "analysis_id": (
                            analysis_id
                        ),

                        "filename": (
                            filename
                        ),

                        "line_index": (
                            comparison.get(
                                "line_index"
                            )
                        ),

                        "barcode_index": (
                            comparison.get(
                                "barcode_index"
                            )
                        ),

                        "numeric_line": (
                            comparison.get(
                                "printed_numeric_line"
                            )
                        ),

                        "line_type": (
                            comparison.get(
                                "line_type"
                            )
                        ),

                        "line_type_label": (
                            comparison.get(
                                "line_type_label"
                            )
                        ),

                        "status": (
                            comparison.get(
                                "status"
                            )
                        ),

                        "status_label": (
                            comparison.get(
                                "status_label"
                            )
                        ),

                        "validation_method": None,

                        "validation_method_label": None,

                        "valid_check_digits": None,

                        "total_check_digits": None,

                        "converted_barcode": (
                            comparison.get(
                                "converted_barcode"
                            )
                        ),

                        "detected_barcode": (
                            comparison.get(
                                "detected_barcode"
                            )
                        ),

                        "message": (
                            comparison.get(
                                "message"
                            )
                        ),
                    }
                )

        return result

    def _build_prompt_injection(
        self,
        analysis_views: list[
            dict[str, Any]
        ],
    ) -> list[dict[str, Any]]:
        result: list[
            dict[str, Any]
        ] = []

        for analysis in analysis_views:
            analysis_id = self._string_value(
                analysis.get(
                    "id"
                )
            )

            filename = self._string_value(
                analysis.get(
                    "filename"
                )
            )

            risk_level = (
                analysis.get(
                    "prompt_injection_risk_level"
                )
            )

            risk_label = (
                analysis.get(
                    "prompt_injection_risk_label"
                )
            )

            score = (
                analysis.get(
                    "prompt_injection_score",
                    0.0,
                )
            )

            score_label = (
                analysis.get(
                    "prompt_injection_score_label"
                )
            )

            evidences = (
                analysis.get(
                    "prompt_injection_evidences",
                    [],
                )
                or []
            )

            for evidence_index, evidence in enumerate(
                evidences,
                start=1,
            ):
                result.append(
                    {
                        "analysis_id": (
                            analysis_id
                        ),

                        "filename": (
                            filename
                        ),

                        "evidence_index": (
                            evidence_index
                        ),

                        "risk_level": (
                            risk_level
                        ),

                        "risk_label": (
                            risk_label
                        ),

                        "score": (
                            score
                        ),

                        "score_label": (
                            score_label
                        ),

                        "code": (
                            evidence.get(
                                "code"
                            )
                        ),

                        "detector": (
                            evidence.get(
                                "detector"
                            )
                        ),

                        "description": (
                            evidence.get(
                                "description"
                            )
                        ),

                        "confidence": (
                            evidence.get(
                                "confidence"
                            )
                        ),

                        "confidence_label": (
                            evidence.get(
                                "confidence_label"
                            )
                        ),

                        "weight": (
                            evidence.get(
                                "weight"
                            )
                        ),

                        "weight_label": (
                            evidence.get(
                                "weight_label"
                            )
                        ),

                        "weighted_score": (
                            evidence.get(
                                "weighted_score"
                            )
                        ),

                        "weighted_score_label": (
                            evidence.get(
                                "weighted_score_label"
                            )
                        ),

                        "page_number": (
                            evidence.get(
                                "page_number"
                            )
                        ),

                        "original_excerpt": (
                            evidence.get(
                                "original_excerpt"
                            )
                        ),

                        "normalized_excerpt": (
                            evidence.get(
                                "normalized_excerpt"
                            )
                        ),

                        "language": (
                            evidence.get(
                                "language"
                            )
                        ),

                        "category": (
                            evidence.get(
                                "category"
                            )
                        ),

                        "category_label": (
                            evidence.get(
                                "category_label"
                            )
                        ),

                        "start_index": (
                            evidence.get(
                                "start_index"
                            )
                        ),

                        "end_index": (
                            evidence.get(
                                "end_index"
                            )
                        ),

                        "matched_rule": (
                            evidence.get(
                                "matched_rule"
                            )
                        ),

                        "source": (
                            evidence.get(
                                "source"
                            )
                        ),

                        "source_label": (
                            evidence.get(
                                "source_label"
                            )
                        ),

                        "font_name": (
                            evidence.get(
                                "font_name"
                            )
                        ),

                        "font_size": (
                            evidence.get(
                                "font_size"
                            )
                        ),

                        "font_color": (
                            evidence.get(
                                "font_color"
                            )
                        ),

                        "maximum_font_size": (
                            evidence.get(
                                "maximum_font_size"
                            )
                        ),

                        "analysis_method": (
                            evidence.get(
                                "analysis_method"
                            )
                        ),

                        "signal_groups": (
                            list(
                                evidence.get(
                                    "signal_groups",
                                    [],
                                )
                                or []
                            )
                        ),

                        "matched_signals": (
                            evidence.get(
                                "matched_signals",
                                {},
                            )
                            or {}
                        ),
                    }
                )

        return result

    def _build_concealment(
        self,
        analysis_views: list[
            dict[str, Any]
        ],
    ) -> list[dict[str, Any]]:
        result: list[
            dict[str, Any]
        ] = []

        for analysis in analysis_views:
            analysis_id = self._string_value(
                analysis.get(
                    "id"
                )
            )

            filename = self._string_value(
                analysis.get(
                    "filename"
                )
            )

            white_findings = (
                analysis.get(
                    "visual_concealment_white_text_findings",
                    [],
                )
                or []
            )

            low_contrast_findings = (
                analysis.get(
                    "visual_concealment_low_contrast_text_findings",
                    [],
                )
                or []
            )

            for finding_index, finding in enumerate(
                white_findings,
                start=1,
            ):
                visual_location = (
                    finding.get(
                        "visual_location"
                    )
                    or {}
                )

                result.append(
                    {
                        "analysis_id": analysis_id,
                        "filename": filename,
                        "finding_index": finding_index,
                        "concealment_type": "white_text",
                        "concealment_type_label": (
                            "Texto branco ou quase branco"
                        ),
                        "code": finding.get("code"),
                        "detector": finding.get("detector"),
                        "page_number": finding.get(
                            "page_number"
                        ),
                        "text": finding.get("text"),
                        "description": None,
                        "font_name": finding.get(
                            "font_name"
                        ),
                        "font_size": finding.get(
                            "font_size"
                        ),
                        "font_color_hex": finding.get(
                            "font_color_hex"
                        ),
                        "background_color_hex": (
                            finding.get(
                                "background_color_hex"
                            )
                        ),
                        "font_relative_luminance": (
                            finding.get(
                                "font_relative_luminance"
                            )
                        ),
                        "background_relative_luminance": (
                            finding.get(
                                "background_relative_luminance"
                            )
                        ),
                        "contrast_ratio": finding.get(
                            "contrast_ratio"
                        ),
                        "contrast_threshold": finding.get(
                            "contrast_threshold"
                        ),
                        "contrast_level": finding.get(
                            "contrast_level"
                        ),
                        "contrast_level_label": (
                            finding.get(
                                "contrast_level_label"
                            )
                        ),
                        "background_dominance_ratio": (
                            finding.get(
                                "background_dominance_ratio"
                            )
                        ),
                        "background_sampling_method": (
                            finding.get(
                                "background_sampling_method"
                            )
                        ),
                        "background_sampling_method_label": (
                            finding.get(
                                "background_sampling_method_label"
                            )
                        ),
                        "contrast_reference": (
                            finding.get(
                                "contrast_reference"
                            )
                        ),
                        "confidence": finding.get(
                            "confidence"
                        ),
                        "confidence_label": finding.get(
                            "confidence_label"
                        ),
                        "signals": list(
                            finding.get(
                                "signals",
                                [],
                            )
                            or []
                        ),
                        "signal_labels": list(
                            finding.get(
                                "signal_labels",
                                [],
                            )
                            or []
                        ),
                        "is_near_white": bool(
                            finding.get(
                                "is_near_white",
                                False,
                            )
                        ),
                        "is_low_contrast": bool(
                            finding.get(
                                "is_low_contrast",
                                False,
                            )
                        ),
                        "is_extreme_low_contrast": bool(
                            finding.get(
                                "is_extreme_low_contrast",
                                False,
                            )
                        ),
                        "is_small_text": bool(
                            finding.get(
                                "is_small_text",
                                False,
                            )
                        ),
                        "is_relative_small_text": bool(
                            finding.get(
                                "is_relative_small_text",
                                False,
                            )
                        ),
                        "is_instruction_like": bool(
                            finding.get(
                                "is_instruction_like",
                                False,
                            )
                        ),
                        "coordinates_label": finding.get(
                            "coordinates_label"
                        ),
                        "located": bool(
                            visual_location.get(
                                "located",
                                False,
                            )
                        ),
                        "location_message": (
                            visual_location.get(
                                "message"
                            )
                        ),
                        "source_image_url": (
                            visual_location.get(
                                "source_image_url"
                            )
                        ),
                        "annotated_image_url": (
                            visual_location.get(
                                "annotated_image_url"
                            )
                        ),
                    }
                )

            low_contrast_start_index = (
                len(white_findings)
                + 1
            )

            for finding_index, finding in enumerate(
                low_contrast_findings,
                start=low_contrast_start_index,
            ):
                visual_location = (
                    finding.get(
                        "visual_location"
                    )
                    or {}
                )

                result.append(
                    {
                        "analysis_id": analysis_id,
                        "filename": filename,
                        "finding_index": finding_index,
                        "concealment_type": (
                            "low_contrast_text"
                        ),
                        "concealment_type_label": (
                            "Texto com baixo contraste"
                        ),
                        "code": finding.get("code"),
                        "detector": finding.get(
                            "detector"
                        ),
                        "page_number": finding.get(
                            "page_number"
                        ),
                        "text": finding.get("text"),
                        "description": (
                            "Contraste reduzido entre "
                            "a cor do texto e o fundo "
                            "estimado da região."
                        ),
                        "font_name": finding.get(
                            "font_name"
                        ),
                        "font_size": finding.get(
                            "font_size"
                        ),
                        "font_color_hex": finding.get(
                            "font_color_hex"
                        ),
                        "background_color_hex": (
                            finding.get(
                                "background_color_hex"
                            )
                        ),
                        "font_relative_luminance": (
                            finding.get(
                                "font_relative_luminance"
                            )
                        ),
                        "background_relative_luminance": (
                            finding.get(
                                "background_relative_luminance"
                            )
                        ),
                        "contrast_ratio": finding.get(
                            "contrast_ratio"
                        ),
                        "contrast_threshold": (
                            finding.get(
                                "contrast_threshold"
                            )
                        ),
                        "contrast_level": finding.get(
                            "contrast_level"
                        ),
                        "contrast_level_label": (
                            finding.get(
                                "contrast_level_label"
                            )
                        ),
                        "background_dominance_ratio": (
                            finding.get(
                                "background_dominance_ratio"
                            )
                        ),
                        "background_sampling_method": (
                            finding.get(
                                "background_sampling_method"
                            )
                        ),
                        "background_sampling_method_label": (
                            finding.get(
                                "background_sampling_method_label"
                            )
                        ),
                        "contrast_reference": (
                            finding.get(
                                "contrast_reference"
                            )
                        ),
                        "confidence": finding.get(
                            "confidence"
                        ),
                        "confidence_label": (
                            finding.get(
                                "confidence_label"
                            )
                        ),
                        "signals": list(
                            finding.get(
                                "signals",
                                [],
                            )
                            or []
                        ),
                        "signal_labels": list(
                            finding.get(
                                "signal_labels",
                                [],
                            )
                            or []
                        ),
                        "is_near_white": bool(
                            finding.get(
                                "is_near_white",
                                False,
                            )
                        ),
                        "is_low_contrast": bool(
                            finding.get(
                                "is_low_contrast",
                                True,
                            )
                        ),
                        "is_extreme_low_contrast": bool(
                            finding.get(
                                "is_extreme_low_contrast",
                                False,
                            )
                        ),
                        "is_small_text": bool(
                            finding.get(
                                "is_small_text",
                                False,
                            )
                        ),
                        "is_relative_small_text": bool(
                            finding.get(
                                "is_relative_small_text",
                                False,
                            )
                        ),
                        "is_instruction_like": bool(
                            finding.get(
                                "is_instruction_like",
                                False,
                            )
                        ),
                        "coordinates_label": (
                            finding.get(
                                "coordinates_label"
                            )
                        ),
                        "located": bool(
                            visual_location.get(
                                "located",
                                False,
                            )
                        ),
                        "location_message": (
                            visual_location.get(
                                "message"
                            )
                        ),
                        "source_image_url": (
                            visual_location.get(
                                "source_image_url"
                            )
                        ),
                        "annotated_image_url": (
                            visual_location.get(
                                "annotated_image_url"
                            )
                        ),
                    }
                )

            tiny_evidences = (
                analysis.get(
                    "visual_concealment_tiny_text_evidences",
                    [],
                )
                or []
            )

            for evidence_index, evidence in enumerate(
                tiny_evidences,
                start=1,
            ):
                result.append(
                    {
                        "analysis_id": analysis_id,
                        "filename": filename,
                        "finding_index": evidence_index,
                        "concealment_type": "tiny_text",
                        "concealment_type_label": (
                            "Texto muito pequeno"
                        ),
                        "code": evidence.get("code"),
                        "detector": evidence.get(
                            "detector"
                        ),
                        "page_number": evidence.get(
                            "page_number"
                        ),
                        "text": evidence.get("text"),
                        "description": evidence.get(
                            "description"
                        ),
                        "font_name": evidence.get(
                            "font_name"
                        ),
                        "font_size": evidence.get(
                            "font_size"
                        ),
                        "font_color_hex": evidence.get(
                            "font_color_hex"
                        ),
                        "background_color_hex": None,
                        "font_relative_luminance": None,
                        "background_relative_luminance": None,
                        "contrast_ratio": None,
                        "contrast_threshold": None,
                        "contrast_level": None,
                        "contrast_level_label": None,
                        "background_dominance_ratio": None,
                        "background_sampling_method": None,
                        "background_sampling_method_label": None,
                        "contrast_reference": None,
                        "confidence": evidence.get(
                            "confidence"
                        ),
                        "confidence_label": (
                            evidence.get(
                                "confidence_label"
                            )
                        ),
                        "signals": [],
                        "signal_labels": [],
                        "is_near_white": False,
                        "is_low_contrast": False,
                        "is_extreme_low_contrast": False,
                        "is_small_text": True,
                        "is_relative_small_text": False,
                        "is_instruction_like": False,
                        "coordinates_label": (
                            evidence.get(
                                "coordinates_label"
                            )
                        ),
                        "located": False,
                        "location_message": None,
                        "source_image_url": None,
                        "annotated_image_url": None,
                    }
                )

        return result

    def _build_locations(
        self,
        analysis_views: list[
            dict[str, Any]
        ],
    ) -> list[dict[str, Any]]:
        result: list[
            dict[str, Any]
        ] = []

        for analysis in analysis_views:
            analysis_id = self._string_value(
                analysis.get(
                    "id"
                )
            )

            filename = self._string_value(
                analysis.get(
                    "filename"
                )
            )

            numeric_locations = (
                analysis.get(
                    "numeric_line_locations",
                    [],
                )
                or []
            )

            for location in numeric_locations:
                result.append(
                    self._build_location_row(
                        analysis_id=analysis_id,
                        filename=filename,
                        location_type=(
                            "numeric_line"
                        ),
                        location_type_label=(
                            "Linha digitável"
                        ),
                        reference_index=(
                            location.get(
                                "line_index"
                            )
                        ),
                        reference_code=None,
                        detector=None,
                        location=location,
                    )
                )

            prompt_locations = (
                analysis.get(
                    "prompt_injection_locations",
                    [],
                )
                or []
            )

            for location in prompt_locations:
                result.append(
                    self._build_location_row(
                        analysis_id=analysis_id,
                        filename=filename,
                        location_type=(
                            "prompt_injection"
                        ),
                        location_type_label=(
                            "Prompt Injection"
                        ),
                        reference_index=(
                            location.get(
                                "evidence_index"
                            )
                        ),
                        reference_code=(
                            location.get(
                                "evidence_code"
                            )
                        ),
                        detector=(
                            location.get(
                                "detector"
                            )
                        ),
                        location=location,
                    )
                )

            concealment_locations = (
                analysis.get(
                    "visual_concealment_locations",
                    [],
                )
                or []
            )

            locatable_findings = [
                *(
                    analysis.get(
                        "visual_concealment_white_text_findings",
                        [],
                    )
                    or []
                ),
                *(
                    analysis.get(
                        "visual_concealment_low_contrast_text_findings",
                        [],
                    )
                    or []
                ),
            ]

            concealment_findings_by_index = {
                index: finding
                for index, finding in enumerate(
                    locatable_findings,
                    start=1,
                )
            }

            for location in concealment_locations:
                finding_index = location.get(
                    "finding_index"
                )

                finding = (
                    concealment_findings_by_index.get(
                        finding_index
                    )
                    or {}
                )

                result.append(
                    self._build_location_row(
                        analysis_id=analysis_id,
                        filename=filename,
                        location_type=(
                            "visual_concealment"
                        ),
                        location_type_label=(
                            "Ocultação visual"
                        ),
                        reference_index=(
                            finding_index
                        ),
                        reference_code=(
                            location.get(
                                "finding_code"
                            )
                        ),
                        detector=(
                            location.get(
                                "detector"
                            )
                        ),
                        location=location,
                        technical_context=finding,
                    )
                )

        return result

    def _build_technical_data(
        self,
        analysis_views: list[
            dict[str, Any]
        ],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        for analysis in analysis_views:
            result.append(
                {
                    "analysis_id": self._string_value(
                        analysis.get("id")
                    ),
                    "filename": self._string_value(
                        analysis.get("filename")
                    ),
                    "uploaded_at": analysis.get(
                        "uploaded_at"
                    ),
                    "size_bytes": analysis.get(
                        "size_bytes"
                    ),
                    "formatted_size": analysis.get(
                        "formatted_size"
                    ),
                    "sha256": analysis.get(
                        "sha256"
                    ),
                    "page_count": analysis.get(
                        "page_count"
                    ),
                    "pdf_title": analysis.get(
                        "pdf_title"
                    ),
                    "pdf_author": analysis.get(
                        "pdf_author"
                    ),
                    "pdf_creator": analysis.get(
                        "pdf_creator"
                    ),
                    "pdf_producer": analysis.get(
                        "pdf_producer"
                    ),
                    "pdf_creation_date": analysis.get(
                        "pdf_creation_date"
                    ),
                    "pdf_modification_date": analysis.get(
                        "pdf_modification_date"
                    ),
                    "pdf_version": analysis.get(
                        "pdf_version"
                    ),
                    "has_native_text": bool(
                        analysis.get(
                            "has_native_text",
                            False,
                        )
                    ),
                    "native_text_character_count": (
                        analysis.get(
                            "native_text_character_count",
                            0,
                        )
                    ),
                    "native_text_pages": analysis.get(
                        "native_text_pages",
                        0,
                    ),
                    "ocr_character_count": analysis.get(
                        "ocr_character_count",
                        0,
                    ),
                    "ocr_pages_processed": analysis.get(
                        "ocr_pages_processed",
                        0,
                    ),
                    "ocr_pages_with_text": analysis.get(
                        "ocr_pages_with_text",
                        0,
                    ),
                    "ocr_language": analysis.get(
                        "ocr_language"
                    ),
                    "has_normalized_document": bool(
                        analysis.get(
                            "has_normalized_document",
                            False,
                        )
                    ),
                    "normalized_document_page_count": (
                        analysis.get(
                            "normalized_document_page_count",
                            0,
                        )
                    ),
                    "normalized_document_text_span_count": (
                        analysis.get(
                            "normalized_document_text_span_count",
                            0,
                        )
                    ),
                    "normalized_document_word_count": (
                        analysis.get(
                            "normalized_document_word_count",
                            0,
                        )
                    ),
                    "normalized_document_character_count": (
                        analysis.get(
                            "normalized_document_character_count",
                            0,
                        )
                    ),
                    "normalized_document_normalized_character_count": (
                        analysis.get(
                            "normalized_document_normalized_character_count",
                            0,
                        )
                    ),
                    "normalized_document_pages_with_text": (
                        analysis.get(
                            "normalized_document_pages_with_text",
                            0,
                        )
                    ),
                    "image_count": analysis.get(
                        "image_count",
                        0,
                    ),
                    "image_fingerprint_count": analysis.get(
                        "image_fingerprint_count",
                        0,
                    ),
                    "barcode_count": analysis.get(
                        "barcode_count",
                        0,
                    ),
                    "barcode_formats": analysis.get(
                        "barcode_formats"
                    ),
                    "barcode_pages": analysis.get(
                        "barcode_pages"
                    ),
                    "printed_numeric_line_count": analysis.get(
                        "printed_numeric_line_count",
                        0,
                    ),
                    "printed_numeric_line_sources": analysis.get(
                        "printed_numeric_line_sources"
                    ),
                    "printed_numeric_digit_total": analysis.get(
                        "printed_numeric_digit_total",
                        0,
                    ),
                    "valid_numeric_line_count": analysis.get(
                        "valid_numeric_line_count",
                        0,
                    ),
                    "invalid_numeric_line_count": analysis.get(
                        "invalid_numeric_line_count",
                        0,
                    ),
                    "inconclusive_numeric_line_count": analysis.get(
                        "inconclusive_numeric_line_count",
                        0,
                    ),
                    "barcode_line_match_count": analysis.get(
                        "barcode_line_match_count",
                        0,
                    ),
                    "barcode_line_mismatch_count": analysis.get(
                        "barcode_line_mismatch_count",
                        0,
                    ),
                    "barcode_line_inconclusive_count": analysis.get(
                        "barcode_line_inconclusive_count",
                        0,
                    ),
                    "evidence_count": analysis.get(
                        "evidence_count",
                        0,
                    ),
                }
            )

        return result

    def _build_images(
        self,
        analysis_views: list[
            dict[str, Any]
        ],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        for analysis in analysis_views:
            analysis_id = self._string_value(
                analysis.get("id")
            )
            filename = self._string_value(
                analysis.get("filename")
            )
            total_extracted_images = analysis.get(
                "image_count",
                0,
            )

            fingerprints = (
                analysis.get(
                    "image_fingerprints",
                    [],
                )
                or []
            )

            for fingerprint in fingerprints:
                location = (
                    fingerprint.get("location")
                    or {}
                )

                result.append(
                    {
                        "analysis_id": analysis_id,
                        "filename": filename,
                        "total_extracted_images": (
                            total_extracted_images
                        ),
                        "fingerprint_index": fingerprint.get(
                            "index"
                        ),
                        "page_number": fingerprint.get(
                            "page_number"
                        ),
                        "width": fingerprint.get(
                            "width"
                        ),
                        "height": fingerprint.get(
                            "height"
                        ),
                        "mime_type": fingerprint.get(
                            "mime_type"
                        ),
                        "dpi": fingerprint.get(
                            "dpi"
                        ),
                        "description": fingerprint.get(
                            "description"
                        ),
                        "confidence": fingerprint.get(
                            "confidence"
                        ),
                        "image_hash": fingerprint.get(
                            "image_hash"
                        ),
                        "perceptual_hash": fingerprint.get(
                            "perceptual_hash"
                        ),
                        "average_hash": fingerprint.get(
                            "average_hash"
                        ),
                        "difference_hash": fingerprint.get(
                            "difference_hash"
                        ),
                        "location_x": location.get(
                            "x"
                        ),
                        "location_y": location.get(
                            "y"
                        ),
                        "location_width": location.get(
                            "width"
                        ),
                        "location_height": location.get(
                            "height"
                        ),
                    }
                )

        return result

    def _build_location_row(
        self,
        *,
        analysis_id: str,
        filename: str,
        location_type: str,
        location_type_label: str,
        reference_index: Any,
        reference_code: Any,
        detector: Any,
        location: dict[str, Any],
        technical_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = (
            technical_context
            or {}
        )

        return {
            "analysis_id": analysis_id,
            "filename": filename,
            "location_type": location_type,
            "location_type_label": (
                location_type_label
            ),
            "reference_index": reference_index,
            "reference_code": reference_code,
            "detector": detector,
            "page_number": location.get(
                "page_number"
            ),
            "matched_content": location.get(
                "matched_content"
            ),
            "left": location.get(
                "left"
            ),
            "top": location.get(
                "top"
            ),
            "width": location.get(
                "width"
            ),
            "height": location.get(
                "height"
            ),
            "confidence": location.get(
                "confidence"
            ),
            "confidence_label": location.get(
                "confidence_label"
            ),
            "font_name": location.get(
                "font_name"
            ),
            "font_size": location.get(
                "font_size"
            ),
            "font_color_hex": location.get(
                "font_color_hex"
            ),
            "background_color_hex": context.get(
                "background_color_hex"
            ),
            "contrast_ratio": context.get(
                "contrast_ratio"
            ),
            "contrast_threshold": context.get(
                "contrast_threshold"
            ),
            "contrast_level": context.get(
                "contrast_level"
            ),
            "contrast_level_label": context.get(
                "contrast_level_label"
            ),
            "background_dominance_ratio": (
                context.get(
                    "background_dominance_ratio"
                )
            ),
            "background_sampling_method": (
                context.get(
                    "background_sampling_method"
                )
            ),
            "background_sampling_method_label": (
                context.get(
                    "background_sampling_method_label"
                )
            ),
            "is_low_contrast": bool(
                context.get(
                    "is_low_contrast",
                    False,
                )
            ),
            "is_extreme_low_contrast": bool(
                context.get(
                    "is_extreme_low_contrast",
                    False,
                )
            ),
            "coordinates_label": location.get(
                "coordinates_label"
            ),
            "located": bool(
                location.get(
                    "located",
                    False,
                )
            ),
            "message": location.get(
                "message"
            ),
            "source_image_url": location.get(
                "source_image_url"
            ),
            "annotated_image_url": location.get(
                "annotated_image_url"
            ),
        }

    @staticmethod
    def _string_value(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        return str(
            value
        )