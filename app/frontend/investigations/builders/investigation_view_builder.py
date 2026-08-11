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

        return [
            self._serialize_card(
                card
            )
            for card
            in cards
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

        return {
            "analysis": (
                analysis_view
            ),
            "investigation": (
                investigation
            ),
            "slug": (
                normalized_slug
            ),
            "back_url": (
                f"/analyses/{analysis_id}"
            ),
        }

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

        Neste momento, o verificador efetivamente executado
        é o detector textual de Prompt Injection.

        Os verificadores visuais de ocultação serão
        incorporados posteriormente.
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

        evidence_count = int(
            analysis.get(
                "prompt_injection_evidence_count",
                0,
            )
        )

        category_count = int(
            analysis.get(
                "prompt_injection_category_count",
                0,
            )
        )

        assessment_summary = str(
            analysis.get(
                "prompt_injection_summary",
                "",
            )
        ).strip()

        if not has_assessment:
            status = (
                InvestigationStatus.NOT_EXECUTED
            )

            status_label = (
                "Verificação não disponível"
            )

            summary = (
                "O verificador textual de segurança para "
                "sistemas de IA não foi disponibilizado "
                "nesta execução."
            )

        elif risk_level == "none":
            status = (
                InvestigationStatus.CLEAR
            )

            status_label = (
                "Nenhum padrão suspeito"
            )

            summary = (
                assessment_summary
                or (
                    "Nenhum padrão textual associado "
                    "a possível Prompt Injection foi "
                    "identificado pelos verificadores "
                    "executados."
                )
            )

        elif risk_level == "low":
            status = (
                InvestigationStatus.ATTENTION
            )

            status_label = (
                "Sinal de baixa intensidade"
            )

            summary = (
                assessment_summary
                or (
                    "Foi identificado sinal textual de "
                    "baixa intensidade associado a padrões "
                    "potenciais de Prompt Injection. "
                    "Recomenda-se revisão contextual."
                )
            )

        elif risk_level == "medium":
            status = (
                InvestigationStatus.ATTENTION
            )

            status_label = (
                "Revisão recomendada"
            )

            summary = (
                assessment_summary
                or (
                    "Foram identificados padrões textuais "
                    "compatíveis com possível Prompt Injection. "
                    "Recomenda-se revisão das evidências."
                )
            )

        elif risk_level in {
            "high",
            "critical",
        }:
            status = (
                InvestigationStatus.ALERT
            )

            status_label = (
                "Atenção prioritária"
            )

            summary = (
                assessment_summary
                or (
                    "Foram identificados sinais relevantes "
                    "associados a possível tentativa de "
                    "direcionamento ou manipulação de "
                    "sistemas de IA."
                )
            )

        else:
            status = (
                InvestigationStatus.ATTENTION
            )

            status_label = (
                "Resultado para revisão"
            )

            summary = (
                assessment_summary
                or (
                    "O verificador de segurança para IA "
                    "produziu resultado que requer revisão."
                )
            )

        return InvestigationCard(
            slug="ai-security",
            title="IA e segurança",
            status=status,
            status_label=status_label,
            summary=summary,
            metrics=(
                InvestigationMetric(
                    label=(
                        "Risco textual"
                    ),
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
                    label=(
                        "Sinais identificados"
                    ),
                    value=str(
                        evidence_count
                    ),
                ),
                InvestigationMetric(
                    label="Categorias",
                    value=str(
                        category_count
                    ),
                ),
            ),
            evidence_count=(
                evidence_count
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