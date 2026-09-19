"""Abstract base class and types for Hypervisor / Cloud Platform adapters."""

from abc import ABC, abstractmethod
import enum
from dataclasses import dataclass
from typing import Optional, List, Dict


class HypervisorPowerState(str, enum.Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"


@dataclass
class HypervisorVMInfo:
    hypervisor_uuid: str
    hostname: str
    power_state: HypervisorPowerState
    core_count: int
    ip_address: Optional[str] = None
    extra_metadata: Optional[Dict[str, str]] = None


class HypervisorAdapter(ABC):
    """Abstract interface defining authoritative cloud/hypervisor power-state interactions."""

    @abstractmethod
    def get_vm_power_state(self, hypervisor_uuid: str) -> HypervisorPowerState:
        """Returns authoritative power state for a specific VM."""
        pass

    @abstractmethod
    def list_vms(self) -> List[HypervisorVMInfo]:
        """Discovers all VMs present on the hypervisor/cloud host."""
        pass

    @abstractmethod
    def start_vm(self, hypervisor_uuid: str) -> bool:
        """Boots a VM (used in Tier 2 controller-gated RBAC start flow)."""
        pass

    @abstractmethod
    def stop_vm(self, hypervisor_uuid: str, graceful: bool = True) -> bool:
        """Shuts down a VM on the hypervisor."""
        pass
