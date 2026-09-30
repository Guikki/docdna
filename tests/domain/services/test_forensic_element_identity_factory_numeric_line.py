from uuid import uuid4

import pytest

from app.domain.services.forensic_element_identity_factory import (
    ForensicElementIdentityFactory,
)


def test_numeric_line_identity_should_be_deterministic() -> None:
    document_id = uuid4()

    first = (
        ForensicElementIdentityFactory
        .numeric_line(
            document_id=document_id,
            line_index=1,
        )
    )

    second = (
        ForensicElementIdentityFactory
        .numeric_line(
            document_id=document_id,
            line_index=1,
        )
    )

    assert first == second


def test_different_numeric_line_indexes_should_have_different_ids(
) -> None:
    document_id = uuid4()

    first = (
        ForensicElementIdentityFactory
        .numeric_line(
            document_id=document_id,
            line_index=1,
        )
    )

    second = (
        ForensicElementIdentityFactory
        .numeric_line(
            document_id=document_id,
            line_index=2,
        )
    )

    assert first != second


def test_raw_and_normalized_line_should_have_different_ids(
) -> None:
    document_id = uuid4()

    raw = (
        ForensicElementIdentityFactory
        .numeric_line(
            document_id=document_id,
            line_index=1,
        )
    )

    normalized = (
        ForensicElementIdentityFactory
        .normalized_numeric_line(
            document_id=document_id,
            line_index=1,
        )
    )

    assert raw != normalized


def test_normalized_line_and_validation_should_have_different_ids(
) -> None:
    document_id = uuid4()

    normalized = (
        ForensicElementIdentityFactory
        .normalized_numeric_line(
            document_id=document_id,
            line_index=1,
        )
    )

    validation = (
        ForensicElementIdentityFactory
        .numeric_line_validation(
            document_id=document_id,
            line_index=1,
        )
    )

    assert normalized != validation


@pytest.mark.parametrize(
    "line_index",
    [
        0,
        -1,
        -10,
    ],
)
def test_numeric_line_should_reject_non_positive_index(
    line_index: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="maior ou igual a um",
    ):
        (
            ForensicElementIdentityFactory
            .numeric_line(
                document_id=uuid4(),
                line_index=line_index,
            )
        )


def test_numeric_line_should_reject_boolean_index() -> None:
    with pytest.raises(
        TypeError,
        match="inteiro",
    ):
        (
            ForensicElementIdentityFactory
            .numeric_line(
                document_id=uuid4(),
                line_index=True,  # type: ignore[arg-type]
            )
        )