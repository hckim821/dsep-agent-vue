import os
import sys
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_editor
from app.models.ingest import (
    IngestAttachment,
    IngestJob,
    IngestPost,
    IngestPostPriority,
    IngestPostStatus,
    IngestPostType,
)
from app.models.user import User
from app.models.wiki import WikiPage, WikiPageSource
from app.schemas.ingest import (
    AttachmentOut,
    IngestJobOut,
    IngestPostCreate,
    IngestPostOut,
)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


def _wiki_pipeline_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@router.get("/posts", response_model=list[IngestPostOut])
def list_posts(
    status: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(IngestPost)
    if status:
        q = q.filter(IngestPost.status == status)
    if category:
        q = q.filter(IngestPost.category == category)
    return q.order_by(IngestPost.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/posts", response_model=IngestPostOut)
def create_post(
    body: IngestPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    data = body.model_dump()
    try:
        if "type" in data:
            data["type"] = IngestPostType(data["type"])
        if "priority" in data:
            data["priority"] = IngestPostPriority(data["priority"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    post = IngestPost(**data, author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/posts/{post_id}")
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.get(IngestPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    jobs = (
        db.query(IngestJob)
        .filter_by(post_id=post_id)
        .order_by(IngestJob.started_at)
        .all()
    )

    sources = db.query(WikiPageSource).filter_by(ingest_post_id=post_id).all()
    wiki_pages = []
    for s in sources:
        page = db.get(WikiPage, s.wiki_page_id)
        if page:
            wiki_pages.append(
                {
                    "id": page.id,
                    "path": page.path,
                    "title": page.title,
                    "relation": s.relation.value,
                }
            )

    attachments = (
        db.query(IngestAttachment).filter_by(post_id=post_id).all()
    )

    return {
        "post": IngestPostOut.model_validate(post).model_dump(mode="json"),
        "jobs": [IngestJobOut.model_validate(j).model_dump(mode="json") for j in jobs],
        "wiki_pages": wiki_pages,
        "attachments": [
            AttachmentOut.model_validate(a).model_dump(mode="json") for a in attachments
        ],
    }


@router.post("/posts/{post_id}/attachments", response_model=AttachmentOut)
async def upload_attachment(
    post_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    post = db.get(IngestPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if _wiki_pipeline_path() not in sys.path:
        sys.path.insert(0, _wiki_pipeline_path())

    try:
        from wiki_pipeline.storage import save_upload
    except ImportError:
        raise HTTPException(status_code=503, detail="Storage module not available")

    data = await file.read()
    try:
        info = save_upload(post_id, file.filename, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    attachment = IngestAttachment(
        post_id=post_id,
        stored_filename=info["stored_filename"],
        original_filename=file.filename,
        file_path=info["file_path"],
        mime_type=file.content_type,
        size_bytes=info["size_bytes"],
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.post("/posts/{post_id}/run")
def run_post(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    post = db.get(IngestPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status.value not in ("pending", "failed"):
        raise HTTPException(
            status_code=400, detail=f"Post is in status: {post.status.value}"
        )

    def _run():
        if _wiki_pipeline_path() not in sys.path:
            sys.path.insert(0, _wiki_pipeline_path())
        try:
            from wiki_pipeline.ingest import ingest_post
            ingest_post(post_id)
        except Exception:
            pass

    background_tasks.add_task(_run)
    return {"message": "Ingest started", "post_id": post_id}


@router.post("/posts/{post_id}/retry")
def retry_post(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    post = db.get(IngestPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = IngestPostStatus.pending
    db.commit()

    def _run():
        if _wiki_pipeline_path() not in sys.path:
            sys.path.insert(0, _wiki_pipeline_path())
        try:
            from wiki_pipeline.ingest import ingest_post
            ingest_post(post_id)
        except Exception:
            pass

    background_tasks.add_task(_run)
    return {"message": "Ingest retry started", "post_id": post_id}
