from pydantic import BaseModel


class BarcodeResponse(BaseModel):
    barcode_index: int
    page_number: int
    format: str
    content: str