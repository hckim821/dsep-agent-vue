import os
import re
import sys
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
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


def _derive_title(body_md: str) -> str:
    """본문에서 제목 자동 추출. 빈 본문이면 임시 제목."""
    if not body_md:
        return "(제목 없는 자료)"
    # 1. 첫 H1 시도
    m = re.search(r"^\s*#\s+(.+)$", body_md, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        return title[:200] or "(제목 없는 자료)"
    # 2. 첫 비어있지 않은 줄
    for line in body_md.splitlines():
        line = line.strip()
        if not line:
            continue
        # 마크다운 부호 제거
        line = re.sub(r"^[#>\-\*\+]\s*", "", line)
        line = re.sub(r"\*\*|__|`", "", line)
        if line:
            return line[:80] + ("…" if len(line) > 80 else "")
    return "(제목 없는 자료)"


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

    # 제목이 비어있으면 본문에서 자동 추출
    title = (data.get("title") or "").strip()
    if not title:
        data["title"] = _derive_title(data.get("body_md", ""))

    post = IngestPost(**data, author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


class IngestPostUpdate(BaseModel):
    title: Optional[str] = None
    body_md: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    target_wiki_path: Optional[str] = None
    rerun: Optional[bool] = False  # 완료 자료 수정 시 ingest 재실행 여부


@router.put("/posts/{post_id}")
def update_post(
    post_id: int,
    body: IngestPostUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    post = db.get(IngestPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # 처리 중인 자료는 수정 불가
    locked_states = {"ocr_running", "ingest_running"}
    if post.status.value in locked_states:
        raise HTTPException(
            status_code=409,
            detail="처리 중인 자료는 수정할 수 없습니다. 잠시 후 다시 시도해주세요.",
        )

    # 권한: 본인 또는 admin
    if post.author_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="본인이 올린 자료만 수정할 수 있습니다.")

    update_data = body.model_dump(exclude_unset=True, exclude_none=False)
    rerun = update_data.pop("rerun", False)

    # type/priority enum 변환
    try:
        if update_data.get("type"):
            update_data["type"] = IngestPostType(update_data["type"])
        if update_data.get("priority"):
            update_data["priority"] = IngestPostPriority(update_data["priority"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 제목 자동 채우기
    if "title" in update_data:
        new_title = (update_data.get("title") or "").strip()
        if not new_title:
            body_for_title = update_data.get("body_md", post.body_md)
            update_data["title"] = _derive_title(body_for_title or "")

    was_done = post.status.value == "done"
    for k, v in update_data.items():
        setattr(post, k, v)

    # 완료 자료 수정 시 처리
    if was_done:
        if rerun:
            # 다시 정리하기 — pending으로 되돌리고 백그라운드 ingest 시작
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
            return {"message": "수정 후 재정리를 시작합니다", "post_id": post_id, "rerun": True}
        else:
            # 원본만 수정 — 위키는 그대로 (어긋날 수 있음을 클라이언트가 안내)
            db.commit()
            return {"message": "원본만 수정되었습니다 (지식베이스는 그대로)", "post_id": post_id, "rerun": False}

    db.commit()
    return {"message": "수정되었습니다", "post_id": post_id, "rerun": False}


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
