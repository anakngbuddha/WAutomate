"""Reconciliation routes for 3-way discrepancy checks."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from weautomate.database.session import get_db
from weautomate.controller.lease_manager import LeaseManager
from weautomate.reconciliation.engine import ReconciliationEngine
from weautomate.hypervisor.mock import MockHypervisorAdapter

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])

# Shared hypervisor adapter for running instances (can be injected or swapped)
_default_hypervisor = MockHypervisorAdapter()


def get_hypervisor_adapter():
    return _default_hypervisor


@router.post("/run")
def trigger_reconciliation(
    auto_release_ghost: bool = True,
    db: Session = Depends(get_db),
    hypervisor=Depends(get_hypervisor_adapter),
):
    """Executes full tripartite reconciliation."""
    # First update any unreachable VMs whose heartbeat has elapsed
    lease_mgr = LeaseManager(db, hypervisor=hypervisor)
    lease_mgr.scan_unreachable_vms()

    engine = ReconciliationEngine(db, hypervisor)
    report = engine.run_reconciliation(auto_release_ghost_leases=auto_release_ghost)
    return {
        "timestamp": report.timestamp,
        "matched_count": report.matched_count,
        "mismatch_count": report.mismatch_count,
        "summary": report.summary,
        "discrepancies": [
            {
                "type": d.discrepancy_type,
                "severity": d.severity,
                "hypervisor_uuid": d.hypervisor_uuid,
                "hostname": d.hostname,
                "controller_state": d.controller_state,
                "hypervisor_state": d.hypervisor_state,
                "has_active_lease": d.has_active_lease,
                "recommended_action": d.recommended_action,
                "resolution_status": d.resolution_status,
            }
            for d in report.discrepancies
        ],
    }


@router.get("/status")
def get_reconciliation_status(
    db: Session = Depends(get_db),
    hypervisor=Depends(get_hypervisor_adapter),
):
    """Checks current unreachable count and running reconciliation summary."""
    lease_mgr = LeaseManager(db, hypervisor=hypervisor)
    unreachable = lease_mgr.scan_unreachable_vms()
    return {
        "unreachable_vms_count": len(unreachable),
        "unreachable_vms": [vm.hostname for vm in unreachable],
    }
