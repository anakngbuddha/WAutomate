"""Lease management endpoints for core allocation, heartbeats, and authoritative release."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from weautomate.database.session import get_db
from weautomate.database.models import Lease, LeaseStatus
from weautomate.controller.schemas import (
    LeaseAllocateRequest,
    LeaseResponse,
    HeartbeatRequest,
    ReleaseRequest,
)
from weautomate.controller.lease_manager import LeaseManager

router = APIRouter(prefix="/leases", tags=["Leases"])


@router.post("/allocate", response_model=LeaseResponse)
def allocate_lease(req: LeaseAllocateRequest, db: Session = Depends(get_db)):
    """Allocates a dynamic core lease. Guaranteed idempotent via request_id."""
    mgr = LeaseManager(db)
    lease, eval_result = mgr.allocate_lease(
        hypervisor_uuid=req.hypervisor_uuid,
        request_id=req.request_id,
        requested_cores=req.requested_cores,
    )
    if not eval_result.allowed or not lease:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "allocation_denied",
                "reason": eval_result.reason,
                "available_cores": eval_result.available_cores,
                "requested_cores": eval_result.requested_cores,
                "total_cores": eval_result.total_entitlement_cores,
            },
        )
    return lease


@router.post("/heartbeat")
def heartbeat(req: HeartbeatRequest, db: Session = Depends(get_db)):
    """Agent heartbeat renewal. Extends lease duration."""
    mgr = LeaseManager(db)
    success, msg = mgr.heartbeat(req.hypervisor_uuid)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "renewed", "message": msg}


@router.post("/release")
def release_lease(req: ReleaseRequest, db: Session = Depends(get_db)):
    """Authoritative release. Released only if hypervisor confirms STOPPED or explicitly forced."""
    mgr = LeaseManager(db)
    success, msg = mgr.release_lease(
        hypervisor_uuid=req.hypervisor_uuid,
        reason=req.reason,
        force=req.force,
        actor="api_client",
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "released", "message": msg}


@router.get("/active", response_model=List[LeaseResponse])
def list_active_leases(db: Session = Depends(get_db)):
    """Lists currently active leases."""
    leases = db.execute(select(Lease).where(Lease.status == LeaseStatus.ACTIVE)).scalars().all()
    return leases


@router.get("", response_model=List[LeaseResponse])
def list_all_leases(db: Session = Depends(get_db)):
    """Lists all leases including historical records."""
    leases = db.execute(select(Lease)).scalars().all()
    return leases
