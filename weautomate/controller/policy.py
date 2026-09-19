"""Licensing Policy Engine for Microsoft Flexible Virtualization Benefit (FVB)."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from weautomate.config import settings
from weautomate.database.models import (
    Entitlement,
    VirtualMachine,
    Lease,
    LeaseStatus,
    VMState,
)


@dataclass
class PolicyEvaluationResult:
    allowed: bool
    reason: str
    available_cores: int
    requested_cores: int
    total_entitlement_cores: int
    active_allocated_cores: int
    details: Dict[str, Any] = field(default_factory=dict)


class LicensingPolicyEngine:
    """Enforces Microsoft FVB rules and core capacity boundaries."""

    def __init__(self, db: Session):
        self.db = db

    def get_entitlement_summary(self, entitlement_id: Optional[int] = None) -> Dict[str, Any]:
        """Calculates total, allocated, and free core counts."""
        query = select(Entitlement)
        if entitlement_id:
            query = query.where(Entitlement.id == entitlement_id)
        entitlement = self.db.execute(query).scalars().first()

        if not entitlement:
            return {
                "entitlement_id": None,
                "total_cores": 0,
                "allocated_cores": 0,
                "available_cores": 0,
                "error": "No entitlement found in database",
            }

        # Calculate currently allocated cores for active leases
        allocated_stmt = (
            select(func.coalesce(func.sum(Lease.cores_allocated), 0))
            .where(
                Lease.entitlement_id == entitlement.id,
                Lease.status == LeaseStatus.ACTIVE,
            )
        )
        allocated_cores = self.db.execute(allocated_stmt).scalar() or 0
        available_cores = max(0, entitlement.core_quantity - allocated_cores)

        return {
            "entitlement_id": entitlement.id,
            "product": entitlement.product,
            "edition": entitlement.edition,
            "version": entitlement.version,
            "license_type": entitlement.license_type.value,
            "total_cores": entitlement.core_quantity,
            "allocated_cores": allocated_cores,
            "available_cores": available_cores,
            "agreement_ref": entitlement.agreement_ref,
        }

    def evaluate_allocation(
        self,
        vm: VirtualMachine,
        requested_cores: Optional[int] = None,
        entitlement_id: Optional[int] = None,
    ) -> PolicyEvaluationResult:
        """Evaluates whether allocating cores to the VM satisfies all FVB & capacity rules."""
        cores_to_allocate = requested_cores if requested_cores is not None else vm.core_count
        summary = self.get_entitlement_summary(entitlement_id)

        if summary.get("error"):
            return PolicyEvaluationResult(
                allowed=False,
                reason="No active licensing entitlement registered.",
                available_cores=0,
                requested_cores=cores_to_allocate,
                total_entitlement_cores=0,
                active_allocated_cores=0,
                details={"error": summary["error"]},
            )

        total_cores = summary["total_cores"]
        allocated_cores = summary["allocated_cores"]
        available_cores = summary["available_cores"]

        # Rule 1: Org-wide 16-core minimum under by-VM licensing
        if total_cores < settings.min_org_cores:
            return PolicyEvaluationResult(
                allowed=False,
                reason=f"Org-wide entitlement ({total_cores} cores) violates FVB 16-core minimum floor.",
                available_cores=available_cores,
                requested_cores=cores_to_allocate,
                total_entitlement_cores=total_cores,
                active_allocated_cores=allocated_cores,
                details={"rule": "org_wide_minimum", "min_required": settings.min_org_cores},
            )

        # Rule 2: 8-core minimum per VM under FVB
        if cores_to_allocate < settings.min_cores_per_vm:
            return PolicyEvaluationResult(
                allowed=False,
                reason=f"Requested cores ({cores_to_allocate}) is below the FVB mandatory 8-core minimum per VM.",
                available_cores=available_cores,
                requested_cores=cores_to_allocate,
                total_entitlement_cores=total_cores,
                active_allocated_cores=allocated_cores,
                details={"rule": "vm_minimum_cores", "min_required": settings.min_cores_per_vm},
            )

        # Rule 3: Server farm boundary check
        if vm.server_farm != settings.server_farm_name:
            return PolicyEvaluationResult(
                allowed=False,
                reason=f"Server farm mismatch: VM is in '{vm.server_farm}', but license pool is dedicated to '{settings.server_farm_name}'.",
                available_cores=available_cores,
                requested_cores=cores_to_allocate,
                total_entitlement_cores=total_cores,
                active_allocated_cores=allocated_cores,
                details={
                    "rule": "server_farm_boundary",
                    "vm_farm": vm.server_farm,
                    "pool_farm": settings.server_farm_name,
                },
            )

        # Rule 4: Capacity check
        if cores_to_allocate > available_cores:
            return PolicyEvaluationResult(
                allowed=False,
                reason=f"Insufficient core capacity: requested {cores_to_allocate} cores, but only {available_cores} cores available ({allocated_cores}/{total_cores} allocated).",
                available_cores=available_cores,
                requested_cores=cores_to_allocate,
                total_entitlement_cores=total_cores,
                active_allocated_cores=allocated_cores,
                details={
                    "rule": "core_capacity_exceeded",
                    "available": available_cores,
                    "requested": cores_to_allocate,
                },
            )

        return PolicyEvaluationResult(
            allowed=True,
            reason="All FVB compliance rules and capacity checks satisfied.",
            available_cores=available_cores,
            requested_cores=cores_to_allocate,
            total_entitlement_cores=total_cores,
            active_allocated_cores=allocated_cores,
            details={"status": "approved"},
        )
