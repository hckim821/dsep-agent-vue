from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SchemaVersionOut(BaseModel):
    id: int
    content: str
    updated_by: int
    updated_at: datetime
    note: Optional[str] = None

    model_config = {"from_attributes": True}


class SchemaVersionCreate(BaseModel):
    content: str
    note: Optional[str] = None
