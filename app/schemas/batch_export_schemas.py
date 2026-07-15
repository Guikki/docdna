from pydantic import BaseModel


class BatchExportResponse(BaseModel):
    batch_id: str
    filename: str
    file_path: str
    download_url: str
    total_documents: int
    exported_documents: int
    exported_evidences: int
    message: str