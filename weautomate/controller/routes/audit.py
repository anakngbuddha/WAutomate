"""Audit log routes for append-only compliance tracking."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from weautomate.database.session import get_db
from weautomate.database.models import AuditLog
from weautomate.controller.schemas import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("", response_model=List[AuditLogResponse])
def get_audit_logs(
    vm_id: Optional[int] = Query(None, description="Filter by VM ID"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieves immutable append-only audit log records."""
    stmt = select(AuditLog).order_by(desc(AuditLog.timestamp))
    if vm_id is not None:
        stmt = stmt.where(AuditLog.vm_id == vm_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()
