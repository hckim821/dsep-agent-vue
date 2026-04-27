import os
import sys
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.ingest import IngestPost
from app.models.wiki import WikiBacklink, WikiPage, WikiPageSource
from app.schemas.wiki import SearchResult, WikiPageDetail, WikiPageOut

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


def _wiki_pipeline_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@router.get("/pages", response_model=list[WikiPageOut])
def list_pages(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(WikiPage)
    if category:
        q = q.filter(WikiPage.category == category)
    return q.order_by(WikiPage.path).all()


@router.get("/tree")
def get_tree(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    pages = db.query(WikiPage).order_by(WikiPage.path).all()
    tree: dict = {}
    for page in pages:
        parts = page.path.split("/")
        node = tree
        for part in parts[:-1]:
            child = node.setdefault(part, {"__children__": {}})
            node = child["__children__"]
        node[parts[-1]] = {
            "id": page.id,
            "path": page.path,
            "title": page.title,
        }
    return tree


@router.get("/pages/by-path", response_model=WikiPageDetail)
def get_page_by_path(
    path: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    page = db.query(WikiPage).filter(WikiPage.path == path).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    if _wiki_pipeline_path() not in sys.path:
        sys.path.insert(0, _wiki_pipeline_path())

    content = None
    try:
        from wiki_pipeline.wiki_repo import read_page
        content = read_page(path)
    except Exception:
        content = None

    result = WikiPageDetail.model_validate(page)
    result.content = content
    return result


@router.get("/pages/{page_id}/backlinks", response_model=list[WikiPageOut])
def get_backlinks(
    page_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    backlinks = db.query(WikiBacklink).filter_by(to_page_id=page_id).all()
    pages = [db.get(WikiPage, bl.from_page_id) for bl in backlinks]
    return [p for p in pages if p]


@router.get("/pages/{page_id}/sources")
def get_page_sources(
    page_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sources = db.query(WikiPageSource).filter_by(wiki_page_id=page_id).all()
    result = []
    for s in sources:
        post = db.get(IngestPost, s.ingest_post_id)
        if post:
            result.append(
                {
                    "relation": s.relation.value,
                    "post_id": post.id,
                    "title": post.title,
                    "created_at": post.created_at.isoformat(),
                }
            )
    return result


@router.get("/search", response_model=list[SearchResult])
def search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        rows = db.execute(
            text(
                "SELECT id, path, title, summary FROM wiki_pages "
                "WHERE MATCH(title, summary) AGAINST(:q IN BOOLEAN MODE) LIMIT 20"
            ),
            {"q": q},
        ).fetchall()
    except Exception:
        rows = db.execute(
            text(
                "SELECT id, path, title, summary FROM wiki_pages "
                "WHERE title LIKE :q OR summary LIKE :q LIMIT 20"
            ),
            {"q": f"%{q}%"},
        ).fetchall()

    return [
        SearchResult(
            page_id=r[0],
            path=r[1],
            title=r[2],
            snippet=(r[3] or "")[:200],
        )
        for r in rows
    ]
