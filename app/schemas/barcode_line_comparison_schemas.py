from pydantic import BaseModel


class BarcodeLineComparisonResponse(BaseModel):
    line_index: int
    barcode_index: int | None
    line_type: str
    printed_numeric_line: str
    converted_barcode: str | None
    detected_barcode: str | None
    status: str
    message: str
