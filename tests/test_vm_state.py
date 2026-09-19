"""Tests for VM state detection and strict unreachable non-release policy."""

import pytest
from datetime import timedelta
from weautomate.controller.lease_manager import LeaseManager
from weautomate.database.models import VMState, LeaseStatus, utc_now
from weautomate.config import settings


def test_heartbeat_timeout_flags_unreachable_without_releasing_lease(db_session):
    """CRITICAL TEST: Verifies that a lost heartbeat marks a VM as UNREACHABLE,

    but does NOT release its core lease. Auto-releasing on heartbeat loss alone
    is strictly forbidden because network partition looks identical to shutdown.
    """
    mgr = LeaseManager(db_session)
    vm = mgr.register_vm(
        hostname="ws2025-flaky-network",
        hypervisor_uuid="uuid-flaky-001",
        core_count=8,
    )
    lease, _ = mgr.allocate_lease(vm.hypervisor_uuid, "req-flaky-001", 8)
    assert vm.current_state == VMState.RUNNING

    # Artificially age the last_heartbeat past the lease duration
    vm.last_heartbeat = utc_now() - timedelta(seconds=settings.lease_duration_seconds + 30)
    db_session.commit()

    # Scanner detects expired heartbeat
    unreachable_vms = mgr.scan_unreachable_vms()
    assert len(unreachable_vms) == 1
    assert unreachable_vms[0].id == vm.id

    db_session.refresh(vm)
    db_session.refresh(lease)

    # VM state must be UNREACHABLE
    assert vm.current_state == VMState.UNREACHABLE

    # CRITICAL: Lease MUST still be ACTIVE!
    assert lease.status == LeaseStatus.ACTIVE
    assert lease.released_at is None

    # Available cores must still reflect that these 8 cores are reserved
    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 8
    assert summary["available_cores"] == 72


def test_unreachable_vm_recovers_on_heartbeat(db_session):
    """Test that an UNREACHABLE VM recovers to RUNNING when network heals and heartbeat arrives."""
    mgr = LeaseManager(db_session)
    vm = mgr.register_vm(hostname="ws2025-healed", hypervisor_uuid="uuid-heal-001", core_count=8)
    mgr.allocate_lease(vm.hypervisor_uuid, "req-heal-01", 8)

    vm.current_state = VMState.UNREACHABLE
    db_session.commit()

    # Heartbeat arrives from agent
    ok, _ = mgr.heartbeat(vm.hypervisor_uuid)
    assert ok

    db_session.refresh(vm)
    assert vm.current_state == VMState.RUNNING
