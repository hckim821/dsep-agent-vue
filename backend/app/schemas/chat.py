from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None


class ChatSessionOut(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations_json: Optional[Any] = None
    created_at: datetime

    model_config = {"from_attributes": True}
