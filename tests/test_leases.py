"""Tests for lease lifecycle management."""

import pytest
from datetime import timedelta
from weautomate.controller.lease_manager import LeaseManager
from weautomate.database.models import VMState, LeaseStatus, utc_now
from weautomate.config import settings
from weautomate.hypervisor.mock import MockHypervisorAdapter, HypervisorPowerState


def test_lease_allocation_and_heartbeat(db_session):
    """Test full cycle of allocation and heartbeat extension."""
    mgr = LeaseManager(db_session)
    vm = mgr.register_vm(
        hostname="ws2025-prod-01",
        hypervisor_uuid="uuid-prod-001",
        core_count=8,
    )

    lease, eval_res = mgr.allocate_lease(
        hypervisor_uuid=vm.hypervisor_uuid,
        request_id="req-lease-cycle-01",
        requested_cores=8,
    )
    assert eval_res.allowed
    assert lease.status == LeaseStatus.ACTIVE
    initial_expires = lease.expires_at

    # Heartbeat extension
    ok, msg = mgr.heartbeat(vm.hypervisor_uuid)
    assert ok
    db_session.refresh(lease)
    assert lease.expires_at >= initial_expires


def test_graceful_stopping_reserves_lease(db_session):
    """Test that graceful stopping signal marks VM STOPPING but keeps core lease reserved."""
    mgr = LeaseManager(db_session)
    vm = mgr.register_vm(hostname="ws2025-stopping", hypervisor_uuid="uuid-stop-001", core_count=8)
    lease, _ = mgr.allocate_lease(vm.hypervisor_uuid, "req-stop-01", 8)

    # Agent notifies stopping
    ok = mgr.notify_stopping(vm.hypervisor_uuid)
    assert ok
    db_session.refresh(vm)
    db_session.refresh(lease)

    assert vm.current_state == VMState.STOPPING
    assert lease.status == LeaseStatus.ACTIVE  # Kept reserved!

    # Cores must remain counted as allocated
    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 8


def test_authoritative_release_releases_cores(db_session):
    """Test that authoritative release cleanly releases cores and updates lease status."""
    hyp = MockHypervisorAdapter()
    hyp.register_simulated_vm("uuid-auth-release", "ws2025-auth", HypervisorPowerState.RUNNING)

    mgr = LeaseManager(db_session, hypervisor=hyp)
    vm = mgr.register_vm(hostname="ws2025-auth", hypervisor_uuid="uuid-auth-release", core_count=8)
    lease, _ = mgr.allocate_lease(vm.hypervisor_uuid, "req-auth-01", 8)

    # Attempt to release while hypervisor still reports RUNNING should fail
    ok, msg = mgr.release_lease(vm.hypervisor_uuid, reason="test_shutdown", force=False)
    assert not ok
    assert "Hypervisor confirms VM is still RUNNING" in msg

    # Now hypervisor confirms STOPPED
    hyp.set_vm_power_state("uuid-auth-release", HypervisorPowerState.STOPPED)
    ok, msg = mgr.release_lease(vm.hypervisor_uuid, reason="hypervisor_confirmed_stop", force=False)
    assert ok

    db_session.refresh(lease)
    db_session.refresh(vm)
    assert lease.status == LeaseStatus.RELEASED
    assert lease.release_reason == "hypervisor_confirmed_stop"
    assert vm.current_state == VMState.STOPPED

    # Cores must be freed
    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 0
    assert summary["available_cores"] == 80
