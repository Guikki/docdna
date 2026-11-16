import pytest
from openpyxl import Workbook

from app.domain.services.batch_excel_export_service import BatchExcelExportService
from app.frontend.exports.batch_export_view_builder import BatchExportViewBuilder


@pytest.mark.parametrize("confidence,expected", [
    (42.25, 0.4225), (90.5, 0.905), (1.0, 0.01), (0.5, 0.005),
    (0.0, 0.0), (100.0, 1.0), (None, None),
])
def test_numeric_location_exports_ocr_percentage_as_excel_ratio(confidence, expected):
    locations = BatchExportViewBuilder()._build_locations([{
        "id": "analysis-test", "filename": "document.pdf",
        "numeric_line_locations": [{"confidence": confidence, "located": True}],
    }])
    sheet = Workbook().active
    BatchExcelExportService()._build_locations_sheet(sheet, {"locations": locations})
    assert sheet.cell(2, 13).value == expected
    if expected is not None:
        assert sheet.cell(2, 13).number_format == "0.0%"
    assert locations[0]["confidence"] == confidence


def test_visual_concealment_confidence_remains_a_ratio():
    sheet = Workbook().active
    BatchExcelExportService()._build_locations_sheet(sheet, {"locations": [{
        "location_type": "visual_concealment", "confidence": 0.92,
    }]})
    assert sheet.cell(2, 13).value == 0.92
