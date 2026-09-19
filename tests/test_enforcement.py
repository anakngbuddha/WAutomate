"""Tests for Tier 1 & Tier 2 admission control and enforcement API."""

import pytest
from fastapi import status
from weautomate.database.models import VirtualMachine, VMState, Lease, LeaseStatus
from weautomate.config import settings


def test_admission_control_permits_start_when_capacity_available(client, db_session):
    """Tier 1/2 start gate permits boot when cores are available."""
    vm = VirtualMachine(
        hostname="ws2025-gate-01",
        hypervisor_uuid="uuid-gate-001",
        core_count=8,
        server_farm=settings.server_farm_name,
        current_state=VMState.STOPPED,
    )
    db_session.add(vm)
    db_session.commit()

    resp = client.post(
        "/api/v1/enforcement/request-start",
        json={"hypervisor_uuid": "uuid-gate-001", "requested_cores": 8, "actor": "test_operator"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["authorized"] is True
    assert data["cores"] == 8
    assert "lease_id" in data


def test_admission_control_denies_start_when_pool_exhausted(client, db_session):
    """Tier 1/2 start gate denies boot when core pool is exhausted."""
    # Pre-occupy 80 cores with 10 VMs
    for i in range(10):
        vm = VirtualMachine(
            hostname=f"occupant-vm-{i:02d}",
            hypervisor_uuid=f"uuid-occupant-{i:02d}",
            core_count=8,
            server_farm=settings.server_farm_name,
            current_state=VMState.RUNNING,
        )
        db_session.add(vm)
        db_session.flush()

        lease = Lease(
            entitlement_id=1,
            vm_id=vm.id,
            request_id=f"req-occupant-{i:02d}",
            cores_allocated=8,
            status=LeaseStatus.ACTIVE,
            granted_at=vm.created_at,
            expires_at=vm.created_at,
        )
        db_session.add(lease)
    db_session.commit()

    # Register 11th VM
    vm_11 = VirtualMachine(
        hostname="denied-vm-11",
        hypervisor_uuid="uuid-denied-011",
        core_count=8,
        server_farm=settings.server_farm_name,
        current_state=VMState.STOPPED,
    )
    db_session.add(vm_11)
    db_session.commit()

    # Attempt to start 11th VM
    resp = client.post(
        "/api/v1/enforcement/request-start",
        json={"hypervisor_uuid": "uuid-denied-011", "requested_cores": 8},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    data = resp.json()
    assert data["detail"]["authorized"] is False
    assert "Insufficient core capacity" in data["detail"]["reason"]
