from __future__ import annotations

import pytest

from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)
from app.domain.prompt_injection.models.prompt_injection_risk_level import (
    PromptInjectionRiskLevel,
)
from app.domain.prompt_injection.services.prompt_injection_assessment_builder import (
    PromptInjectionAssessmentBuilder,
)


def _evidence(
    *,
    category: str = "ai_targeting",
    confidence: float = 0.80,
    weight: float = 0.50,
    language: str = "pt-BR",
    detector: str = "prompt_phrase_detector",
    code: str = "PROMPT_INJECTION_TEST",
) -> PromptInjectionEvidence:
    return PromptInjectionEvidence(
        code=code,
        detector=detector,
        description=(
            "Padrão textual potencialmente associado "
            "a Prompt Injection."
        ),
        confidence=confidence,
        weight=weight,
        language=language,
        category=category,
    )


def test_should_build_none_assessment_when_no_evidences() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        []
    )

    assert assessment.score == 0.0

    assert (
        assessment.risk_level
        == PromptInjectionRiskLevel.NONE
    )

    assert assessment.evidences == ()

    assert assessment.evidence_count == 0

    assert assessment.has_evidences is False

    assert assessment.summary is not None

    assert (
        "Nenhum padrão textual"
        in assessment.summary
    )


def test_should_include_empty_metadata_when_no_evidences() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        []
    )

    assert (
        assessment.metadata[
            "evidence_count"
        ]
        == 0
    )

    assert (
        assessment.metadata[
            "category_count"
        ]
        == 0
    )

    assert (
        assessment.metadata[
            "language_count"
        ]
        == 0
    )

    assert (
        assessment.metadata[
            "strong_category_count"
        ]
        == 0
    )


def test_should_use_highest_weighted_score_as_base() -> None:
    builder = PromptInjectionAssessmentBuilder()

    evidences = [
        _evidence(
            confidence=0.50,
            weight=0.50,
        ),
    ]

    assessment = builder.build(
        evidences
    )

    assert assessment.score == 0.25


def test_should_classify_low_risk() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                confidence=0.40,
                weight=0.50,
            ),
        ]
    )

    assert assessment.score == 0.20

    assert (
        assessment.risk_level
        == PromptInjectionRiskLevel.LOW
    )


def test_should_classify_medium_risk() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                confidence=0.80,
                weight=0.50,
            ),
        ]
    )

    assert assessment.score == 0.40

    assert (
        assessment.risk_level
        == PromptInjectionRiskLevel.MEDIUM
    )


def test_should_classify_high_risk() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                confidence=0.80,
                weight=0.75,
            ),
        ]
    )

    assert assessment.score == 0.60

    assert (
        assessment.risk_level
        == PromptInjectionRiskLevel.HIGH
    )


def test_should_classify_critical_risk() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                category=(
                    "system_prompt_extraction"
                ),
                confidence=0.90,
                weight=0.90,
            ),
        ]
    )

    assert assessment.score >= 0.80

    assert (
        assessment.risk_level
        == PromptInjectionRiskLevel.CRITICAL
    )


def test_should_add_category_diversity_bonus() -> None:
    builder = PromptInjectionAssessmentBuilder()

    evidences = [
        _evidence(
            category="ai_targeting",
            confidence=0.60,
            weight=0.50,
            code="AI_TARGETING",
        ),
        _evidence(
            category="response_control",
            confidence=0.60,
            weight=0.50,
            code="RESPONSE_CONTROL",
        ),
    ]

    assessment = builder.build(
        evidences
    )

    highest_individual_score = 0.30

    assert (
        assessment.score
        > highest_individual_score
    )


def test_should_add_multiple_evidence_bonus() -> None:
    builder = PromptInjectionAssessmentBuilder()

    evidences = [
        _evidence(
            category="ai_targeting",
            confidence=0.50,
            weight=0.50,
            code="TEST_1",
        ),
        _evidence(
            category="ai_targeting",
            confidence=0.50,
            weight=0.50,
            code="TEST_2",
        ),
    ]

    assessment = builder.build(
        evidences
    )

    assert assessment.score > 0.25


def test_should_add_strong_category_bonus() -> None:
    builder = PromptInjectionAssessmentBuilder()

    ordinary = builder.build(
        [
            _evidence(
                category="ai_targeting",
                confidence=0.50,
                weight=0.50,
            )
        ]
    )

    strong = builder.build(
        [
            _evidence(
                category=(
                    "instruction_override"
                ),
                confidence=0.50,
                weight=0.50,
            )
        ]
    )

    assert (
        strong.score
        > ordinary.score
    )


def test_should_recognize_all_strong_categories() -> None:
    builder = PromptInjectionAssessmentBuilder()

    expected = {
        "instruction_override",
        "system_prompt_extraction",
        "tool_manipulation",
    }

    assert (
        builder.STRONG_CATEGORIES
        == expected
    )


def test_should_limit_score_to_one() -> None:
    builder = PromptInjectionAssessmentBuilder()

    evidences = [
        _evidence(
            category=(
                "instruction_override"
            ),
            confidence=1.0,
            weight=1.0,
            code="STRONG_1",
        ),
        _evidence(
            category=(
                "system_prompt_extraction"
            ),
            confidence=1.0,
            weight=1.0,
            code="STRONG_2",
        ),
        _evidence(
            category="tool_manipulation",
            confidence=1.0,
            weight=1.0,
            code="STRONG_3",
        ),
        _evidence(
            category="role_manipulation",
            confidence=1.0,
            weight=1.0,
            code="STRONG_4",
        ),
    ]

    assessment = builder.build(
        evidences
    )

    assert assessment.score == 1.0


def test_should_preserve_evidences() -> None:
    builder = PromptInjectionAssessmentBuilder()

    first = _evidence(
        code="FIRST"
    )

    second = _evidence(
        code="SECOND"
    )

    assessment = builder.build(
        [
            first,
            second,
        ]
    )

    assert assessment.evidences == (
        first,
        second,
    )


def test_should_collect_unique_categories() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                category="ai_targeting",
                code="FIRST",
            ),
            _evidence(
                category="ai_targeting",
                code="SECOND",
            ),
            _evidence(
                category="response_control",
                code="THIRD",
            ),
        ]
    )

    assert (
        assessment.metadata[
            "categories"
        ]
        == (
            "ai_targeting",
            "response_control",
        )
    )

    assert (
        assessment.metadata[
            "category_count"
        ]
        == 2
    )


def test_should_collect_unique_languages() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                language="pt-BR",
                code="FIRST",
            ),
            _evidence(
                language="pt-BR",
                code="SECOND",
            ),
            _evidence(
                language="en",
                code="THIRD",
            ),
        ]
    )

    assert (
        assessment.metadata[
            "languages"
        ]
        == (
            "pt-BR",
            "en",
        )
    )

    assert (
        assessment.metadata[
            "language_count"
        ]
        == 2
    )


def test_should_collect_unique_detectors() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                detector=(
                    "prompt_phrase_detector"
                ),
                code="FIRST",
            ),
            _evidence(
                detector=(
                    "prompt_phrase_detector"
                ),
                code="SECOND",
            ),
            _evidence(
                detector="another_detector",
                code="THIRD",
            ),
        ]
    )

    assert (
        assessment.metadata[
            "detectors"
        ]
        == (
            "prompt_phrase_detector",
            "another_detector",
        )
    )

    assert (
        assessment.metadata[
            "detector_count"
        ]
        == 2
    )


def test_should_collect_strong_categories() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                category="ai_targeting",
                code="FIRST",
            ),
            _evidence(
                category=(
                    "instruction_override"
                ),
                code="SECOND",
            ),
            _evidence(
                category=(
                    "system_prompt_extraction"
                ),
                code="THIRD",
            ),
        ]
    )

    assert (
        assessment.metadata[
            "strong_categories"
        ]
        == (
            "instruction_override",
            "system_prompt_extraction",
        )
    )

    assert (
        assessment.metadata[
            "strong_category_count"
        ]
        == 2
    )


def test_should_include_highest_weighted_score_in_metadata() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                confidence=0.40,
                weight=0.50,
                code="FIRST",
            ),
            _evidence(
                confidence=0.80,
                weight=0.75,
                code="SECOND",
            ),
        ]
    )

    assert (
        assessment.metadata[
            "highest_weighted_score"
        ]
        == pytest.approx(0.60)
    )


def test_should_build_low_summary() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                confidence=0.20,
                weight=0.50,
            )
        ]
    )

    assert (
        assessment.risk_level
        == PromptInjectionRiskLevel.LOW
    )

    assert assessment.summary is not None

    assert (
        "baixa intensidade"
        in assessment.summary
    )


def test_should_build_medium_summary() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                confidence=0.80,
                weight=0.50,
            )
        ]
    )

    assert (
        assessment.risk_level
        == PromptInjectionRiskLevel.MEDIUM
    )

    assert assessment.summary is not None

    assert (
        "potenciais de Prompt Injection"
        in assessment.summary
    )


def test_should_build_high_summary() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                confidence=0.80,
                weight=0.75,
            )
        ]
    )

    assert (
        assessment.risk_level
        == PromptInjectionRiskLevel.HIGH
    )

    assert assessment.summary is not None

    assert (
        "direcionamento ou manipulação"
        in assessment.summary
    )


def test_should_build_critical_summary() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                category=(
                    "system_prompt_extraction"
                ),
                confidence=1.0,
                weight=1.0,
            )
        ]
    )

    assert (
        assessment.risk_level
        == PromptInjectionRiskLevel.CRITICAL
    )

    assert assessment.summary is not None

    assert (
        "alta intensidade"
        in assessment.summary
    )


def test_should_accept_tuple_of_evidences() -> None:
    builder = PromptInjectionAssessmentBuilder()

    evidence = _evidence()

    assessment = builder.build(
        (
            evidence,
        )
    )

    assert (
        assessment.evidences
        == (
            evidence,
        )
    )


def test_should_reject_string_as_evidence_sequence() -> None:
    builder = PromptInjectionAssessmentBuilder()

    with pytest.raises(
        TypeError
    ):
        builder.build(
            "invalid"  # type: ignore[arg-type]
        )


def test_should_reject_bytes_as_evidence_sequence() -> None:
    builder = PromptInjectionAssessmentBuilder()

    with pytest.raises(
        TypeError
    ):
        builder.build(
            b"invalid"  # type: ignore[arg-type]
        )


def test_should_reject_non_sequence() -> None:
    builder = PromptInjectionAssessmentBuilder()

    with pytest.raises(
        TypeError
    ):
        builder.build(
            123  # type: ignore[arg-type]
        )


def test_should_reject_invalid_evidence_item() -> None:
    builder = PromptInjectionAssessmentBuilder()

    with pytest.raises(
        TypeError,
        match="Invalid item at index 1",
    ):
        builder.build(
            [
                _evidence(),
                "invalid",  # type: ignore[list-item]
            ]
        )


def test_should_keep_score_inside_valid_range() -> None:
    builder = PromptInjectionAssessmentBuilder()

    assessment = builder.build(
        [
            _evidence(
                category=(
                    "instruction_override"
                ),
                confidence=1.0,
                weight=1.0,
                code="FIRST",
            ),
            _evidence(
                category=(
                    "system_prompt_extraction"
                ),
                confidence=1.0,
                weight=1.0,
                code="SECOND",
            ),
            _evidence(
                category=(
                    "tool_manipulation"
                ),
                confidence=1.0,
                weight=1.0,
                code="THIRD",
            ),
        ]
    )

    assert (
        0.0
        <= assessment.score
        <= 1.0
    )


@pytest.mark.parametrize(
    "score,expected",
    [
        (
            0.0,
            PromptInjectionRiskLevel.NONE,
        ),
        (
            0.01,
            PromptInjectionRiskLevel.LOW,
        ),
        (
            0.29,
            PromptInjectionRiskLevel.LOW,
        ),
        (
            0.30,
            PromptInjectionRiskLevel.MEDIUM,
        ),
        (
            0.54,
            PromptInjectionRiskLevel.MEDIUM,
        ),
        (
            0.55,
            PromptInjectionRiskLevel.HIGH,
        ),
        (
            0.79,
            PromptInjectionRiskLevel.HIGH,
        ),
        (
            0.80,
            PromptInjectionRiskLevel.CRITICAL,
        ),
        (
            1.0,
            PromptInjectionRiskLevel.CRITICAL,
        ),
    ],
)
def test_should_classify_boundary_values(
    score: float,
    expected: PromptInjectionRiskLevel,
) -> None:
    builder = PromptInjectionAssessmentBuilder()

    result = (
        builder._classify_risk_level(
            score
        )
    )

    assert result == expected