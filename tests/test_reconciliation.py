"""Tests for the 3-way Reconciliation Engine."""

import pytest
from weautomate.controller.lease_manager import LeaseManager
from weautomate.reconciliation.engine import ReconciliationEngine
from weautomate.hypervisor.mock import MockHypervisorAdapter, HypervisorPowerState
from weautomate.database.models import VMState, LeaseStatus


def test_reconciliation_auto_releases_ghost_lease(db_session):
    """Scenario: Controller holds an active lease, but hypervisor confirms the VM is STOPPED.

    Resolution: Safely auto-releases the ghost lease and frees up cores.
    """
    hyp = MockHypervisorAdapter()
    hyp.register_simulated_vm("uuid-ghost-001", "vm-ghost", HypervisorPowerState.STOPPED)

    mgr = LeaseManager(db_session, hypervisor=hyp)
    vm = mgr.register_vm(hostname="vm-ghost", hypervisor_uuid="uuid-ghost-001", core_count=8)
    lease, _ = mgr.allocate_lease(vm.hypervisor_uuid, "req-ghost-01", 8)

    engine = ReconciliationEngine(db_session, hyp)
    report = engine.run_reconciliation(auto_release_ghost_leases=True)

    assert report.mismatch_count == 1
    assert report.discrepancies[0].discrepancy_type == "GHOST_LEASE"
    assert report.discrepancies[0].resolution_status == "AUTO_RESOLVED"

    db_session.refresh(lease)
    assert lease.status == LeaseStatus.RELEASED
    assert "reconciliation_authoritative_stopped" in lease.release_reason

    # Cores freed
    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 0
    assert summary["available_cores"] == 80


def test_reconciliation_detects_shadow_vm(db_session):
    """Scenario: An unauthorized VM is physically RUNNING on the hypervisor without an active lease.

    Resolution: Emits CRITICAL alert.
    """
    hyp = MockHypervisorAdapter()
    # Shadow VM running on hypervisor
    hyp.register_simulated_vm("uuid-shadow-001", "vm-unauthorized-shadow", HypervisorPowerState.RUNNING)

    engine = ReconciliationEngine(db_session, hyp)
    report = engine.run_reconciliation()

    assert report.mismatch_count == 1
    assert report.discrepancies[0].discrepancy_type == "SHADOW_RUNNING_VM"
    assert report.discrepancies[0].severity == "CRITICAL"
    assert report.discrepancies[0].resolution_status == "ESCALATED"


def test_reconciliation_detects_network_partition(db_session):
    """Scenario: VM is UNREACHABLE (heartbeat lost), but Hypervisor confirms it is still physically RUNNING.

    Resolution: Flags NETWORK_PARTITION, keeps core allocation reserved.
    """
    hyp = MockHypervisorAdapter()
    hyp.register_simulated_vm("uuid-part-001", "vm-partitioned", HypervisorPowerState.RUNNING)

    mgr = LeaseManager(db_session, hypervisor=hyp)
    vm = mgr.register_vm(hostname="vm-partitioned", hypervisor_uuid="uuid-part-001", core_count=8)
    lease, _ = mgr.allocate_lease(vm.hypervisor_uuid, "req-part-01", 8)

    vm.current_state = VMState.UNREACHABLE
    db_session.commit()

    engine = ReconciliationEngine(db_session, hyp)
    report = engine.run_reconciliation()

    assert report.mismatch_count == 1
    assert report.discrepancies[0].discrepancy_type == "NETWORK_PARTITION"
    assert report.discrepancies[0].has_active_lease is True

    # Lease must remain ACTIVE!
    db_session.refresh(lease)
    assert lease.status == LeaseStatus.ACTIVE


def test_auto_deallocate_on_shutdown_and_reallocate_to_running_vm(db_session):
    """Answers USER question 1:

    When VM A shuts down, does the system auto de-allocate its license,
    and then allocate it to an unlicensed VM B that is currently running?
    """
    hyp = MockHypervisorAdapter()
    mgr = LeaseManager(db_session, hypervisor=hyp)

    # VM A is registered and running with an active lease
    hyp.register_simulated_vm("uuid-vm-a", "VM-A", HypervisorPowerState.RUNNING, core_count=8)
    vm_a = mgr.register_vm(hostname="VM-A", hypervisor_uuid="uuid-vm-a", core_count=8)
    lease_a, _ = mgr.allocate_lease("uuid-vm-a", "req-lease-a", 8)
    assert lease_a.status == LeaseStatus.ACTIVE

    # VM B is registered and physically RUNNING on hypervisor, but currently has NO lease (unlicensed)
    hyp.register_simulated_vm("uuid-vm-b", "VM-B", HypervisorPowerState.RUNNING, core_count=8)
    vm_b = mgr.register_vm(hostname="VM-B", hypervisor_uuid="uuid-vm-b", core_count=8)

    # Now VM A shuts down on hypervisor
    hyp.set_vm_power_state("uuid-vm-a", HypervisorPowerState.STOPPED)

    # Reconciliation runs (as it does automatically or on schedule)
    engine = ReconciliationEngine(db_session, hyp)
    report = engine.run_reconciliation(auto_release_ghost_leases=True, auto_adopt_unlicensed=True)

    db_session.refresh(lease_a)
    db_session.refresh(vm_a)
    db_session.refresh(vm_b)

    # 1. VM A's lease must be automatically de-allocated (RELEASED)
    assert lease_a.status == LeaseStatus.RELEASED
    assert vm_a.current_state == VMState.STOPPED

    # 2. VM B must now have an ACTIVE lease automatically allocated!
    active_b_lease = [d for d in report.discrepancies if d.hypervisor_uuid == "uuid-vm-b"][0]
    assert active_b_lease.resolution_status == "AUTO_RESOLVED"
    assert vm_b.current_state == VMState.RUNNING

    # 3. Verify in database that VM B holds an active lease
    from sqlalchemy import select
    from weautomate.database.models import Lease
    lease_b = db_session.execute(
        select(Lease).where(Lease.vm_id == vm_b.id, Lease.status == LeaseStatus.ACTIVE)
    ).scalars().first()
    assert lease_b is not None
    assert lease_b.cores_allocated == 8

