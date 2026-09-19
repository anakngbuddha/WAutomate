"""Hyper-V platform adapter for Windows Server environments."""

import json
import subprocess
from typing import List, Optional
from weautomate.hypervisor.base import (
    HypervisorAdapter,
    HypervisorPowerState,
    HypervisorVMInfo,
)


class HyperVAdapter(HypervisorAdapter):
    """Hyper-V management adapter utilizing PowerShell CimInstance / Get-VM."""

    def _run_ps(self, cmd: str) -> str:
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
            return res.stdout.strip()
        except Exception:
            return ""

    def get_vm_power_state(self, hypervisor_uuid: str) -> HypervisorPowerState:
        ps_cmd = (
            f"Get-VM | Where-Object {{ $_.Id.ToString() -eq '{hypervisor_uuid}' }} | "
            f"Select-Object -ExpandProperty State"
        )
        output = self._run_ps(ps_cmd).upper()
        if not output:
            return HypervisorPowerState.NOT_FOUND
        if "RUNNING" in output:
            return HypervisorPowerState.RUNNING
        if "OFF" in output or "STOPPED" in output:
            return HypervisorPowerState.STOPPED
        if "PAUSED" in output or "SUSPENDED" in output:
            return HypervisorPowerState.SUSPENDED
        return HypervisorPowerState.UNKNOWN

    def list_vms(self) -> List[HypervisorVMInfo]:
        ps_cmd = (
            "Get-VM | Select-Object Id, Name, State, ProcessorCount | "
            "ConvertTo-Json -Compress"
        )
        output = self._run_ps(ps_cmd)
        if not output:
            return []
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                data = [data]
            vms = []
            for item in data:
                raw_state = str(item.get("State", "")).upper()
                if "RUNNING" in raw_state:
                    state = HypervisorPowerState.RUNNING
                elif "OFF" in raw_state or "STOPPED" in raw_state:
                    state = HypervisorPowerState.STOPPED
                else:
                    state = HypervisorPowerState.UNKNOWN
                vms.append(
                    HypervisorVMInfo(
                        hypervisor_uuid=str(item.get("Id", "")),
                        hostname=str(item.get("Name", "")),
                        power_state=state,
                        core_count=int(item.get("ProcessorCount", 8)),
                    )
                )
            return vms
        except Exception:
            return []

    def start_vm(self, hypervisor_uuid: str) -> bool:
        ps_cmd = f"Start-VM -Id '{hypervisor_uuid}' -ErrorAction SilentlyContinue"
        res = self._run_ps(ps_cmd)
        return True

    def stop_vm(self, hypervisor_uuid: str, graceful: bool = True) -> bool:
        flag = "-SaveState" if not graceful else ""
        ps_cmd = f"Stop-VM -Id '{hypervisor_uuid}' {flag} -ErrorAction SilentlyContinue"
        self._run_ps(ps_cmd)
        return True
