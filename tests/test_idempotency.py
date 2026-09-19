"""Tests for idempotent core lease allocation via request_id."""

import pytest
from weautomate.controller.lease_manager import LeaseManager
from weautomate.database.models import VirtualMachine, LeaseStatus, Lease
from weautomate.config import settings


def test_idempotent_allocation_same_request_id(db_session):
    """Verifies that calling allocate_lease multiple times with the same request_id does NOT allocate duplicate cores."""
    mgr = LeaseManager(db_session)
    vm = mgr.register_vm(
        hostname="ws2025-node-01",
        hypervisor_uuid="f47ac10b-58cc-4372-a567-0e02b2c3d479",
        core_count=8,
        server_farm=settings.server_farm_name,
    )

    request_id = "req-idempotency-test-12345"

    # Call 1: First allocation
    lease1, eval1 = mgr.allocate_lease(
        hypervisor_uuid=vm.hypervisor_uuid,
        request_id=request_id,
        requested_cores=8,
    )
    assert eval1.allowed
    assert lease1 is not None
    assert lease1.cores_allocated == 8
    assert lease1.status == LeaseStatus.ACTIVE

    # Check total active leases in database
    active_count_1 = db_session.query(Lease).filter(Lease.status == LeaseStatus.ACTIVE).count()
    assert active_count_1 == 1

    # Call 2: Exact same request_id (simulating network retry)
    lease2, eval2 = mgr.allocate_lease(
        hypervisor_uuid=vm.hypervisor_uuid,
        request_id=request_id,
        requested_cores=8,
    )
    assert eval2.allowed
    assert lease2.id == lease1.id  # Must return identical lease
    assert lease2.request_id == request_id
    assert eval2.details.get("idempotent") is True

    # Call 3: Third attempt
    lease3, eval3 = mgr.allocate_lease(
        hypervisor_uuid=vm.hypervisor_uuid,
        request_id=request_id,
        requested_cores=8,
    )
    assert lease3.id == lease1.id

    # Total active leases in database must still be exactly 1
    active_count_final = db_session.query(Lease).filter(Lease.status == LeaseStatus.ACTIVE).count()
    assert active_count_final == 1

    # Total allocated cores must still be 8, not 24
    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 8
    assert summary["available_cores"] == 72
