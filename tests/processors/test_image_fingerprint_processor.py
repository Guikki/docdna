from types import SimpleNamespace

from app.processors.image_fingerprint_processor import (
    ImageFingerprintProcessor,
)


class _FakeReader:
    def read(
        self,
        source,
    ):
        return [
            SimpleNamespace(
                page_number=1,
                width=100,
                height=80,
                filename="image.png",
                image_index=1,
                xref=10,
            ),
            SimpleNamespace(
                page_number=2,
                width=120,
                height=90,
                filename="image.png",
                image_index=2,
                xref=11,
            ),
        ]


class _FakeAnalyzer:
    def __init__(self) -> None:
        self.performance_report = None
        self.calls = 0

    def analyze(
        self,
        image,
    ):
        self.calls += 1

        self.performance_report = {
            "total_seconds": 0.3,
            "stages": {
                "image_hash_sha256": {
                    "duration_seconds": 0.1,
                    "calls": 1,
                },
                "image_hash_phash": {
                    "duration_seconds": 0.2,
                    "calls": 1,
                },
            },
        }

        return object()


class _FakeBuilder:
    def build_from_analysis(
        self,
        **kwargs,
    ):
        return object()


def test_should_accumulate_internal_performance_across_images(
) -> None:
    processor = ImageFingerprintProcessor(
        reader=_FakeReader(),
        analyzer=_FakeAnalyzer(),
        builder=_FakeBuilder(),
    )

    result = processor.process(
        "document.pdf"
    )

    assert len(result) == 2

    report = (
        processor.performance_report
    )

    assert report is not None

    stages = report[
        "stages"
    ]

    assert (
        stages[
            "image_fp_extraction"
        ][
            "calls"
        ]
        == 1
    )

    assert (
        stages[
            "image_hash_sha256"
        ][
            "calls"
        ]
        == 2
    )

    assert (
        stages[
            "image_hash_sha256"
        ][
            "duration_seconds"
        ]
        == 0.2
    )

    assert (
        stages[
            "image_hash_phash"
        ][
            "calls"
        ]
        == 2
    )

    assert (
        stages[
            "image_hash_phash"
        ][
            "duration_seconds"
        ]
        == 0.4
    )

    assert (
        stages[
            "image_fp_build"
        ][
            "calls"
        ]
        == 2
    )
