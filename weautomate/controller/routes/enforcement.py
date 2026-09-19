"""Enforcement endpoints implementing Tier 1 (Pre-boot admission) & Tier 2 (Platform RBAC start gating)."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from weautomate.config import settings
from weautomate.database.session import get_db
from weautomate.database.models import VirtualMachine, Lease, LeaseStatus, VMState
from weautomate.controller.schemas import RequestStartVM
from weautomate.controller.policy import LicensingPolicyEngine
from weautomate.controller.lease_manager import LeaseManager

router = APIRouter(prefix="/enforcement", tags=["Enforcement"])


@router.get("/status")
def get_enforcement_status():
    """Returns configured enforcement tier and descriptions."""
    descriptions = {
        1: "Tier 1 (Preferred): Pre-boot admission hook / gate API. VM start call gated by controller.",
        2: "Tier 2 (Practical fallback): Platform RBAC start proxy. Humans/automation start VMs via controller.",
        3: "Tier 3 (Minimum viable): Detection & alerting on unauthorized running VMs.",
    }
    return {
        "active_tier": settings.enforcement_tier,
        "description": descriptions.get(settings.enforcement_tier, "Unknown tier"),
        "pre_boot_gating_enabled": settings.enforcement_tier in (1, 2),
    }


@router.post("/request-start")
def request_start_vm(req: RequestStartVM, db: Session = Depends(get_db)):
    """Admission control gate: Verifies core availability before allowing or initiating a VM boot."""
    policy_engine = LicensingPolicyEngine(db)
    lease_mgr = LeaseManager(db)

    # 1. Fetch VM
    stmt = select(VirtualMachine).where(VirtualMachine.hypervisor_uuid == req.hypervisor_uuid)
    vm = db.execute(stmt).scalars().first()
    if not vm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VM with hypervisor_uuid '{req.hypervisor_uuid}' is not registered.",
        )

    # 2. Check if already has an active lease and running
    active_lease = db.execute(
        select(Lease).where(Lease.vm_id == vm.id, Lease.status == LeaseStatus.ACTIVE)
    ).scalars().first()

    if active_lease:
        return {
            "authorized": True,
            "message": f"VM {vm.hostname} already has an active lease (#{active_lease.id}). Start authorized.",
            "lease_id": active_lease.id,
            "cores": active_lease.cores_allocated,
        }

    # 3. Evaluate capacity & FVB policy
    eval_res = policy_engine.evaluate_allocation(vm, requested_cores=req.requested_cores)
    if not eval_res.allowed:
        lease_mgr.log_audit(
            action="ENFORCE_START_DENIED",
            actor=req.actor,
            vm_id=vm.id,
            notes=f"Tier {settings.enforcement_tier} blocked start: {eval_res.reason}",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "authorized": False,
                "error": "start_denied_insufficient_cores",
                "reason": eval_res.reason,
                "available_cores": eval_res.available_cores,
                "requested_cores": eval_res.requested_cores,
            },
        )

    # 4. If policy passes, create pre-boot lease reservation
    pre_boot_request_id = f"start-{uuid.uuid4()}"
    lease, _ = lease_mgr.allocate_lease(
        hypervisor_uuid=req.hypervisor_uuid,
        request_id=pre_boot_request_id,
        requested_cores=req.requested_cores,
    )

    lease_mgr.log_audit(
        action="ENFORCE_START_PERMITTED",
        actor=req.actor,
        vm_id=vm.id,
        notes=(
            f"Tier {settings.enforcement_tier} admission granted for VM {vm.hostname}. "
            f"Reserved {lease.cores_allocated} cores under lease #{lease.id}."
        ),
    )

    return {
        "authorized": True,
        "message": f"Admission granted. Reserved {lease.cores_allocated} cores for VM {vm.hostname}.",
        "lease_id": lease.id,
        "cores": lease.cores_allocated,
        "request_id": pre_boot_request_id,
    }
