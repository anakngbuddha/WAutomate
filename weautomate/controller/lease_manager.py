"""Lease Manager for Windows Server 2025 dynamic core licensing."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from weautomate.config import settings
from weautomate.database.models import (
    VirtualMachine,
    Lease,
    AuditLog,
    VMState,
    LeaseStatus,
    Entitlement,
    utc_now,
)
from weautomate.controller.policy import LicensingPolicyEngine, PolicyEvaluationResult
from weautomate.hypervisor.base import HypervisorAdapter, HypervisorPowerState


class LeaseManager:
    """Manages lease lifecycles with idempotency, state tracking, and strict release rules."""

    def __init__(self, db: Session, hypervisor: Optional[HypervisorAdapter] = None):
        self.db = db
        self.policy_engine = LicensingPolicyEngine(db)
        self.hypervisor = hypervisor

    def log_audit(
        self,
        action: str,
        actor: str,
        vm_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AuditLog:
        """Append an immutable audit entry."""
        log = AuditLog(
            timestamp=utc_now(),
            vm_id=vm_id,
            action=action,
            actor=actor,
            notes=notes,
        )
        self.db.add(log)
        self.db.commit()
        return log

    def register_vm(
        self,
        hostname: str,
        hypervisor_uuid: str,
        core_count: int = 8,
        server_farm: Optional[str] = None,
        ip_address: Optional[str] = None,
        os_version: Optional[str] = "Windows Server 2025 Standard",
        activation_status: Optional[str] = "Licensed",
    ) -> VirtualMachine:
        """Registers a VM or returns existing registration."""
        farm = server_farm or settings.server_farm_name
        stmt = select(VirtualMachine).where(VirtualMachine.hypervisor_uuid == hypervisor_uuid)
        vm = self.db.execute(stmt).scalars().first()

        if vm:
            # Check for hostname conflict (possible clone attempt)
            if vm.hostname != hostname:
                self.log_audit(
                    action="VM_HOSTNAME_CHANGED",
                    actor=f"agent:{hypervisor_uuid}",
                    vm_id=vm.id,
                    notes=f"Hostname changed from {vm.hostname} to {hostname}. Checking for VM clone.",
                )
            vm.hostname = hostname
            vm.core_count = max(core_count, settings.min_cores_per_vm)
            vm.server_farm = farm
            vm.ip_address = ip_address or vm.ip_address
            vm.os_version = os_version or vm.os_version
            vm.activation_status = activation_status or vm.activation_status
        else:
            vm = VirtualMachine(
                hostname=hostname,
                hypervisor_uuid=hypervisor_uuid,
                core_count=max(core_count, settings.min_cores_per_vm),
                server_farm=farm,
                current_state=VMState.STOPPED,
                ip_address=ip_address,
                os_version=os_version,
                activation_status=activation_status,
            )
            self.db.add(vm)
            self.db.flush()
            self.log_audit(
                action="VM_REGISTERED",
                actor=f"agent:{hypervisor_uuid}",
                vm_id=vm.id,
                notes=f"Registered VM {hostname} ({core_count} cores, farm: {farm})",
            )

        self.db.commit()
        self.db.refresh(vm)
        return vm

    def allocate_lease(
        self,
        hypervisor_uuid: str,
        request_id: str,
        requested_cores: Optional[int] = None,
    ) -> Tuple[Optional[Lease], PolicyEvaluationResult]:
        """Allocates a core lease idempotently using request_id."""
        # Check idempotency first: If a lease with this request_id already exists, return it
        stmt = select(Lease).where(Lease.request_id == request_id)
        existing_lease = self.db.execute(stmt).scalars().first()
        if existing_lease:
            summary = self.policy_engine.get_entitlement_summary(existing_lease.entitlement_id)
            eval_res = PolicyEvaluationResult(
                allowed=True,
                reason="Idempotent response: Returning existing lease for this request_id.",
                available_cores=summary.get("available_cores", 0),
                requested_cores=existing_lease.cores_allocated,
                total_entitlement_cores=summary.get("total_cores", 0),
                active_allocated_cores=summary.get("allocated_cores", 0),
                details={"idempotent": True, "lease_id": existing_lease.id},
            )
            return existing_lease, eval_res

        # Fetch VM
        vm_stmt = select(VirtualMachine).where(VirtualMachine.hypervisor_uuid == hypervisor_uuid)
        vm = self.db.execute(vm_stmt).scalars().first()
        if not vm:
            eval_res = PolicyEvaluationResult(
                allowed=False,
                reason=f"VM with hypervisor_uuid '{hypervisor_uuid}' is not registered.",
                available_cores=0,
                requested_cores=requested_cores or 8,
                total_entitlement_cores=0,
                active_allocated_cores=0,
                details={"error": "vm_not_registered"},
            )
            return None, eval_res

        # Check if VM already has an active lease
        active_lease_stmt = select(Lease).where(
            Lease.vm_id == vm.id,
            Lease.status == LeaseStatus.ACTIVE,
        )
        current_active = self.db.execute(active_lease_stmt).scalars().first()
        if current_active:
            summary = self.policy_engine.get_entitlement_summary(current_active.entitlement_id)
            eval_res = PolicyEvaluationResult(
                allowed=True,
                reason=f"VM {vm.hostname} already holds active lease #{current_active.id}.",
                available_cores=summary.get("available_cores", 0),
                requested_cores=current_active.cores_allocated,
                total_entitlement_cores=summary.get("total_cores", 0),
                active_allocated_cores=summary.get("allocated_cores", 0),
                details={"already_active": True, "lease_id": current_active.id},
            )
            return current_active, eval_res

        # Policy evaluation
        eval_res = self.policy_engine.evaluate_allocation(vm, requested_cores=requested_cores)
        if not eval_res.allowed:
            self.log_audit(
                action="ALLOCATE_DENIED",
                actor=f"agent:{vm.hypervisor_uuid}",
                vm_id=vm.id,
                notes=f"Core allocation denied: {eval_res.reason}",
            )
            return None, eval_res

        # Entitlement lookup
        entitlement = self.db.execute(select(Entitlement)).scalars().first()
        now = utc_now()
        expires = now + timedelta(seconds=settings.lease_duration_seconds)
        cores = requested_cores if requested_cores is not None else vm.core_count

        new_lease = Lease(
            entitlement_id=entitlement.id,
            vm_id=vm.id,
            request_id=request_id,
            cores_allocated=cores,
            status=LeaseStatus.ACTIVE,
            granted_at=now,
            expires_at=expires,
        )
        self.db.add(new_lease)

        # Update VM state
        vm.current_state = VMState.RUNNING
        vm.last_heartbeat = now

        self.db.flush()
        self.log_audit(
            action="ALLOCATE_SUCCESS",
            actor=f"agent:{vm.hypervisor_uuid}",
            vm_id=vm.id,
            notes=f"Granted lease #{new_lease.id} for {cores} cores. Expires at {expires.isoformat()}.",
        )
        self.db.commit()
        self.db.refresh(new_lease)
        return new_lease, eval_res

    def heartbeat(self, hypervisor_uuid: str) -> Tuple[bool, str]:
        """Extends active lease and marks VM healthy."""
        vm_stmt = select(VirtualMachine).where(VirtualMachine.hypervisor_uuid == hypervisor_uuid)
        vm = self.db.execute(vm_stmt).scalars().first()
        if not vm:
            return False, "VM not registered"

        now = utc_now()
        lease_stmt = select(Lease).where(
            Lease.vm_id == vm.id,
            Lease.status == LeaseStatus.ACTIVE,
        )
        lease = self.db.execute(lease_stmt).scalars().first()
        if not lease:
            return False, "No active lease found for this VM"

        # Extend lease
        lease.expires_at = now + timedelta(seconds=settings.lease_duration_seconds)
        vm.last_heartbeat = now

        # If it was UNREACHABLE, recover it
        if vm.current_state in (VMState.UNREACHABLE, VMState.UNKNOWN):
            vm.current_state = VMState.RUNNING
            self.log_audit(
                action="HEARTBEAT_RECOVERED",
                actor=f"agent:{vm.hypervisor_uuid}",
                vm_id=vm.id,
                notes=f"VM {vm.hostname} recovered from {vm.current_state} to RUNNING.",
            )
        else:
            vm.current_state = VMState.RUNNING

        self.db.commit()
        return True, f"Lease extended until {lease.expires_at.isoformat()}"

    def notify_stopping(self, hypervisor_uuid: str) -> bool:
        """Records graceful shutdown signal from VM Agent. Lease remains reserved until authoritative confirmation."""
        vm_stmt = select(VirtualMachine).where(VirtualMachine.hypervisor_uuid == hypervisor_uuid)
        vm = self.db.execute(vm_stmt).scalars().first()
        if not vm:
            return False

        vm.current_state = VMState.STOPPING
        self.log_audit(
            action="VM_STOPPING_SIGNAL",
            actor=f"agent:{vm.hypervisor_uuid}",
            vm_id=vm.id,
            notes="Agent signaled shutdown in progress. Core allocation remains reserved.",
        )
        self.db.commit()
        return True

    def release_lease(
        self,
        hypervisor_uuid: str,
        reason: str,
        force: bool = False,
        actor: str = "controller",
    ) -> Tuple[bool, str]:
        """Releases lease ONLY upon authoritative hypervisor confirmation (STOPPED/TERMINATED) or explicit admin force."""
        vm_stmt = select(VirtualMachine).where(VirtualMachine.hypervisor_uuid == hypervisor_uuid)
        vm = self.db.execute(vm_stmt).scalars().first()
        if not vm:
            return False, "VM not registered"

        # Check authoritative hypervisor state if adapter is configured and not forced
        if self.hypervisor and not force:
            hw_state = self.hypervisor.get_vm_power_state(hypervisor_uuid)
            if hw_state == HypervisorPowerState.RUNNING:
                return (
                    False,
                    "Release rejected: Hypervisor confirms VM is still RUNNING. Cannot release active core allocation.",
                )

        lease_stmt = select(Lease).where(
            Lease.vm_id == vm.id,
            Lease.status == LeaseStatus.ACTIVE,
        )
        lease = self.db.execute(lease_stmt).scalars().first()
        if not lease:
            return False, "No active lease to release"

        now = utc_now()
        lease.status = LeaseStatus.RELEASED
        lease.released_at = now
        lease.release_reason = reason

        vm.current_state = VMState.STOPPED

        self.log_audit(
            action="RELEASE_SUCCESS",
            actor=actor,
            vm_id=vm.id,
            notes=f"Released lease #{lease.id} ({lease.cores_allocated} cores). Reason: {reason}",
        )
        self.db.commit()
        return True, f"Lease #{lease.id} released successfully"

    def scan_unreachable_vms(self) -> List[VirtualMachine]:
        """Detects VMs whose heartbeat expired. Marks UNREACHABLE without releasing leases."""
        now = utc_now()
        cutoff = now - timedelta(seconds=settings.lease_duration_seconds)

        stmt = select(VirtualMachine).where(
            VirtualMachine.current_state == VMState.RUNNING,
            VirtualMachine.last_heartbeat < cutoff,
        )
        unreachable_vms = list(self.db.execute(stmt).scalars().all())

        for vm in unreachable_vms:
            vm.current_state = VMState.UNREACHABLE
            self.log_audit(
                action="VM_UNREACHABLE",
                actor="controller:heartbeat_monitor",
                vm_id=vm.id,
                notes=(
                    f"Heartbeat lost for VM {vm.hostname}. Flagged as UNREACHABLE. "
                    "Core allocation remains reserved to prevent over-allocation."
                ),
            )
        if unreachable_vms:
            self.db.commit()
        return unreachable_vms
