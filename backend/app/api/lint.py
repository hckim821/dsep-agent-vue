import os
import sys
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.lint import LintFinding
from app.schemas.lint import LintFindingOut

router = APIRouter(prefix="/api/lint", tags=["lint"])


def _wiki_pipeline_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@router.get("/findings", response_model=list[LintFindingOut])
def list_findings(
    type: Optional[str] = None,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(LintFinding)
    if type:
        q = q.filter(LintFinding.type == type)
    if severity:
        q = q.filter(LintFinding.severity == severity)
    if resolved is not None:
        if resolved:
            q = q.filter(LintFinding.resolved_at.isnot(None))
        else:
            q = q.filter(LintFinding.resolved_at.is_(None))
    return (
        q.order_by(LintFinding.detected_at.desc()).offset(skip).limit(limit).all()
    )


@router.post("/run")
def run_lint(
    background_tasks: BackgroundTasks,
    check_types: Optional[list[str]] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    def _run():
        if _wiki_pipeline_path() not in sys.path:
            sys.path.insert(0, _wiki_pipeline_path())
        try:
            from wiki_pipeline.lint import run_lint as _lint
            _lint(check_types)
        except Exception:
            pass

    background_tasks.add_task(_run)
    return {"message": "Lint started"}
