from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.domain.prompt_injection.models.prompt_injection_assessment import (
    PromptInjectionAssessment,
)
from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)
from app.domain.prompt_injection.models.prompt_injection_risk_level import (
    PromptInjectionRiskLevel,
)


class PromptInjectionAssessmentBuilder:
    """
    Consolida evidências de Prompt Injection em uma avaliação única.

    O builder não executa detectores.

    Ele recebe evidências já produzidas e calcula:

    - score consolidado;
    - nível de risco;
    - resumo executivo;
    - metadados auxiliares.

    O score representa intensidade dos sinais observados,
    não confirmação de fraude ou de Prompt Injection.
    """

    LOW_THRESHOLD = 0.01
    MEDIUM_THRESHOLD = 0.30
    HIGH_THRESHOLD = 0.55
    CRITICAL_THRESHOLD = 0.80

    STRONG_CATEGORIES = {
        "instruction_override",
        "system_prompt_extraction",
        "tool_manipulation",
    }

    CATEGORY_DIVERSITY_BONUS = 0.05
    MULTIPLE_EVIDENCE_BONUS = 0.03
    STRONG_CATEGORY_BONUS = 0.08

    MAX_CATEGORY_DIVERSITY_BONUS = 0.15
    MAX_MULTIPLE_EVIDENCE_BONUS = 0.12
    MAX_STRONG_CATEGORY_BONUS = 0.16

    def build(
        self,
        evidences: Sequence[
            PromptInjectionEvidence
        ],
    ) -> PromptInjectionAssessment:
        normalized_evidences = (
            self._validate_evidences(
                evidences
            )
        )

        if not normalized_evidences:
            return PromptInjectionAssessment(
                score=0.0,
                risk_level=(
                    PromptInjectionRiskLevel.NONE
                ),
                evidences=(),
                summary=(
                    "Nenhum padrão textual associado "
                    "a possível Prompt Injection foi "
                    "identificado pelos detectores executados."
                ),
                metadata={
                    "evidence_count": 0,
                    "category_count": 0,
                    "language_count": 0,
                    "strong_category_count": 0,
                },
            )

        score = self._calculate_score(
            normalized_evidences
        )

        risk_level = (
            self._classify_risk_level(
                score
            )
        )

        categories = (
            self._collect_categories(
                normalized_evidences
            )
        )

        languages = (
            self._collect_languages(
                normalized_evidences
            )
        )

        detectors = (
            self._collect_detectors(
                normalized_evidences
            )
        )

        strong_categories = tuple(
            category
            for category in categories
            if category
            in self.STRONG_CATEGORIES
        )

        summary = self._build_summary(
            risk_level=risk_level,
            evidence_count=len(
                normalized_evidences
            ),
            category_count=len(
                categories
            ),
        )

        metadata: dict[str, Any] = {
            "evidence_count": len(
                normalized_evidences
            ),
            "category_count": len(
                categories
            ),
            "categories": categories,
            "language_count": len(
                languages
            ),
            "languages": languages,
            "detector_count": len(
                detectors
            ),
            "detectors": detectors,
            "strong_category_count": len(
                strong_categories
            ),
            "strong_categories": (
                strong_categories
            ),
            "highest_weighted_score": (
                self._highest_weighted_score(
                    normalized_evidences
                )
            ),
        }

        return PromptInjectionAssessment(
            score=score,
            risk_level=risk_level,
            evidences=normalized_evidences,
            summary=summary,
            metadata=metadata,
        )

    def _calculate_score(
        self,
        evidences: tuple[
            PromptInjectionEvidence,
            ...
        ],
    ) -> float:
        """
        Consolida os sinais sem simplesmente somá-los.

        O score parte da evidência individual mais forte e adiciona
        bônus limitados por:

        - quantidade de categorias distintas;
        - quantidade de evidências adicionais;
        - presença de categorias consideradas fortes.
        """

        highest_score = (
            self._highest_weighted_score(
                evidences
            )
        )

        categories = (
            self._collect_categories(
                evidences
            )
        )

        strong_categories = {
            category
            for category in categories
            if category
            in self.STRONG_CATEGORIES
        }

        category_bonus = min(
            max(
                0,
                len(categories) - 1,
            )
            * self.CATEGORY_DIVERSITY_BONUS,
            self.MAX_CATEGORY_DIVERSITY_BONUS,
        )

        evidence_bonus = min(
            max(
                0,
                len(evidences) - 1,
            )
            * self.MULTIPLE_EVIDENCE_BONUS,
            self.MAX_MULTIPLE_EVIDENCE_BONUS,
        )

        strong_category_bonus = min(
            len(strong_categories)
            * self.STRONG_CATEGORY_BONUS,
            self.MAX_STRONG_CATEGORY_BONUS,
        )

        score = (
            highest_score
            + category_bonus
            + evidence_bonus
            + strong_category_bonus
        )

        return round(
            min(
                1.0,
                max(
                    0.0,
                    score,
                ),
            ),
            4,
        )

    def _classify_risk_level(
        self,
        score: float,
    ) -> PromptInjectionRiskLevel:
        if score <= 0.0:
            return (
                PromptInjectionRiskLevel.NONE
            )

        if score < self.MEDIUM_THRESHOLD:
            return (
                PromptInjectionRiskLevel.LOW
            )

        if score < self.HIGH_THRESHOLD:
            return (
                PromptInjectionRiskLevel.MEDIUM
            )

        if score < self.CRITICAL_THRESHOLD:
            return (
                PromptInjectionRiskLevel.HIGH
            )

        return (
            PromptInjectionRiskLevel.CRITICAL
        )

    @staticmethod
    def _highest_weighted_score(
        evidences: tuple[
            PromptInjectionEvidence,
            ...
        ],
    ) -> float:
        if not evidences:
            return 0.0

        return max(
            evidence.weighted_score
            for evidence in evidences
        )

    @staticmethod
    def _collect_categories(
        evidences: tuple[
            PromptInjectionEvidence,
            ...
        ],
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                evidence.category
                for evidence in evidences
                if evidence.category
                is not None
            )
        )

    @staticmethod
    def _collect_languages(
        evidences: tuple[
            PromptInjectionEvidence,
            ...
        ],
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                evidence.language
                for evidence in evidences
                if evidence.language
                is not None
            )
        )

    @staticmethod
    def _collect_detectors(
        evidences: tuple[
            PromptInjectionEvidence,
            ...
        ],
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                evidence.detector
                for evidence in evidences
            )
        )

    def _build_summary(
        self,
        *,
        risk_level: PromptInjectionRiskLevel,
        evidence_count: int,
        category_count: int,
    ) -> str:
        if (
            risk_level
            == PromptInjectionRiskLevel.NONE
        ):
            return (
                "Nenhum padrão textual associado "
                "a possível Prompt Injection foi "
                "identificado pelos detectores executados."
            )

        if (
            risk_level
            == PromptInjectionRiskLevel.LOW
        ):
            return (
                f"Foram identificados {evidence_count} "
                "sinal(is) textual(is) de baixa intensidade "
                f"em {category_count} categoria(s). "
                "Os resultados devem ser interpretados "
                "no contexto do documento."
            )

        if (
            risk_level
            == PromptInjectionRiskLevel.MEDIUM
        ):
            return (
                f"Foram identificados {evidence_count} "
                "sinal(is) compatível(is) com padrões "
                "potenciais de Prompt Injection, distribuídos "
                f"em {category_count} categoria(s). "
                "Recomenda-se revisão do conteúdo identificado."
            )

        if (
            risk_level
            == PromptInjectionRiskLevel.HIGH
        ):
            return (
                f"Foram identificados {evidence_count} "
                "sinal(is) relevantes associados a possíveis "
                "tentativas de direcionamento ou manipulação "
                f"de sistemas de IA em {category_count} "
                "categoria(s). Recomenda-se revisão detalhada."
            )

        return (
            f"Foram identificados {evidence_count} "
            "sinal(is) de alta intensidade e diversidade "
            "associados a possíveis tentativas de Prompt "
            f"Injection em {category_count} categoria(s). "
            "A análise detalhada das evidências é fortemente "
            "recomendada."
        )

    @staticmethod
    def _validate_evidences(
        evidences: Sequence[
            PromptInjectionEvidence
        ],
    ) -> tuple[
        PromptInjectionEvidence,
        ...
    ]:
        if isinstance(
            evidences,
            (str, bytes),
        ):
            raise TypeError(
                "PromptInjectionAssessmentBuilder "
                "evidences must be a sequence of "
                "PromptInjectionEvidence instances."
            )

        if not isinstance(
            evidences,
            Sequence,
        ):
            raise TypeError(
                "PromptInjectionAssessmentBuilder "
                "evidences must be a sequence."
            )

        normalized = tuple(
            evidences
        )

        for index, evidence in enumerate(
            normalized
        ):
            if not isinstance(
                evidence,
                PromptInjectionEvidence,
            ):
                raise TypeError(
                    "PromptInjectionAssessmentBuilder "
                    "evidences must contain only "
                    "PromptInjectionEvidence instances. "
                    f"Invalid item at index {index}."
                )

        return normalized