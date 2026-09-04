from __future__ import annotations

from typing import Any
from uuid import UUID

from app.frontend.investigations.models.investigation_card import (
    InvestigationCard,
)
from app.frontend.investigations.models.investigation_metric import (
    InvestigationMetric,
)
from app.frontend.investigations.models.investigation_status import (
    InvestigationStatus,
)


class InvestigationViewBuilder:
    """
    Converte os dados preparados pelo AnalysisViewBuilder
    em investigações compreensíveis para o usuário.

    Este builder pertence exclusivamente à camada
    de apresentação.

    Ele não:

    - executa detectores;
    - produz evidências;
    - calcula hashes;
    - interpreta autenticidade;
    - decide existência de fraude.

    Sua responsabilidade é organizar resultados técnicos
    já existentes em agrupamentos investigativos.
    """

    _SUPPORTED_SLUGS = {
        "identity",
        "structure",
        "content",
        "visual",
        "financial",
        "ai-security",
        "evidence",
    }

    def build_cards(
        self,
        *,
        analysis_id: UUID,
        analysis_view: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Constrói todos os cards exibidos
        no panorama da análise.
        """

        self._validate_analysis_id(
            analysis_id
        )

        self._validate_analysis_view(
            analysis_view
        )

        cards = (
            self._build_identity_card(
                analysis_id=analysis_id,
                analysis=analysis_view,
            ),
            self._build_structure_card(
                analysis_id=analysis_id,
                analysis=analysis_view,
            ),
            self._build_content_card(
                analysis_id=analysis_id,
                analysis=analysis_view,
            ),
            self._build_visual_card(
                analysis_id=analysis_id,
                analysis=analysis_view,
            ),
            self._build_financial_card(
                analysis_id=analysis_id,
                analysis=analysis_view,
            ),
            self._build_ai_security_card(
                analysis_id=analysis_id,
                analysis=analysis_view,
            ),
            self._build_evidence_card(
                analysis_id=analysis_id,
                analysis=analysis_view,
            ),
        )

        ordered_cards = (
            self._sort_cards_by_status(
                cards
            )
        )

        return [
            self._serialize_card(
                card
            )
            for card
            in ordered_cards
        ]

    def build_detail(
            self,
            *,
            analysis_id: UUID,
            slug: str,
            analysis_view: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Constrói o contexto de apresentação
        de uma investigação detalhada.
        """

        self._validate_analysis_id(
            analysis_id
        )

        self._validate_analysis_view(
            analysis_view
        )

        normalized_slug = (
            self._normalize_slug(
                slug
            )
        )

        if (
                normalized_slug
                not in self._SUPPORTED_SLUGS
        ):
            raise ValueError(
                "Investigação não reconhecida."
            )

        cards = {
            card["slug"]: card
            for card
            in self.build_cards(
                analysis_id=analysis_id,
                analysis_view=analysis_view,
            )
        }

        investigation = (
            cards[
                normalized_slug
            ]
        )

        detail = (
            self._build_detail_content(
                slug=normalized_slug,
                analysis=analysis_view,
            )
        )

        return {
            "analysis": (
                analysis_view
            ),
            "investigation": (
                investigation
            ),
            "detail": (
                detail
            ),
            "slug": (
                normalized_slug
            ),
            "back_url": (
                f"/analyses/{analysis_id}"
            ),
        }

    def _build_detail_content(
        self,
        *,
        slug: str,
        analysis: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Constrói conteúdo detalhado específico
        para investigações que necessitam de
        organização adicional dos dados.
        """

        if slug == "ai-security":
            return (
                self._build_ai_security_detail(
                    analysis
                )
            )

        return None

    def _build_ai_security_detail(
        self,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Organiza as evidências de segurança para IA
        em uma visão investigativa compreensível.

        A apresentação diferencia:

        - ocorrências suspeitas;
        - evidências técnicas;
        - fontes independentes;
        - representações derivadas;
        - indicadores de ocultação visual.
        """

        evidences = list(
            analysis.get(
                "prompt_injection_evidences",
                [],
            )
        )

        locations = list(
            analysis.get(
                "prompt_injection_locations",
                [],
            )
        )

        visual_locations = (
            self._build_ai_security_visual_locations(
                locations=locations,
                evidences=evidences,
            )
        )

        located_visual_locations = [
            location
            for location
            in visual_locations
            if location.get(
                "located"
            )
        ]

        unlocated_visual_locations = [
            location
            for location
            in visual_locations
            if not location.get(
                "located"
            )
        ]

        primary_visual_location = (
            located_visual_locations[0]
            if located_visual_locations
            else None
        )

        textual_evidences = [
            evidence
            for evidence
            in evidences
            if evidence.get(
                "category"
            )
            != "visual_concealment"
        ]

        concealment_evidences = [
            evidence
            for evidence
            in evidences
            if evidence.get(
                "category"
            )
            == "visual_concealment"
        ]

        occurrences = (
            self._group_ai_security_occurrences(
                textual_evidences
            )
        )

        sources = (
            self._build_ai_security_sources(
                evidences
            )
        )

        concealment_indicators = (
            self._build_concealment_indicators(
                concealment_evidences
            )
        )

        independent_sources_detected = [
            source
            for source
            in sources
            if (
                source[
                    "independent"
                ]
                and source[
                    "detected"
                ]
            )
        ]

        corroborated = (
            len(
                independent_sources_detected
            )
            >= 2
        )

        primary_occurrence = (
            occurrences[0]
            if occurrences
            else None
        )

        return {
            "type": (
                "ai-security"
            ),

            "risk_level": (
                analysis.get(
                    "prompt_injection_risk_level",
                    "none",
                )
            ),

            "risk_label": (
                analysis.get(
                    "prompt_injection_risk_label",
                    "Nenhum",
                )
            ),

            "score": (
                analysis.get(
                    "prompt_injection_score",
                    0.0,
                )
            ),

            "score_label": (
                analysis.get(
                    "prompt_injection_score_label",
                    "0.0%",
                )
            ),

            "summary": (
                analysis.get(
                    "prompt_injection_summary",
                    ""
                )
            ),

            "evidence_count": (
                len(
                    evidences
                )
            ),

            "textual_evidence_count": (
                len(
                    textual_evidences
                )
            ),

            "occurrence_count": (
                len(
                    occurrences
                )
            ),

            "concealment_evidence_count": (
                len(
                    concealment_evidences
                )
            ),

            "category_count": (
                analysis.get(
                    "prompt_injection_category_count",
                    0,
                )
            ),

            "categories": (
                analysis.get(
                    "prompt_injection_category_labels",
                    [],
                )
            ),

            "languages": (
                analysis.get(
                    "prompt_injection_languages",
                    [],
                )
            ),

            "sources": (
                sources
            ),

            "independent_source_count": (
                len(
                    independent_sources_detected
                )
            ),

            "corroborated": (
                corroborated
            ),

            "corroboration_label": (
                "Corroborado por fontes independentes"
                if corroborated
                else (
                    "Identificado em uma fonte independente"
                    if independent_sources_detected
                    else (
                        "Sem corroboração independente"
                    )
                )
            ),

            "occurrences": (
                occurrences
            ),

            "primary_occurrence": (
                primary_occurrence
            ),

            "concealment_indicators": (
                concealment_indicators
            ),

            "visual_locations": (
                visual_locations
            ),

            "located_visual_locations": (
                located_visual_locations
            ),

            "unlocated_visual_locations": (
                unlocated_visual_locations
            ),

            "visual_location_count": (
                len(
                    visual_locations
                )
            ),

            "located_visual_location_count": (
                len(
                    located_visual_locations
                )
            ),

            "unlocated_visual_location_count": (
                len(
                    unlocated_visual_locations
                )
            ),

            "has_visual_locations": (
                bool(
                    located_visual_locations
                )
            ),

            "primary_visual_location": (
                primary_visual_location
            ),

            "evidences": (
                evidences
            ),
        }

    def _build_ai_security_visual_locations(
        self,
        *,
        locations: list[
            dict[str, Any]
        ],
        evidences: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:
        """
        Organiza as localizações visuais produzidas pelo
        PromptInjectionVisualEvidenceBuilder.

        O evidence_index é 1-based e corresponde à ordem
        das evidências no PromptInjectionAssessment.
        """

        result: list[
            dict[str, Any]
        ] = []

        for location in locations:
            evidence_index = location.get(
                "evidence_index"
            )

            related_evidence = None

            if (
                isinstance(
                    evidence_index,
                    int,
                )
                and evidence_index >= 1
                and evidence_index
                <= len(
                    evidences
                )
            ):
                related_evidence = (
                    evidences[
                        evidence_index - 1
                    ]
                )

            page_number = location.get(
                "page_number"
            )

            matched_content = (
                location.get(
                    "matched_content"
                )
                or (
                    related_evidence.get(
                        "original_excerpt"
                    )
                    if related_evidence
                    else None
                )
                or (
                    related_evidence.get(
                        "normalized_excerpt"
                    )
                    if related_evidence
                    else None
                )
                or ""
            )

            left = location.get(
                "left"
            )

            top = location.get(
                "top"
            )

            width = location.get(
                "width"
            )

            height = location.get(
                "height"
            )

            coordinates_available = all(
                value is not None
                for value in (
                    left,
                    top,
                    width,
                    height,
                )
            )

            coordinates_label = (
                (
                    f"X {left} · Y {top} · "
                    f"{width} × {height}"
                )
                if coordinates_available
                else (
                    "Coordenadas não disponíveis"
                )
            )

            result.append(
                {
                    **location,

                    "page_label": (
                        self._format_single_page_label(
                            page_number
                        )
                    ),

                    "coordinates_label": (
                        coordinates_label
                    ),

                    "excerpt": (
                        matched_content
                    ),

                    "category": (
                        related_evidence.get(
                            "category"
                        )
                        if related_evidence
                        else None
                    ),

                    "category_label": (
                        related_evidence.get(
                            "category_label"
                        )
                        if related_evidence
                        else (
                            "Evidência de segurança para IA"
                        )
                    ),

                    "source": (
                        related_evidence.get(
                            "source"
                        )
                        if related_evidence
                        else None
                    ),

                    "source_label": (
                        related_evidence.get(
                            "source_label"
                        )
                        if related_evidence
                        else (
                            "Não informada"
                        )
                    ),

                    "evidence_confidence_label": (
                        related_evidence.get(
                            "confidence_label"
                        )
                        if related_evidence
                        else None
                    ),

                    "has_annotated_image": bool(
                        location.get(
                            "annotated_image_url"
                        )
                    ),

                    "has_source_image": bool(
                        location.get(
                            "source_image_url"
                        )
                    ),
                }
            )

        return result

    def _build_ai_security_sources(
        self,
        evidences: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:
        """
        Monta o quadro de fontes utilizadas.

        Texto nativo e OCR são tratados como fontes
        independentes.

        Documento normalizado é uma representação
        derivada utilizada internamente pelo DocDNA.

        Análise tipográfica representa verificação
        estrutural/visual dos TextSpan.
        """

        definitions = (
            {
                "source": (
                    "native_text"
                ),
                "label": (
                    "Texto nativo do PDF"
                ),
                "description": (
                    "Conteúdo existente diretamente "
                    "na camada textual do arquivo PDF."
                ),
                "independent": True,
            },
            {
                "source": (
                    "ocr"
                ),
                "label": (
                    "OCR"
                ),
                "description": (
                    "Conteúdo identificado por leitura "
                    "óptica independente da camada "
                    "textual do PDF."
                ),
                "independent": True,
            },
            {
                "source": (
                    "normalized_document"
                ),
                "label": (
                    "Documento normalizado"
                ),
                "description": (
                    "Representação textual reconstruída "
                    "pelo DocDNA para análise estrutural."
                ),
                "independent": False,
            },
            {
                "source": (
                    "normalized_document_visual"
                ),
                "label": (
                    "Análise tipográfica"
                ),
                "description": (
                    "Verificação de tamanho, fonte e "
                    "características dos trechos textuais."
                ),
                "independent": False,
            },
        )

        result = []

        for definition in definitions:
            source_name = (
                definition[
                    "source"
                ]
            )

            source_evidences = [
                evidence
                for evidence
                in evidences
                if evidence.get(
                    "source"
                )
                == source_name
            ]

            result.append(
                {
                    **definition,
                    "detected": bool(
                        source_evidences
                    ),
                    "evidence_count": (
                        len(
                            source_evidences
                        )
                    ),
                }
            )

        return result

    def _group_ai_security_occurrences(
        self,
        evidences: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:
        """
        Agrupa evidências técnicas que provavelmente
        representam a mesma ocorrência textual.

        O agrupamento é exclusivo da apresentação.
        Não modifica score nem evidências de domínio.
        """

        occurrences: list[
            dict[str, Any]
        ] = []

        ordered_evidences = sorted(
            evidences,
            key=lambda evidence: (
                float(
                    evidence.get(
                        "weighted_score",
                        0.0,
                    )
                    or 0.0
                ),
                float(
                    evidence.get(
                        "confidence",
                        0.0,
                    )
                    or 0.0
                ),
            ),
            reverse=True,
        )

        for evidence in ordered_evidences:
            excerpt = (
                evidence.get(
                    "original_excerpt"
                )
                or evidence.get(
                    "normalized_excerpt"
                )
                or ""
            )

            signature = (
                self._normalize_occurrence_text(
                    excerpt
                )
            )

            matched_occurrence = None

            for occurrence in occurrences:
                if (
                    self._occurrence_texts_match(
                        signature,
                        occurrence[
                            "_signature"
                        ],
                    )
                ):
                    matched_occurrence = (
                        occurrence
                    )
                    break

            if matched_occurrence is None:
                matched_occurrence = {
                    "_signature": (
                        signature
                    ),
                    "_source_names": set(),
                    "_detector_names": set(),
                    "_categories": set(),
                    "_page_numbers": set(),

                    "excerpt": (
                        excerpt
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

                    "matched_rule": (
                        evidence.get(
                            "matched_rule"
                        )
                    ),

                    "evidence_count": 0,
                }

                occurrences.append(
                    matched_occurrence
                )

            matched_occurrence[
                "evidence_count"
            ] += 1

            source = evidence.get(
                "source"
            )

            if source:
                matched_occurrence[
                    "_source_names"
                ].add(
                    source
                )

            detector = evidence.get(
                "detector"
            )

            if detector:
                matched_occurrence[
                    "_detector_names"
                ].add(
                    detector
                )

            category_label = (
                evidence.get(
                    "category_label"
                )
            )

            if category_label:
                matched_occurrence[
                    "_categories"
                ].add(
                    category_label
                )

            page_number = evidence.get(
                "page_number"
            )

            if page_number is not None:
                matched_occurrence[
                    "_page_numbers"
                ].add(
                    page_number
                )

        result = []

        for index, occurrence in enumerate(
            occurrences,
            start=1,
        ):
            source_names = sorted(
                occurrence[
                    "_source_names"
                ]
            )

            source_labels = [
                self._ai_security_source_label(
                    source
                )
                for source
                in source_names
            ]

            page_numbers = sorted(
                occurrence[
                    "_page_numbers"
                ]
            )

            independent_sources = {
                source
                for source
                in source_names
                if source
                in {
                    "native_text",
                    "ocr",
                }
            }

            corroborated = (
                len(
                    independent_sources
                )
                >= 2
            )

            result.append(
                {
                    "index": (
                        index
                    ),

                    "title": (
                        "Possível instrução "
                        "direcionada a sistema de IA"
                    ),

                    "excerpt": (
                        occurrence[
                            "excerpt"
                        ]
                    ),

                    "page_numbers": (
                        page_numbers
                    ),

                    "page_label": (
                        self._format_page_labels(
                            page_numbers
                        )
                    ),

                    "sources": (
                        source_names
                    ),

                    "source_labels": (
                        source_labels
                    ),

                    "detectors": sorted(
                        occurrence[
                            "_detector_names"
                        ]
                    ),

                    "categories": sorted(
                        occurrence[
                            "_categories"
                        ]
                    ),

                    "confidence": (
                        occurrence[
                            "confidence"
                        ]
                    ),

                    "confidence_label": (
                        occurrence[
                            "confidence_label"
                        ]
                    ),

                    "weighted_score": (
                        occurrence[
                            "weighted_score"
                        ]
                    ),

                    "weighted_score_label": (
                        occurrence[
                            "weighted_score_label"
                        ]
                    ),

                    "matched_rule": (
                        occurrence[
                            "matched_rule"
                        ]
                    ),

                    "evidence_count": (
                        occurrence[
                            "evidence_count"
                        ]
                    ),

                    "corroborated": (
                        corroborated
                    ),

                    "corroboration_label": (
                        "Confirmado em texto nativo e OCR"
                        if corroborated
                        else (
                            "Identificado em uma fonte"
                        )
                    ),
                }
            )

        return result

    def _build_concealment_indicators(
        self,
        evidences: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:
        """
        Organiza indicadores de possível ocultação
        tipográfica.
        """

        result = []

        for index, evidence in enumerate(
            evidences,
            start=1,
        ):
            font_size = evidence.get(
                "font_size"
            )

            maximum_font_size = (
                evidence.get(
                    "maximum_font_size"
                )
            )

            result.append(
                {
                    "index": index,

                    "type": (
                        "tiny_text"
                    ),

                    "title": (
                        "Texto com fonte "
                        "anormalmente pequena"
                    ),

                    "page_number": (
                        evidence.get(
                            "page_number"
                        )
                    ),

                    "page_label": (
                        self._format_single_page_label(
                            evidence.get(
                                "page_number"
                            )
                        )
                    ),

                    "excerpt": (
                        evidence.get(
                            "original_excerpt"
                        )
                        or evidence.get(
                            "normalized_excerpt"
                        )
                        or ""
                    ),

                    "font_name": (
                        evidence.get(
                            "font_name"
                        )
                        or "Não identificada"
                    ),

                    "font_size": (
                        font_size
                    ),

                    "font_size_label": (
                        (
                            f"{float(font_size):.2f} pt"
                        )
                        if font_size
                        is not None
                        else (
                            "Não informado"
                        )
                    ),

                    "maximum_font_size": (
                        maximum_font_size
                    ),

                    "maximum_font_size_label": (
                        (
                            f"{float(maximum_font_size):.2f} pt"
                        )
                        if maximum_font_size
                        is not None
                        else (
                            "Não informado"
                        )
                    ),

                    "font_color": (
                        evidence.get(
                            "font_color"
                        )
                        or "Não informada"
                    ),

                    "confidence_label": (
                        evidence.get(
                            "confidence_label"
                        )
                    ),

                    "detector": (
                        evidence.get(
                            "detector"
                        )
                    ),
                }
            )

        return result

    @staticmethod
    def _normalize_occurrence_text(
        value: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            return ""

        return " ".join(
            value
            .casefold()
            .split()
        )

    def _occurrence_texts_match(
        self,
        first: str,
        second: str,
    ) -> bool:
        if not first or not second:
            return False

        if (
            first in second
            or second in first
        ):
            return True

        first_tokens = {
            token
            for token
            in first.split()
            if len(token) >= 3
        }

        second_tokens = {
            token
            for token
            in second.split()
            if len(token) >= 3
        }

        if (
            not first_tokens
            or not second_tokens
        ):
            return False

        intersection = (
            first_tokens
            & second_tokens
        )

        union = (
            first_tokens
            | second_tokens
        )

        similarity = (
            len(intersection)
            / len(union)
        )

        return (
            similarity >= 0.70
        )

    @staticmethod
    def _ai_security_source_label(
        source: str,
    ) -> str:
        labels = {
            "native_text": (
                "Texto nativo do PDF"
            ),
            "ocr": (
                "OCR"
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

    @staticmethod
    def _format_page_labels(
        page_numbers: list[int],
    ) -> str:
        if not page_numbers:
            return (
                "Localização não determinada "
                "nesta fonte"
            )

        if len(page_numbers) == 1:
            return (
                f"Página {page_numbers[0]}"
            )

        pages = ", ".join(
            str(page)
            for page
            in page_numbers
        )

        return (
            f"Páginas {pages}"
        )

    @staticmethod
    def _format_single_page_label(
        page_number: Any,
    ) -> str:
        if page_number is None:
            return (
                "Página não determinada"
            )

        return (
            f"Página {page_number}"
        )

    def _build_identity_card(
        self,
        *,
        analysis_id: UUID,
        analysis: dict[str, Any],
    ) -> InvestigationCard:
        """
        Agrupa informações de identidade
        e integridade do arquivo.
        """

        return InvestigationCard(
            slug="identity",
            title=(
                "Identidade e integridade"
            ),
            status=(
                InvestigationStatus.CLEAR
            ),
            status_label=(
                "Dados coletados"
            ),
            summary=(
                "O arquivo foi identificado e teve sua "
                "integridade criptográfica registrada. "
                "Esta etapa organiza os dados técnicos "
                "coletados e não representa, por si só, "
                "uma conclusão de autenticidade documental."
            ),
            metrics=(
                InvestigationMetric(
                    label="Páginas",
                    value=str(
                        analysis[
                            "page_count"
                        ]
                    ),
                ),
                InvestigationMetric(
                    label="Tamanho",
                    value=str(
                        analysis[
                            "formatted_size"
                        ]
                    ),
                ),
                InvestigationMetric(
                    label="SHA-256",
                    value="Registrado",
                ),
            ),
            evidence_count=0,
            route=self._build_route(
                analysis_id=analysis_id,
                slug="identity",
            ),
        )

    def _build_structure_card(
        self,
        *,
        analysis_id: UUID,
        analysis: dict[str, Any],
    ) -> InvestigationCard:
        """
        Agrupa o domínio documental normalizado.
        """

        has_document = bool(
            analysis[
                "has_normalized_document"
            ]
        )

        if has_document:
            status = (
                InvestigationStatus.CLEAR
            )

            status_label = (
                "Etapa concluída"
            )

            summary = (
                "A estrutura documental foi normalizada "
                "em páginas e trechos textuais posicionais. "
                "Nenhuma inconsistência estrutural foi "
                "produzida pelos verificadores executados "
                "nesta etapa."
            )

        else:
            status = (
                InvestigationStatus.NOT_EXECUTED
            )

            status_label = (
                "Não disponível"
            )

            summary = (
                "A estrutura documental normalizada "
                "não foi disponibilizada nesta execução."
            )

        return InvestigationCard(
            slug="structure",
            title=(
                "Estrutura documental"
            ),
            status=status,
            status_label=status_label,
            summary=summary,
            metrics=(
                InvestigationMetric(
                    label="Páginas",
                    value=str(
                        analysis[
                            "normalized_document_page_count"
                        ]
                    ),
                ),
                InvestigationMetric(
                    label="Trechos textuais",
                    value=str(
                        analysis[
                            "normalized_document_text_span_count"
                        ]
                    ),
                ),
                InvestigationMetric(
                    label="Palavras",
                    value=str(
                        analysis[
                            "normalized_document_word_count"
                        ]
                    ),
                ),
            ),
            evidence_count=0,
            route=self._build_route(
                analysis_id=analysis_id,
                slug="structure",
            ),
        )

    def _build_content_card(
        self,
        *,
        analysis_id: UUID,
        analysis: dict[str, Any],
    ) -> InvestigationCard:
        """
        Agrupa texto nativo, OCR
        e conteúdo normalizado.
        """

        native_character_count = int(
            analysis[
                "native_text_character_count"
            ]
        )

        ocr_character_count = int(
            analysis[
                "ocr_character_count"
            ]
        )

        has_content = (
            native_character_count > 0
            or ocr_character_count > 0
        )

        if has_content:
            status = (
                InvestigationStatus.CLEAR
            )

            status_label = (
                "Conteúdo extraído"
            )

            summary = (
                "O conteúdo textual foi extraído pelas "
                "camadas disponíveis de texto nativo e OCR. "
                "A presença ou ausência de uma dessas camadas "
                "não representa, isoladamente, indício "
                "de fraude."
            )

        else:
            status = (
                InvestigationStatus.ATTENTION
            )

            status_label = (
                "Revisão recomendada"
            )

            summary = (
                "Nenhum conteúdo textual legível foi obtido "
                "pelas camadas executadas. Recomenda-se "
                "revisão manual da legibilidade e estrutura "
                "do documento."
            )

        return InvestigationCard(
            slug="content",
            title="Conteúdo textual",
            status=status,
            status_label=status_label,
            summary=summary,
            metrics=(
                InvestigationMetric(
                    label=(
                        "Caracteres nativos"
                    ),
                    value=str(
                        native_character_count
                    ),
                ),
                InvestigationMetric(
                    label="Caracteres OCR",
                    value=str(
                        ocr_character_count
                    ),
                ),
                InvestigationMetric(
                    label="Páginas OCR",
                    value=str(
                        analysis[
                            "ocr_pages_with_text"
                        ]
                    ),
                ),
            ),
            evidence_count=0,
            route=self._build_route(
                analysis_id=analysis_id,
                slug="content",
            ),
        )

    def _build_visual_card(
        self,
        *,
        analysis_id: UUID,
        analysis: dict[str, Any],
    ) -> InvestigationCard:
        """
        Agrupa imagens internas
        e fingerprints visuais.
        """

        image_count = int(
            analysis[
                "image_count"
            ]
        )

        fingerprint_count = int(
            analysis[
                "image_fingerprint_count"
            ]
        )

        has_visual_data = (
            image_count > 0
            or fingerprint_count > 0
        )

        if has_visual_data:
            status = (
                InvestigationStatus.CLEAR
            )

            status_label = (
                "Dados visuais coletados"
            )

            summary = (
                "Os elementos visuais disponíveis foram "
                "extraídos e receberam representação técnica "
                "quando possível. A análise individual atual "
                "ainda não classifica automaticamente logos, "
                "assinaturas ou duplicidades entre documentos."
            )

        else:
            status = (
                InvestigationStatus.NOT_EXECUTED
            )

            status_label = (
                "Sem elementos analisáveis"
            )

            summary = (
                "Nenhum elemento visual interno com dados "
                "suficientes foi disponibilizado para "
                "esta investigação."
            )

        return InvestigationCard(
            slug="visual",
            title="Elementos visuais",
            status=status,
            status_label=status_label,
            summary=summary,
            metrics=(
                InvestigationMetric(
                    label="Imagens extraídas",
                    value=str(
                        image_count
                    ),
                ),
                InvestigationMetric(
                    label="Fingerprints",
                    value=str(
                        fingerprint_count
                    ),
                ),
                InvestigationMetric(
                    label="Imagens no PDF",
                    value=(
                        "Sim"
                        if analysis[
                            "has_images"
                        ]
                        else "Não"
                    ),
                ),
            ),
            evidence_count=0,
            route=self._build_route(
                analysis_id=analysis_id,
                slug="visual",
            ),
        )

    def _build_financial_card(
        self,
        *,
        analysis_id: UUID,
        analysis: dict[str, Any],
    ) -> InvestigationCard:
        """
        Agrupa barcode, linha digitável,
        validações e comparações.
        """

        barcode_count = int(
            analysis[
                "barcode_count"
            ]
        )

        line_count = int(
            analysis[
                "printed_numeric_line_count"
            ]
        )

        mismatch_count = int(
            analysis[
                "barcode_line_mismatch_count"
            ]
        )

        invalid_count = int(
            analysis[
                "invalid_numeric_line_count"
            ]
        )

        barcode_inconclusive_count = int(
            analysis[
                "barcode_line_inconclusive_count"
            ]
        )

        line_inconclusive_count = int(
            analysis[
                "inconclusive_numeric_line_count"
            ]
        )

        total_inconclusive = (
            barcode_inconclusive_count
            + line_inconclusive_count
        )

        has_elements = (
            barcode_count > 0
            or line_count > 0
        )

        if (
            mismatch_count > 0
            or invalid_count > 0
        ):
            status = (
                InvestigationStatus.ALERT
            )

            status_label = (
                "Inconsistência identificada"
            )

            summary = (
                "Foram identificadas divergências entre "
                "elementos financeiros ou sequências "
                "estruturalmente inválidas. A revisão "
                "detalhada desta etapa é recomendada."
            )

        elif total_inconclusive > 0:
            status = (
                InvestigationStatus.ATTENTION
            )

            status_label = (
                "Resultado inconclusivo"
            )

            summary = (
                "Parte dos verificadores financeiros "
                "produziu resultado inconclusivo. "
                "Os dados detalhados devem ser revisados "
                "antes de qualquer conclusão."
            )

        elif has_elements:
            status = (
                InvestigationStatus.CLEAR
            )

            status_label = (
                "Sem divergência detectada"
            )

            summary = (
                "Nenhuma divergência foi identificada "
                "pelos verificadores financeiros "
                "executados nesta etapa."
            )

        else:
            status = (
                InvestigationStatus.NOT_EXECUTED
            )

            status_label = (
                "Sem elementos analisáveis"
            )

            summary = (
                "Não foram encontrados códigos ou "
                "sequências numéricas suficientes "
                "para esta investigação."
            )

        financial_evidence_count = (
            mismatch_count
            + invalid_count
        )

        return InvestigationCard(
            slug="financial",
            title=(
                "Elementos financeiros"
            ),
            status=status,
            status_label=status_label,
            summary=summary,
            metrics=(
                InvestigationMetric(
                    label="Códigos",
                    value=str(
                        barcode_count
                    ),
                ),
                InvestigationMetric(
                    label="Sequências",
                    value=str(
                        line_count
                    ),
                ),
                InvestigationMetric(
                    label="Divergências",
                    value=str(
                        mismatch_count
                    ),
                ),
            ),
            evidence_count=(
                financial_evidence_count
            ),
            route=self._build_route(
                analysis_id=analysis_id,
                slug="financial",
            ),
        )

    def _build_ai_security_card(
        self,
        *,
        analysis_id: UUID,
        analysis: dict[str, Any],
    ) -> InvestigationCard:
        """
        Agrupa os verificadores relacionados
        à interação entre o documento e sistemas de IA.

        O status global desta investigação considera duas
        frentes independentes de análise:

        - Prompt Injection;
        - ocultação visual textual.

        A presença de ocultação visual pode recomendar
        revisão humana mesmo quando o risco textual de
        Prompt Injection permanecer classificado como
        "Nenhum".

        Este builder não altera o score do detector de
        Prompt Injection e não converte ocultação visual
        em Prompt Injection.
        """

        has_assessment = bool(
            analysis.get(
                "has_prompt_injection_assessment",
                False,
            )
        )

        risk_level = str(
            analysis.get(
                "prompt_injection_risk_level",
                "none",
            )
        ).lower()

        risk_label = str(
            analysis.get(
                "prompt_injection_risk_label",
                "Nenhum",
            )
        )

        score_label = str(
            analysis.get(
                "prompt_injection_score_label",
                "0.0%",
            )
        )

        prompt_evidence_count = int(
            analysis.get(
                "prompt_injection_evidence_count",
                0,
            )
        )

        located_visual_count = int(
            analysis.get(
                "located_prompt_injection_count",
                0,
            )
        )

        assessment_summary = str(
            analysis.get(
                "prompt_injection_summary",
                "",
            )
        ).strip()

        visual_concealment_count = int(
            analysis.get(
                "visual_concealment_total_count",
                0,
            )
        )

        white_text_count = int(
            analysis.get(
                "visual_concealment_white_text_count",
                0,
            )
        )

        low_contrast_text_count = int(
            analysis.get(
                "visual_concealment_low_contrast_text_count",
                0,
            )
        )

        tiny_text_count = int(
            analysis.get(
                "visual_concealment_tiny_text_count",
                0,
            )
        )

        has_visual_concealment = bool(
            analysis.get(
                "has_visual_concealment_findings",
                False,
            )
            or visual_concealment_count > 0
        )

        total_security_evidence_count = (
            prompt_evidence_count
            + visual_concealment_count
        )

        if risk_level in {"high", "critical"}:
            status = InvestigationStatus.ALERT
            status_label = "Atenção prioritária"

            if has_visual_concealment:
                summary = (
                    "Foram identificados sinais relevantes associados a possível "
                    "tentativa de direcionamento ou manipulação de sistemas de IA, "
                    "além de conteúdo textual com características de ocultação visual. "
                    "Recomenda-se revisão prioritária."
                )
            else:
                summary = assessment_summary or (
                    "Foram identificados sinais relevantes associados a possível "
                    "tentativa de direcionamento ou manipulação de sistemas de IA."
                )

        elif risk_level in {"low", "medium"} or has_visual_concealment:
            status = InvestigationStatus.ATTENTION
            status_label = "Revisão recomendada"

            if risk_level == "none" and has_visual_concealment:
                summary = (
                    "Nenhum padrão textual foi classificado como Prompt Injection, "
                    "porém foram identificados conteúdos com características de "
                    "ocultação visual, como fonte branca ou quase branca, baixo "
                    "contraste em relação ao fundo e/ou tamanho tipográfico reduzido. "
                    "Recomenda-se revisão humana."
                )
            elif has_visual_concealment:
                summary = (
                    "Foram identificados sinais associados a possível Prompt Injection "
                    "e também achados de ocultação visual textual. Recomenda-se revisão "
                    "conjunta das evidências."
                )
            elif risk_level == "low":
                summary = assessment_summary or (
                    "Foi identificado sinal textual de baixa intensidade associado a "
                    "padrões potenciais de Prompt Injection. Recomenda-se revisão contextual."
                )
            else:
                summary = assessment_summary or (
                    "Foram identificados padrões textuais compatíveis com possível "
                    "Prompt Injection. Recomenda-se revisão das evidências."
                )

        elif not has_assessment:
            status = InvestigationStatus.NOT_EXECUTED
            status_label = "Verificação não disponível"
            summary = (
                "O verificador textual de segurança para sistemas de IA não foi "
                "disponibilizado nesta execução e nenhum achado independente de "
                "ocultação visual foi registrado."
            )

        elif risk_level == "none":
            status = InvestigationStatus.CLEAR
            status_label = "Nenhum padrão suspeito"
            summary = assessment_summary or (
                "Nenhum padrão textual associado a possível Prompt Injection e nenhum "
                "achado de ocultação visual textual foram identificados pelos "
                "verificadores executados."
            )

        else:
            status = InvestigationStatus.ATTENTION
            status_label = "Resultado para revisão"
            summary = assessment_summary or (
                "Os verificadores de segurança para IA produziram resultado que requer revisão."
            )

        concealment_metric_value = str(
            visual_concealment_count
        )

        if visual_concealment_count > 0:
            parts = [
                f"{visual_concealment_count}",
                f"{white_text_count} branco/quase branco",
            ]

            if low_contrast_text_count > 0:
                parts.append(
                    f"{low_contrast_text_count} baixo contraste"
                )

            if tiny_text_count > 0:
                parts.append(
                    f"{tiny_text_count} minúsculo"
                )

            concealment_metric_value = (
                parts[0]
                + " ("
                + ", ".join(parts[1:])
                + ")"
            )

        return InvestigationCard(
            slug="ai-security",
            title="IA e segurança",
            status=status,
            status_label=status_label,
            summary=summary,
            metrics=(
                InvestigationMetric(
                    label="Risco textual",
                    value=(
                        risk_label
                        if has_assessment
                        else "Não executado"
                    ),
                ),
                InvestigationMetric(
                    label="Score",
                    value=(
                        score_label
                        if has_assessment
                        else "—"
                    ),
                ),
                InvestigationMetric(
                    label="Ocultação visual",
                    value=concealment_metric_value,
                ),
                InvestigationMetric(
                    label="Evidências técnicas",
                    value=str(
                        total_security_evidence_count
                    ),
                ),
                InvestigationMetric(
                    label="Áreas de Prompt Injection localizadas",
                    value=str(
                        located_visual_count
                    ),
                ),
            ),
            evidence_count=(
                total_security_evidence_count
            ),
            route=self._build_route(
                analysis_id=analysis_id,
                slug="ai-security",
            ),
        )

    def _build_evidence_card(
        self,
        *,
        analysis_id: UUID,
        analysis: dict[str, Any],
    ) -> InvestigationCard:
        """
        Agrupa os findings produzidos
        pelos detectores documentais gerais.

        As evidências específicas de Prompt Injection
        permanecem na investigação IA e segurança,
        pois pertencem a outro modelo de domínio.
        """

        evidences = analysis[
            "evidences"
        ]

        evidence_count = int(
            analysis[
                "evidence_count"
            ]
        )

        medium_count = sum(
            evidence.get(
                "severity"
            ) == "medium"
            for evidence
            in evidences
        )

        high_or_critical_count = sum(
            evidence.get(
                "severity"
            )
            in {
                "high",
                "critical",
            }
            for evidence
            in evidences
        )

        low_or_info_count = sum(
            evidence.get(
                "severity"
            )
            in {
                "info",
                "low",
            }
            for evidence
            in evidences
        )

        if high_or_critical_count > 0:
            status = (
                InvestigationStatus.ALERT
            )

            status_label = (
                "Atenção prioritária"
            )

            summary = (
                "Existem evidências de alta prioridade "
                "produzidas pelos detectores executados. "
                "Recomenda-se revisão detalhada "
                "pelo analista."
            )

        elif medium_count > 0:
            status = (
                InvestigationStatus.ATTENTION
            )

            status_label = (
                "Pontos para revisão"
            )

            summary = (
                "Foram registradas evidências "
                "de severidade média que merecem "
                "revisão manual."
            )

        elif evidence_count > 0:
            status = (
                InvestigationStatus.CLEAR
            )

            status_label = (
                "Evidências informativas"
            )

            summary = (
                "Foram registradas evidências técnicas "
                "informativas ou de baixa severidade, "
                "sem alerta de alta prioridade "
                "nesta análise."
            )

        else:
            status = (
                InvestigationStatus.CLEAR
            )

            status_label = (
                "Nenhum alerta registrado"
            )

            summary = (
                "Nenhuma evidência técnica foi registrada "
                "pelos verificadores executados. "
                "Isso não equivale a uma declaração "
                "de autenticidade documental."
            )

        return InvestigationCard(
            slug="evidence",
            title=(
                "Evidências e alertas"
            ),
            status=status,
            status_label=status_label,
            summary=summary,
            metrics=(
                InvestigationMetric(
                    label="Total",
                    value=str(
                        evidence_count
                    ),
                ),
                InvestigationMetric(
                    label=(
                        "Informativas ou baixas"
                    ),
                    value=str(
                        low_or_info_count
                    ),
                ),
                InvestigationMetric(
                    label=(
                        "Médias ou superiores"
                    ),
                    value=str(
                        medium_count
                        + high_or_critical_count
                    ),
                ),
            ),
            evidence_count=(
                evidence_count
            ),
            route=self._build_route(
                analysis_id=analysis_id,
                slug="evidence",
            ),
        )

    @staticmethod
    def _sort_cards_by_status(
            cards: tuple[
                InvestigationCard,
                ...,
            ],
    ) -> tuple[
        InvestigationCard,
        ...,
    ]:
        """
        Ordena os cards por prioridade analítica de apresentação.

        Precedência:

            ALERT
            ATTENTION
            CLEAR
            NOT_EXECUTED

        """

        priority = {
            InvestigationStatus.ALERT: 0,
            InvestigationStatus.ATTENTION: 1,
            InvestigationStatus.CLEAR: 2,
            InvestigationStatus.NOT_EXECUTED: 3,
        }

        return tuple(
            sorted(
                cards,
                key=lambda card: (
                    priority[
                        card.status
                    ]
                ),
            )
        )

    @staticmethod
    def _build_route(
        *,
        analysis_id: UUID,
        slug: str,
    ) -> str:
        return (
            f"/analyses/{analysis_id}"
            f"/investigations/{slug}"
        )

    @staticmethod
    def _serialize_card(
        card: InvestigationCard,
    ) -> dict[str, Any]:
        """
        Converte InvestigationCard para estrutura
        simples consumida pelos templates Jinja.
        """

        return {
            "slug": card.slug,
            "title": card.title,
            "status": (
                card.status.value
            ),
            "status_label": (
                card.status_label
            ),
            "summary": (
                card.summary
            ),
            "metrics": [
                {
                    "label": (
                        metric.label
                    ),
                    "value": (
                        metric.value
                    ),
                }
                for metric
                in card.metrics
            ],
            "evidence_count": (
                card.evidence_count
            ),
            "route": (
                card.route
            ),
        }

    @staticmethod
    def _normalize_slug(
        value: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "Investigation slug "
                "must be a string."
            )

        normalized = (
            value
            .strip()
            .lower()
        )

        if not normalized:
            raise ValueError(
                "Investigation slug "
                "cannot be empty."
            )

        return normalized

    @staticmethod
    def _validate_analysis_id(
        value: UUID,
    ) -> None:
        if not isinstance(
            value,
            UUID,
        ):
            raise TypeError(
                "analysis_id must "
                "be a UUID."
            )

    @staticmethod
    def _validate_analysis_view(
        value: dict[str, Any],
    ) -> None:
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "analysis_view must "
                "be a dictionary."
            )