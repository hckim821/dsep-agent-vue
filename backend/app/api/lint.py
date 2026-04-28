import os
import sys
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_editor
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
    body: Optional[dict] = Body(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_editor),
):
    """동기 실행 — lint는 빠른 편이라 백그라운드 대신 즉시 결과를 돌려준다."""
    check_types = (body or {}).get("check_types")
    if isinstance(check_types, list) and not check_types:
        check_types = None

    if _wiki_pipeline_path() not in sys.path:
        sys.path.insert(0, _wiki_pipeline_path())

    try:
        from wiki_pipeline.lint import run_lint as _lint
        findings = _lint(check_types)
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"품질 점검 실행 실패: {e}\n{traceback.format_exc()[-500:]}",
        )

    # 유형별 카운트 집계
    by_type: dict[str, int] = {}
    for f in findings:
        by_type[f.type] = by_type.get(f.type, 0) + 1

    return {
        "message": "품질 점검 완료",
        "total": len(findings),
        "by_type": by_type,
    }
