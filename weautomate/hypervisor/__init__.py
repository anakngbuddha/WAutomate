"""Hypervisor adapters package."""

from weautomate.hypervisor.base import (
    HypervisorAdapter,
    HypervisorPowerState,
    HypervisorVMInfo,
)
from weautomate.hypervisor.mock import MockHypervisorAdapter
from weautomate.hypervisor.hyperv import HyperVAdapter

__all__ = [
    "HypervisorAdapter",
    "HypervisorPowerState",
    "HypervisorVMInfo",
    "MockHypervisorAdapter",
    "HyperVAdapter",
]
