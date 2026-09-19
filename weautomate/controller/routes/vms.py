"""VM endpoints for registration and status tracking."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from weautomate.database.session import get_db
from weautomate.database.models import VirtualMachine
from weautomate.controller.schemas import VMRegisterRequest, VMResponse, StoppingRequest
from weautomate.controller.lease_manager import LeaseManager

router = APIRouter(prefix="/vms", tags=["Virtual Machines"])


@router.post("/register", response_model=VMResponse, status_code=status.HTTP_201_CREATED)
def register_vm(req: VMRegisterRequest, db: Session = Depends(get_db)):
    """Registers a VM identity. Outbound only; idempotent."""
    mgr = LeaseManager(db)
    vm = mgr.register_vm(
        hostname=req.hostname,
        hypervisor_uuid=req.hypervisor_uuid,
        core_count=req.core_count,
        server_farm=req.server_farm,
        ip_address=req.ip_address,
        os_version=req.os_version,
        activation_status=req.activation_status,
    )
    return vm


@router.get("", response_model=List[VMResponse])
def list_vms(db: Session = Depends(get_db)):
    """Lists all registered virtual machines."""
    vms = db.execute(select(VirtualMachine)).scalars().all()
    return vms


@router.get("/{hypervisor_uuid}", response_model=VMResponse)
def get_vm(hypervisor_uuid: str, db: Session = Depends(get_db)):
    """Fetches details for a specific VM."""
    stmt = select(VirtualMachine).where(VirtualMachine.hypervisor_uuid == hypervisor_uuid)
    vm = db.execute(stmt).scalars().first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    return vm


@router.post("/stopping")
def notify_stopping(req: StoppingRequest, db: Session = Depends(get_db)):
    """Graceful shutdown notification from VM agent."""
    mgr = LeaseManager(db)
    success = mgr.notify_stopping(req.hypervisor_uuid)
    if not success:
        raise HTTPException(status_code=404, detail="VM not found")
    return {"status": "stopping_acknowledged", "hypervisor_uuid": req.hypervisor_uuid}
