from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class LintFindingOut(BaseModel):
    id: int
    type: str
    page_ids_json: Optional[Any] = None
    description: Optional[str] = None
    severity: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
