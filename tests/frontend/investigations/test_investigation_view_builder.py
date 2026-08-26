from app.frontend.investigations.builders.investigation_view_builder import (
    InvestigationViewBuilder,
)
from app.frontend.investigations.models.investigation_card import (
    InvestigationCard,
)
from app.frontend.investigations.models.investigation_metric import (
    InvestigationMetric,
)
from app.frontend.investigations.models.investigation_status import (
    InvestigationStatus,
)


def _card(
    *,
    slug: str,
    status: InvestigationStatus,
) -> InvestigationCard:
    return InvestigationCard(
        slug=slug,
        title=slug.replace(
            "-",
            " ",
        ).title(),
        status=status,
        status_label=(
            status.value
        ),
        summary=(
            "Resumo de teste."
        ),
        metrics=(
            InvestigationMetric(
                label="Teste",
                value="1",
            ),
        ),
        evidence_count=0,
        route=(
            f"/analyses/test/"
            f"investigations/{slug}"
        ),
    )


def test_should_sort_cards_by_analytical_priority():
    builder = (
        InvestigationViewBuilder()
    )

    cards = (
        _card(
            slug="identity",
            status=(
                InvestigationStatus.CLEAR
            ),
        ),
        _card(
            slug="structure",
            status=(
                InvestigationStatus.NOT_EXECUTED
            ),
        ),
        _card(
            slug="content",
            status=(
                InvestigationStatus.ATTENTION
            ),
        ),
        _card(
            slug="financial",
            status=(
                InvestigationStatus.ALERT
            ),
        ),
    )

    ordered = (
        builder._sort_cards_by_status(
            cards
        )
    )

    statuses = [
        card.status
        for card in ordered
    ]

    assert statuses == [
        InvestigationStatus.ALERT,
        InvestigationStatus.ATTENTION,
        InvestigationStatus.CLEAR,
        InvestigationStatus.NOT_EXECUTED,
    ]


def test_should_preserve_original_order_when_status_is_equal():
    builder = (
        InvestigationViewBuilder()
    )

    cards = (
        _card(
            slug="content",
            status=(
                InvestigationStatus.ATTENTION
            ),
        ),
        _card(
            slug="financial",
            status=(
                InvestigationStatus.ATTENTION
            ),
        ),
        _card(
            slug="ai-security",
            status=(
                InvestigationStatus.ATTENTION
            ),
        ),
    )

    ordered = (
        builder._sort_cards_by_status(
            cards
        )
    )

    slugs = [
        card.slug
        for card in ordered
    ]

    assert slugs == [
        "content",
        "financial",
        "ai-security",
    ]


def test_alert_should_come_before_clear_even_when_created_later():
    builder = (
        InvestigationViewBuilder()
    )

    cards = (
        _card(
            slug="identity",
            status=(
                InvestigationStatus.CLEAR
            ),
        ),
        _card(
            slug="structure",
            status=(
                InvestigationStatus.CLEAR
            ),
        ),
        _card(
            slug="ai-security",
            status=(
                InvestigationStatus.ALERT
            ),
        ),
    )

    ordered = (
        builder._sort_cards_by_status(
            cards
        )
    )

    assert (
        ordered[0].slug
        == "ai-security"
    )

    assert (
        ordered[1].slug
        == "identity"
    )

    assert (
        ordered[2].slug
        == "structure"
    )


def test_attention_should_come_before_clear_and_not_executed():
    builder = (
        InvestigationViewBuilder()
    )

    cards = (
        _card(
            slug="visual",
            status=(
                InvestigationStatus.NOT_EXECUTED
            ),
        ),
        _card(
            slug="identity",
            status=(
                InvestigationStatus.CLEAR
            ),
        ),
        _card(
            slug="content",
            status=(
                InvestigationStatus.ATTENTION
            ),
        ),
    )

    ordered = (
        builder._sort_cards_by_status(
            cards
        )
    )

    assert [
        card.slug
        for card in ordered
    ] == [
        "content",
        "identity",
        "visual",
    ]


def test_empty_tuple_should_remain_empty():
    builder = (
        InvestigationViewBuilder()
    )

    ordered = (
        builder._sort_cards_by_status(
            ()
        )
    )

    assert ordered == ()