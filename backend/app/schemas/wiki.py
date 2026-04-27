from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class WikiPageOut(BaseModel):
    id: int
    path: str
    title: str
    category: Optional[str] = None
    summary: Optional[str] = None
    current_commit_sha: Optional[str] = None
    last_ingest_id: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class WikiPageDetail(WikiPageOut):
    content: Optional[str] = None


class WikiTreeNode(BaseModel):
    key: str
    title: str
    path: str
    isLeaf: bool = True
    children: List["WikiTreeNode"] = []


WikiTreeNode.model_rebuild()


class SearchResult(BaseModel):
    page_id: int
    path: str
    title: str
    snippet: str
