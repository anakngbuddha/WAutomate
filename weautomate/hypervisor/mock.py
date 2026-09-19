"""Mock hypervisor adapter for tests and local simulation."""

from typing import Dict, List, Optional
from weautomate.hypervisor.base import (
    HypervisorAdapter,
    HypervisorPowerState,
    HypervisorVMInfo,
)


class MockHypervisorAdapter(HypervisorAdapter):
    """In-memory hypervisor state adapter for automated testing and simulation."""

    def __init__(self):
        self._vms: Dict[str, HypervisorVMInfo] = {}

    def register_simulated_vm(
        self,
        hypervisor_uuid: str,
        hostname: str,
        power_state: HypervisorPowerState = HypervisorPowerState.STOPPED,
        core_count: int = 8,
        ip_address: Optional[str] = "192.168.1.100",
    ) -> HypervisorVMInfo:
        info = HypervisorVMInfo(
            hypervisor_uuid=hypervisor_uuid,
            hostname=hostname,
            power_state=power_state,
            core_count=core_count,
            ip_address=ip_address,
        )
        self._vms[hypervisor_uuid] = info
        return info

    def set_vm_power_state(self, hypervisor_uuid: str, state: HypervisorPowerState):
        if hypervisor_uuid in self._vms:
            self._vms[hypervisor_uuid].power_state = state
        else:
            self._vms[hypervisor_uuid] = HypervisorVMInfo(
                hypervisor_uuid=hypervisor_uuid,
                hostname=f"vm-{hypervisor_uuid[:8]}",
                power_state=state,
                core_count=8,
            )

    def remove_vm(self, hypervisor_uuid: str):
        if hypervisor_uuid in self._vms:
            del self._vms[hypervisor_uuid]

    def get_vm_power_state(self, hypervisor_uuid: str) -> HypervisorPowerState:
        if hypervisor_uuid not in self._vms:
            return HypervisorPowerState.NOT_FOUND
        return self._vms[hypervisor_uuid].power_state

    def list_vms(self) -> List[HypervisorVMInfo]:
        return list(self._vms.values())

    def start_vm(self, hypervisor_uuid: str) -> bool:
        if hypervisor_uuid in self._vms:
            self._vms[hypervisor_uuid].power_state = HypervisorPowerState.RUNNING
            return True
        return False

    def stop_vm(self, hypervisor_uuid: str, graceful: bool = True) -> bool:
        if hypervisor_uuid in self._vms:
            self._vms[hypervisor_uuid].power_state = HypervisorPowerState.STOPPED
            return True
        return False
