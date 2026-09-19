"""Reconciliation Engine: 3-way authority comparison between Controller, Hypervisor, and VM Agent."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from weautomate.config import settings
from weautomate.database.models import (
    VirtualMachine,
    Lease,
    AuditLog,
    VMState,
    LeaseStatus,
    utc_now,
)
from weautomate.hypervisor.base import (
    HypervisorAdapter,
    HypervisorPowerState,
    HypervisorVMInfo,
)


@dataclass
class DiscrepancyItem:
    discrepancy_type: str  # SHADOW_RUNNING_VM, GHOST_LEASE, NETWORK_PARTITION, CLONE_DETECTED
    severity: str          # CRITICAL, WARNING, INFO
    hypervisor_uuid: str
    hostname: str
    controller_state: Optional[str]
    hypervisor_state: Optional[str]
    has_active_lease: bool
    recommended_action: str
    resolution_status: str  # AUTO_RESOLVED, ESCALATED, PENDING


@dataclass
class ReconciliationReport:
    timestamp: datetime
    matched_count: int
    mismatch_count: int
    discrepancies: List[DiscrepancyItem] = field(default_factory=list)
    summary: str = ""


class ReconciliationEngine:
    """Compares Controller records against authoritative Hypervisor states and Agent telemetry."""

    def __init__(self, db: Session, hypervisor: HypervisorAdapter):
        self.db = db
        self.hypervisor = hypervisor

    def run_reconciliation(
        self,
        auto_release_ghost_leases: bool = True,
        auto_adopt_unlicensed: bool = True,
    ) -> ReconciliationReport:
        """Executes full tripartite reconciliation with optional ghost lease release and running VM adoption."""
        now = utc_now()
        report = ReconciliationReport(
            timestamp=now,
            matched_count=0,
            mismatch_count=0,
            discrepancies=[],
        )

        from weautomate.controller.lease_manager import LeaseManager
        lease_mgr = LeaseManager(self.db, hypervisor=self.hypervisor)

        # 1. Fetch all VMs known to the Controller
        vms_stmt = select(VirtualMachine)
        controller_vms = {vm.hypervisor_uuid: vm for vm in self.db.execute(vms_stmt).scalars().all()}

        # 2. Fetch all active leases in Controller
        leases_stmt = select(Lease).where(Lease.status == LeaseStatus.ACTIVE)
        active_leases = {lease.vm_id: lease for lease in self.db.execute(leases_stmt).scalars().all()}

        # 3. Fetch authoritative VM states from Hypervisor
        hypervisor_vms: Dict[str, HypervisorVMInfo] = {
            h_vm.hypervisor_uuid: h_vm for h_vm in self.hypervisor.list_vms()
        }

        # Check all Controller VMs
        for uuid, vm in controller_vms.items():
            vm.last_reconciled = now
            has_lease = vm.id in active_leases
            h_info = hypervisor_vms.get(uuid)
            hw_state = h_info.power_state if h_info else self.hypervisor.get_vm_power_state(uuid)

            # Scenario A: Ghost Lease (VM is STOPPED/NOT_FOUND on hypervisor, but holds active lease in Controller)
            if has_lease and hw_state in (HypervisorPowerState.STOPPED, HypervisorPowerState.TERMINATED, HypervisorPowerState.NOT_FOUND):
                resolution = "PENDING"
                if auto_release_ghost_leases:
                    lease = active_leases[vm.id]
                    lease.status = LeaseStatus.RELEASED
                    lease.released_at = now
                    lease.release_reason = f"reconciliation_authoritative_{hw_state.value.lower()}"
                    vm.current_state = VMState.STOPPED
                    self.db.add(
                        AuditLog(
                            timestamp=now,
                            vm_id=vm.id,
                            action="RECONCILE_RELEASE_GHOST_LEASE",
                            actor="reconciliation_engine",
                            notes=(
                                f"Auto-released lease #{lease.id} ({lease.cores_allocated} cores) because "
                                f"hypervisor authoritatively confirmed VM is {hw_state.value}."
                            ),
                        )
                    )
                    del active_leases[vm.id]
                    resolution = "AUTO_RESOLVED"

                report.mismatch_count += 1
                report.discrepancies.append(
                    DiscrepancyItem(
                        discrepancy_type="GHOST_LEASE",
                        severity="WARNING",
                        hypervisor_uuid=uuid,
                        hostname=vm.hostname,
                        controller_state=vm.current_state.value,
                        hypervisor_state=hw_state.value,
                        has_active_lease=has_lease,
                        recommended_action="Release active core lease as VM is verified stopped.",
                        resolution_status=resolution,
                    )
                )

            # Scenario B: Network Partition / Unreachable (VM RUNNING on hypervisor, but heartbeat lost in Controller)
            elif has_lease and hw_state == HypervisorPowerState.RUNNING and vm.current_state == VMState.UNREACHABLE:
                report.mismatch_count += 1
                report.discrepancies.append(
                    DiscrepancyItem(
                        discrepancy_type="NETWORK_PARTITION",
                        severity="WARNING",
                        hypervisor_uuid=uuid,
                        hostname=vm.hostname,
                        controller_state=vm.current_state.value,
                        hypervisor_state=hw_state.value,
                        has_active_lease=has_lease,
                        recommended_action="Keep core allocation reserved; investigate guest network connectivity.",
                        resolution_status="ESCALATED",
                    )
                )

            # Scenario C: State Matches Perfectly
            elif (has_lease and hw_state == HypervisorPowerState.RUNNING) or (not has_lease and hw_state != HypervisorPowerState.RUNNING):
                report.matched_count += 1

        # Check for Shadow VMs: Running on hypervisor with NO active lease in Controller
        for uuid, h_vm in hypervisor_vms.items():
            if h_vm.power_state == HypervisorPowerState.RUNNING:
                ctrl_vm = controller_vms.get(uuid)
                has_lease = (ctrl_vm.id in active_leases) if ctrl_vm else False
                if not has_lease:
                    resolution = "ESCALATED"
                    action_msg = "CRITICAL: Unauthorized VM running without license. Gate or allocate cores immediately."

                    # If auto_adopt_unlicensed is enabled and VM is registered, attempt auto-allocation
                    if auto_adopt_unlicensed and ctrl_vm:
                        adopt_req_id = f"recon-adopt-{uuid}-{int(now.timestamp())}"
                        new_lease, eval_res = lease_mgr.allocate_lease(
                            hypervisor_uuid=uuid,
                            request_id=adopt_req_id,
                            requested_cores=ctrl_vm.core_count,
                        )
                        if new_lease and eval_res.allowed:
                            active_leases[ctrl_vm.id] = new_lease
                            resolution = "AUTO_RESOLVED"
                            action_msg = f"Auto-allocated lease #{new_lease.id} ({new_lease.cores_allocated} cores) to running VM."
                            self.db.add(
                                AuditLog(
                                    timestamp=now,
                                    vm_id=ctrl_vm.id,
                                    action="RECONCILE_AUTO_ALLOCATE_RUNNING_VM",
                                    actor="reconciliation_engine",
                                    notes=f"Auto-allocated {new_lease.cores_allocated} cores to running VM {ctrl_vm.hostname} as capacity became available.",
                                )
                            )

                    report.mismatch_count += 1
                    report.discrepancies.append(
                        DiscrepancyItem(
                            discrepancy_type="SHADOW_RUNNING_VM",
                            severity="CRITICAL" if resolution == "ESCALATED" else "INFO",
                            hypervisor_uuid=uuid,
                            hostname=h_vm.hostname,
                            controller_state=ctrl_vm.current_state.value if ctrl_vm else "UNREGISTERED",
                            hypervisor_state=h_vm.power_state.value,
                            has_active_lease=(resolution == "AUTO_RESOLVED"),
                            recommended_action=action_msg,
                            resolution_status=resolution,
                        )
                    )
                    if resolution == "ESCALATED":
                        self.db.add(
                            AuditLog(
                                timestamp=now,
                                vm_id=ctrl_vm.id if ctrl_vm else None,
                                action="ALERT_SHADOW_VM",
                                actor="reconciliation_engine",
                                notes=f"CRITICAL: VM {h_vm.hostname} (UUID {uuid}) is RUNNING on hypervisor without a licensed core lease!",
                            )
                        )

        self.db.commit()
        report.summary = (
            f"Reconciliation completed: {report.matched_count} matched, "
            f"{report.mismatch_count} discrepancies detected."
        )
        return report
