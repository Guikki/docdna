from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from app.services.image_hash_analyzer import (
    ImageHashAnalyzer,
)


def test_should_report_internal_hash_stages(
    tmp_path,
) -> None:
    image_path = Path(
        tmp_path
    ) / "sample.png"

    Image.new(
        "RGB",
        (32, 32),
        "white",
    ).save(
        image_path
    )

    document_image = SimpleNamespace(
        saved_path=str(
            image_path
        )
    )

    analyzer = ImageHashAnalyzer()

    analyzer.analyze(
        document_image
    )

    report = (
        analyzer.performance_report
    )

    assert report is not None

    assert list(
        report[
            "stages"
        ].keys()
    ) == [
        "image_hash_validate_path",
        "image_hash_sha256",
        "image_hash_open_convert",
        "image_hash_phash",
        "image_hash_average_hash",
        "image_hash_difference_hash",
    ]

    assert all(
        stage[
            "calls"
        ] == 1
        for stage
        in report[
            "stages"
        ].values()
    )
