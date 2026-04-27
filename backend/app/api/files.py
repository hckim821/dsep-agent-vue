import os
import sys

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.ingest import IngestAttachment

router = APIRouter(prefix="/api/files", tags=["files"])


def _wiki_pipeline_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@router.get("/{post_id}/{filename}")
def serve_file(
    post_id: int,
    filename: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    attachment = (
        db.query(IngestAttachment)
        .filter_by(post_id=post_id, stored_filename=filename)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="File not found")

    if _wiki_pipeline_path() not in sys.path:
        sys.path.insert(0, _wiki_pipeline_path())

    try:
        from wiki_pipeline.storage import get_file_path
        file_path = get_file_path(attachment.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found on disk")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=attachment.original_filename,
        media_type=attachment.mime_type or "application/octet-stream",
    )
