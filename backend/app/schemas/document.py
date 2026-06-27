from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime

class DocumentVersionResponse(BaseModel):
    id: uuid.UUID
    version: int
    file_size: int
    mime_type: str
    page_count: int
    chunk_count: int
    error_message: Optional[str] = None
    created_at: datetime
    created_by: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    department_id: uuid.UUID
    owner_id: Optional[uuid.UUID] = None
    current_version: int
    status: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentResponseWithRelations(DocumentResponse):
    versions: List[DocumentVersionResponse] = []

    model_config = ConfigDict(from_attributes=True)
