"""Dashboard telemetry and aggregated metrics endpoints."""

from typing import List, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from weautomate.database.session import get_db
from weautomate.database.models import (
    Entitlement,
    VirtualMachine,
    Lease,
    LeaseStatus,
    VMState,
)
from weautomate.controller.schemas import DashboardMetrics, EntitlementResponse
from weautomate.controller.policy import LicensingPolicyEngine

router = APIRouter(tags=["Dashboard & Entitlements"])


@router.get("/entitlements", response_model=List[EntitlementResponse])
def list_entitlements(db: Session = Depends(get_db)):
    """Lists registered core licensing entitlements."""
    return db.execute(select(Entitlement)).scalars().all()


@router.get("/dashboard/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Aggregated core capacity, VM state breakdown, and lease telemetry for the web dashboard."""
    policy_engine = LicensingPolicyEngine(db)
    summary = policy_engine.get_entitlement_summary()

    total_cores = summary.get("total_cores", 0)
    allocated_cores = summary.get("allocated_cores", 0)
    available_cores = summary.get("available_cores", 0)
    utilization = round((allocated_cores / total_cores * 100), 1) if total_cores > 0 else 0.0

    # VM counts by state
    vms = db.execute(select(VirtualMachine)).scalars().all()
    vms_by_state: Dict[str, int] = {state.value: 0 for state in VMState}
    for vm in vms:
        vms_by_state[vm.current_state.value] = vms_by_state.get(vm.current_state.value, 0) + 1

    active_leases_count = db.execute(
        select(func.count(Lease.id)).where(Lease.status == LeaseStatus.ACTIVE)
    ).scalar() or 0

    return DashboardMetrics(
        total_cores=total_cores,
        allocated_cores=allocated_cores,
        available_cores=available_cores,
        utilization_percentage=utilization,
        total_vms=len(vms),
        vms_by_state=vms_by_state,
        active_leases_count=active_leases_count,
        latest_reconciliation=None,
    )
