"""Tests for Microsoft Flexible Virtualization Benefit (FVB) licensing policy compliance."""

import pytest
from weautomate.controller.policy import LicensingPolicyEngine
from weautomate.database.models import VirtualMachine, VMState, Entitlement, LicenseType
from weautomate.config import settings


def test_fvb_minimum_8_cores_per_vm(db_session):
    """Test that requesting fewer than 8 cores per VM is rejected under FVB."""
    engine = LicensingPolicyEngine(db_session)
    vm = VirtualMachine(
        hostname="small-vm",
        hypervisor_uuid="uuid-small-001",
        core_count=4,  # Below 8-core minimum
        server_farm=settings.server_farm_name,
        current_state=VMState.STOPPED,
    )
    db_session.add(vm)
    db_session.commit()

    result = engine.evaluate_allocation(vm, requested_cores=4)
    assert not result.allowed
    assert "8-core minimum" in result.reason


def test_fvb_org_wide_16_core_floor(db_session):
    """Test that an organization entitlement pool under 16 cores is rejected."""
    # Delete default 80-core entitlement and replace with 12 cores
    db_session.query(Entitlement).delete()
    sub_floor_entitlement = Entitlement(
        product="Windows Server",
        edition="Standard",
        version="2025",
        license_type=LicenseType.SUBSCRIPTION,
        core_quantity=12,  # Sub-floor
        agreement_ref="MS-SUB-FLOOR",
    )
    db_session.add(sub_floor_entitlement)
    db_session.commit()

    engine = LicensingPolicyEngine(db_session)
    vm = VirtualMachine(
        hostname="test-vm",
        hypervisor_uuid="uuid-test-001",
        core_count=8,
        server_farm=settings.server_farm_name,
        current_state=VMState.STOPPED,
    )
    db_session.add(vm)
    db_session.commit()

    result = engine.evaluate_allocation(vm, requested_cores=8)
    assert not result.allowed
    assert "16-core minimum floor" in result.reason


def test_server_farm_boundary_check(db_session):
    """Test that VMs in a different server farm cannot consume the license pool."""
    engine = LicensingPolicyEngine(db_session)
    vm = VirtualMachine(
        hostname="foreign-farm-vm",
        hypervisor_uuid="uuid-foreign-001",
        core_count=8,
        server_farm="external-farm-secondary",
        current_state=VMState.STOPPED,
    )
    db_session.add(vm)
    db_session.commit()

    result = engine.evaluate_allocation(vm, requested_cores=8)
    assert not result.allowed
    assert "Server farm mismatch" in result.reason


def test_capacity_exhaustion_prevention(db_session):
    """Test that allocation is rejected when the available core pool is exhausted."""
    engine = LicensingPolicyEngine(db_session)
    # Available cores is 80
    vm = VirtualMachine(
        hostname="huge-vm",
        hypervisor_uuid="uuid-huge-001",
        core_count=96,  # Demands 96 cores from 80-core pool
        server_farm=settings.server_farm_name,
        current_state=VMState.STOPPED,
    )
    db_session.add(vm)
    db_session.commit()

    result = engine.evaluate_allocation(vm, requested_cores=96)
    assert not result.allowed
    assert "Insufficient core capacity" in result.reason
