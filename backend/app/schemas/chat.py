from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

class MessageResponse(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    role: str # user or assistant
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    confidence_score: Optional[float] = None
    related_questions: Optional[List[str]] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatBase(BaseModel):
    title: str = Field(..., max_length=255)
    department_id: Optional[uuid.UUID] = None

class ChatCreate(ChatBase):
    pass

class ChatResponse(ChatBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatResponseWithMessages(ChatResponse):
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)

class QueryRequest(BaseModel):
    content: str = Field(..., description="Natural language prompt query content")
