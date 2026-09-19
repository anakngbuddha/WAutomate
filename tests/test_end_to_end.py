"""End-to-end integration test simulating the entire 10-VM pool lifecycle.

Covers:
- 10 VMs sharing a fixed 80-core FVB pool (8 cores each).
- Starting 10 VMs reaches 80/80 cores allocated.
- 11th VM start request is blocked by admission control.
- Normal shutdown of VM 1 releases its 8 cores.
- 11th VM is now admitted and boots.
- VM 2 experiences a network partition (unreachable): cores remain reserved.
- 12th VM is rejected because unreachable VM's cores are protected.
- Authoritative shutdown of VM 2 releases its lease; 12th VM starts successfully.
"""

import pytest
from weautomate.controller.lease_manager import LeaseManager
from weautomate.hypervisor.mock import MockHypervisorAdapter, HypervisorPowerState
from weautomate.database.models import VMState, LeaseStatus
from weautomate.config import settings


def test_full_pool_lifecycle_10_vms(db_session):
    hyp = MockHypervisorAdapter()
    mgr = LeaseManager(db_session, hypervisor=hyp)

    # 1. Register 10 VMs
    vms = []
    for i in range(1, 11):
        uuid = f"vm-node-{i:02d}-uuid"
        name = f"WS2025-NODE-{i:02d}"
        hyp.register_simulated_vm(uuid, name, HypervisorPowerState.STOPPED, core_count=8)
        vm = mgr.register_vm(hostname=name, hypervisor_uuid=uuid, core_count=8)
        vms.append(vm)

    # 2. Start and allocate all 10 VMs
    for i, vm in enumerate(vms, start=1):
        hyp.start_vm(vm.hypervisor_uuid)
        lease, eval_res = mgr.allocate_lease(
            hypervisor_uuid=vm.hypervisor_uuid,
            request_id=f"req-boot-node-{i:02d}",
            requested_cores=8,
        )
        assert eval_res.allowed, f"VM {i} should be allowed"
        assert lease.status == LeaseStatus.ACTIVE

    # Verify pool is at 100% capacity (80/80 cores allocated)
    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 80
    assert summary["available_cores"] == 0

    # 3. Attempt to allocate an 11th VM -> MUST BE REJECTED
    hyp.register_simulated_vm("vm-node-11-uuid", "WS2025-NODE-11", HypervisorPowerState.STOPPED, core_count=8)
    vm_11 = mgr.register_vm(hostname="WS2025-NODE-11", hypervisor_uuid="vm-node-11-uuid", core_count=8)

    lease_11, eval_11 = mgr.allocate_lease(
        hypervisor_uuid=vm_11.hypervisor_uuid,
        request_id="req-boot-node-11",
        requested_cores=8,
    )
    assert not eval_11.allowed
    assert lease_11 is None
    assert "Insufficient core capacity" in eval_11.reason

    # 4. Graceful shutdown of VM 1
    # Step A: Agent notifies stopping
    mgr.notify_stopping(vms[0].hypervisor_uuid)
    db_session.refresh(vms[0])
    assert vms[0].current_state == VMState.STOPPING

    # Cores must still be reserved during STOPPING
    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 80

    # Step B: Hypervisor powers off VM 1
    hyp.stop_vm(vms[0].hypervisor_uuid)

    # Step C: Authoritative release
    released, msg = mgr.release_lease(
        hypervisor_uuid=vms[0].hypervisor_uuid,
        reason="node_01_planned_maintenance",
        force=False,
    )
    assert released
    db_session.refresh(vms[0])
    assert vms[0].current_state == VMState.STOPPED

    # Pool now has 8 cores free
    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 72
    assert summary["available_cores"] == 8

    # 5. VM 11 can now acquire lease
    hyp.start_vm(vm_11.hypervisor_uuid)
    lease_11, eval_11 = mgr.allocate_lease(
        hypervisor_uuid=vm_11.hypervisor_uuid,
        request_id="req-boot-node-11-retry",
        requested_cores=8,
    )
    assert eval_11.allowed
    assert lease_11 is not None
    assert lease_11.cores_allocated == 8

    # Pool back to 80/80
    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 80

    # 6. Simulate Network Partition on VM 2
    # Heartbeat stops, but VM is still physically RUNNING on hypervisor
    from datetime import timedelta
    from weautomate.database.models import utc_now
    vms[1].last_heartbeat = utc_now() - timedelta(seconds=settings.lease_duration_seconds + 30)
    db_session.commit()

    unreachable = mgr.scan_unreachable_vms()
    assert len(unreachable) >= 1
    db_session.refresh(vms[1])
    assert vms[1].current_state == VMState.UNREACHABLE

    # Pool MUST STILL BE 80 cores allocated! Unreachable does NOT release!
    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 80
    assert summary["available_cores"] == 0

    # Attempt to start 12th VM -> MUST BE REJECTED
    hyp.register_simulated_vm("vm-node-12-uuid", "WS2025-NODE-12", HypervisorPowerState.STOPPED, core_count=8)
    vm_12 = mgr.register_vm(hostname="WS2025-NODE-12", hypervisor_uuid="vm-node-12-uuid", core_count=8)
    lease_12, eval_12 = mgr.allocate_lease(vm_12.hypervisor_uuid, "req-boot-node-12", 8)
    assert not eval_12.allowed

    # 7. Authoritative Hypervisor Confirmation of VM 2 stop
    hyp.stop_vm(vms[1].hypervisor_uuid)
    released_2, _ = mgr.release_lease(vms[1].hypervisor_uuid, reason="hypervisor_confirmed_down", force=False)
    assert released_2

    # Now VM 12 can start!
    hyp.start_vm(vm_12.hypervisor_uuid)
    lease_12, eval_12 = mgr.allocate_lease(vm_12.hypervisor_uuid, "req-boot-node-12-retry", 8)
    assert eval_12.allowed
    assert lease_12 is not None

    summary = mgr.policy_engine.get_entitlement_summary()
    assert summary["allocated_cores"] == 80
