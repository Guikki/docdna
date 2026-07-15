from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.shared.enums import DocumentStatus


@dataclass
class Document:
    id: UUID
    original_filename: str
    stored_filename: str
    saved_path: str
    extension: str
    mime_type: str
    size_bytes: int
    sha256: str
    uploaded_at: datetime
    status: DocumentStatus