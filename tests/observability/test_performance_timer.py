import pytest

from app.observability.performance_timer import (
    PerformanceTimer,
)


class FakeClock:

    def __init__(
        self,
    ) -> None:
        self.current = 0.0

    def __call__(
        self,
    ) -> float:
        return self.current

    def advance(
        self,
        seconds: float,
    ) -> None:
        self.current += seconds


def test_should_measure_stage_duration() -> None:
    clock = FakeClock()

    timer = PerformanceTimer(
        clock=clock
    )

    with timer.measure(
        "ocr"
    ):
        clock.advance(
            1.25
        )

    report = timer.report()

    stage = report.get_stage(
        "ocr"
    )

    assert stage is not None

    assert (
        stage.duration_seconds
        == pytest.approx(
            1.25
        )
    )

    assert stage.calls == 1


def test_should_accumulate_repeated_stage() -> None:
    clock = FakeClock()

    timer = PerformanceTimer(
        clock=clock
    )

    with timer.measure(
        "ocr"
    ):
        clock.advance(
            1.0
        )

    with timer.measure(
        "ocr"
    ):
        clock.advance(
            2.0
        )

    stage = (
        timer.report()
        .get_stage(
            "ocr"
        )
    )

    assert stage is not None

    assert (
        stage.duration_seconds
        == pytest.approx(
            3.0
        )
    )

    assert stage.calls == 2

    assert (
        stage.average_seconds
        == pytest.approx(
            1.5
        )
    )


def test_should_record_stage_when_operation_fails() -> None:
    clock = FakeClock()

    timer = PerformanceTimer(
        clock=clock
    )

    with pytest.raises(
        RuntimeError
    ):
        with timer.measure(
            "failing_stage"
        ):
            clock.advance(
                0.75
            )

            raise RuntimeError(
                "falha controlada"
            )

    stage = (
        timer.report()
        .get_stage(
            "failing_stage"
        )
    )

    assert stage is not None

    assert (
        stage.duration_seconds
        == pytest.approx(
            0.75
        )
    )

    assert stage.calls == 1


def test_should_reject_empty_stage_name() -> None:
    clock = FakeClock()

    timer = PerformanceTimer(
        clock=clock
    )

    invalid_names = [
        "",
        "   ",
        None,
    ]

    for invalid_name in invalid_names:
        with pytest.raises(
            ValueError
        ):
            with timer.measure(
                invalid_name
            ):
                pass


def test_total_should_include_unmeasured_time() -> None:
    clock = FakeClock()

    timer = PerformanceTimer(
        clock=clock
    )

    clock.advance(
        1.0
    )

    with timer.measure(
        "ocr"
    ):
        clock.advance(
            2.0
        )

    clock.advance(
        1.0
    )

    report = timer.report()

    assert (
        report.total_seconds
        == pytest.approx(
            4.0
        )
    )

    stage = report.get_stage(
        "ocr"
    )

    assert stage is not None

    assert (
        stage.percentage_of(
            report.total_seconds
        )
        == pytest.approx(
            50.0
        )
    )


def test_should_export_report_as_dictionary() -> None:
    clock = FakeClock()

    timer = PerformanceTimer(
        clock=clock
    )

    with timer.measure(
        "pdf_reader"
    ):
        clock.advance(
            0.5
        )

    with timer.measure(
        "ocr"
    ):
        clock.advance(
            1.5
        )

    exported = (
        timer.to_dict()
    )

    assert (
        exported[
            "total_seconds"
        ]
        == 2.0
    )

    assert list(
        exported[
            "stages"
        ].keys()
    ) == [
        "pdf_reader",
        "ocr",
    ]

    assert (
        exported[
            "stages"
        ][
            "pdf_reader"
        ][
            "calls"
        ]
        == 1
    )

    assert (
        exported[
            "stages"
        ][
            "ocr"
        ][
            "duration_seconds"
        ]
        == 1.5
    )

    assert (
        exported[
            "stages"
        ][
            "ocr"
        ][
            "percentage_of_total"
        ]
        == 75.0
    )