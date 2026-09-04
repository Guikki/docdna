from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.frontend.investigations.builders.investigation_view_builder import (
    InvestigationViewBuilder,
)
from app.frontend.view_models.analysis_view_builder import AnalysisViewBuilder


def _low_contrast_finding() -> SimpleNamespace:
    return SimpleNamespace(
        code="low_contrast_text",
        detector="low_contrast_text_detector",
        page_number=2,
        text="Trecho praticamente invisível.",
        bounding_box=SimpleNamespace(
            left=100.0,
            top=200.0,
            width=240.0,
            height=14.0,
        ),
        font_name="Helvetica",
        font_size=8.0,
        font_color_hex="#F7F7F7",
        confidence=0.98,
        signals=(
            "low_contrast",
            "background_color_estimated",
            "extreme_low_contrast",
            "high_background_dominance",
        ),
        is_near_white=True,
        is_small_text=False,
        is_relative_small_text=False,
        is_instruction_like=False,
        background_color_hex="#FFFFFF",
        font_relative_luminance=0.93011,
        background_relative_luminance=1.0,
        contrast_ratio=1.0714,
        contrast_threshold=2.0,
        contrast_level="extreme_low_contrast",
        background_sampling_method="dominant_quantized_bbox_color",
        background_dominance_ratio=0.91,
        is_low_contrast=True,
        is_extreme_low_contrast=True,
    )


def test_analysis_view_should_expose_low_contrast_technical_data() -> None:
    analysis = SimpleNamespace(
        white_text_findings=(),
        low_contrast_text_findings=(
            _low_contrast_finding(),
        ),
        tiny_text_evidences=(),
        has_findings=True,
        total_findings=1,
        white_text_count=0,
        low_contrast_text_count=1,
        tiny_text_count=0,
        highest_confidence=0.98,
    )

    result = (
        AnalysisViewBuilder()
        ._build_visual_concealment_analysis(
            analysis
        )
    )

    assert result["low_contrast_text_count"] == 1
    assert result["total_findings"] == 1

    finding = result[
        "low_contrast_text_findings"
    ][0]

    assert finding["code"] == "low_contrast_text"
    assert finding["background_color_hex"] == "#FFFFFF"
    assert finding["contrast_ratio"] == pytest.approx(1.0714)
    assert finding["contrast_ratio_label"] == "1.07:1"
    assert finding["contrast_threshold_label"] == "2.00:1"
    assert (
        finding["contrast_level_label"]
        == "Contraste extremamente baixo"
    )
    assert finding["background_dominance_label"] == "91.0%"
    assert finding["is_low_contrast"] is True
    assert finding["is_extreme_low_contrast"] is True
    assert (
        "Contraste inferior ao limiar técnico do DocDNA"
        in finding["signal_labels"]
    )


def test_ai_security_card_should_describe_low_contrast_findings() -> None:
    card = (
        InvestigationViewBuilder()
        ._build_ai_security_card(
            analysis_id=uuid4(),
            analysis={
                "has_prompt_injection_assessment": True,
                "prompt_injection_risk_level": "none",
                "prompt_injection_risk_label": "Nenhum",
                "prompt_injection_score_label": "0.0%",
                "prompt_injection_evidence_count": 0,
                "located_prompt_injection_count": 0,
                "prompt_injection_summary": "",
                "visual_concealment_total_count": 2,
                "visual_concealment_white_text_count": 0,
                "visual_concealment_low_contrast_text_count": 2,
                "visual_concealment_tiny_text_count": 0,
                "has_visual_concealment_findings": True,
            },
        )
    )

    metrics = {
        metric.label: metric.value
        for metric in card.metrics
    }

    assert card.status.value == "attention"
    assert "baixo contraste" in card.summary
    assert (
        metrics["Ocultação visual"]
        == "2 (0 branco/quase branco, 2 baixo contraste)"
    )
