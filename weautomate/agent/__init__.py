"""VM Agent package."""

from weautomate.agent.agent import VMAgent
from weautomate.agent.hardware import get_hypervisor_uuid, get_core_count, get_hostname
from weautomate.agent.activation import get_windows_activation_status

__all__ = [
    "VMAgent",
    "get_hypervisor_uuid",
    "get_core_count",
    "get_hostname",
    "get_windows_activation_status",
]
