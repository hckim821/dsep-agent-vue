from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.schema_version import SchemaVersion
from app.schemas.schema_version import SchemaVersionCreate, SchemaVersionOut

router = APIRouter(prefix="/api/schema", tags=["schema"])


@router.get("/current", response_model=SchemaVersionOut)
def get_current_schema(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    schema = (
        db.query(SchemaVersion).order_by(SchemaVersion.updated_at.desc()).first()
    )
    if not schema:
        raise HTTPException(status_code=404, detail="No schema found")
    return schema


@router.put("/current", response_model=SchemaVersionOut)
def update_schema(
    body: SchemaVersionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    schema = SchemaVersion(
        content=body.content,
        updated_by=current_user.id,
        note=body.note,
    )
    db.add(schema)
    db.commit()
    db.refresh(schema)
    return schema


@router.get("/versions", response_model=list[SchemaVersionOut])
def list_versions(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return (
        db.query(SchemaVersion)
        .order_by(SchemaVersion.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
