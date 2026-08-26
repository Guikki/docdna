import pytest

from app.frontend.investigations.models.investigation_status import (
    InvestigationStatus,
)
from app.frontend.investigations.services.investigation_status_resolver import (
    InvestigationStatusResolver,
)


def test_empty_cards_should_return_not_executed():
    resolver = InvestigationStatusResolver()

    status = resolver.resolve([])

    assert (
        status
        == InvestigationStatus.NOT_EXECUTED
    )


def test_alert_should_have_highest_priority():
    resolver = InvestigationStatusResolver()

    cards = [
        {"status": "clear"},
        {"status": "attention"},
        {"status": "alert"},
        {"status": "not_executed"},
    ]

    status = resolver.resolve(
        cards
    )

    assert (
        status
        == InvestigationStatus.ALERT
    )


def test_attention_should_win_when_alert_is_absent():
    resolver = InvestigationStatusResolver()

    cards = [
        {"status": "clear"},
        {"status": "attention"},
        {"status": "not_executed"},
    ]

    status = resolver.resolve(
        cards
    )

    assert (
        status
        == InvestigationStatus.ATTENTION
    )


def test_clear_should_win_when_only_clear_and_not_executed_exist():
    resolver = InvestigationStatusResolver()

    cards = [
        {"status": "not_executed"},
        {"status": "clear"},
    ]

    status = resolver.resolve(
        cards
    )

    assert (
        status
        == InvestigationStatus.CLEAR
    )


def test_only_not_executed_should_return_not_executed():
    resolver = InvestigationStatusResolver()

    cards = [
        {"status": "not_executed"},
        {"status": "not_executed"},
    ]

    status = resolver.resolve(
        cards
    )

    assert (
        status
        == InvestigationStatus.NOT_EXECUTED
    )


def test_resolve_statuses_should_use_same_priority():
    resolver = InvestigationStatusResolver()

    status = resolver.resolve_statuses(
        [
            InvestigationStatus.CLEAR,
            InvestigationStatus.ALERT,
            InvestigationStatus.ATTENTION,
        ]
    )

    assert (
        status
        == InvestigationStatus.ALERT
    )


@pytest.mark.parametrize(
    (
        "status",
        "expected_label",
    ),
    [
        (
            InvestigationStatus.ALERT,
            "Alta prioridade",
        ),
        (
            InvestigationStatus.ATTENTION,
            "Revisão recomendada",
        ),
        (
            InvestigationStatus.CLEAR,
            "Sem apontamentos",
        ),
        (
            InvestigationStatus.NOT_EXECUTED,
            "Análise incompleta",
        ),
    ],
)
def test_should_return_status_label(
    status,
    expected_label,
):
    resolver = InvestigationStatusResolver()

    assert (
        resolver.label(status)
        == expected_label
    )


def test_unknown_serialized_status_should_raise_error():
    resolver = InvestigationStatusResolver()

    with pytest.raises(
        ValueError,
        match="Unknown investigation status",
    ):
        resolver.resolve(
            [
                {
                    "status": (
                        "something_unknown"
                    )
                }
            ]
        )