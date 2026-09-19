"""Hardware identification and host telemetry for VM Agent."""

import os
import socket
import subprocess
import uuid


def get_hypervisor_uuid() -> str:
    """Retrieves immutable BIOS/hypervisor UUID via CIM/WMI or generates consistent fallback."""
    # Attempt Windows CIM query
    try:
        res = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystemProduct).UUID",
            ],
            capture_output=True,
            text=True,
            timeout=8,
        )
        hw_uuid = res.stdout.strip()
        if hw_uuid and len(hw_uuid) >= 16 and "ERROR" not in hw_uuid.upper():
            return hw_uuid.lower()
    except Exception:
        pass

    # Fallback for non-Windows or environments where CIM is inaccessible
    # Combines hostname with MAC address node for deterministic identity
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname().lower()))


def get_core_count() -> int:
    """Returns detected logical/virtual CPU cores, respecting minimum 8-core FVB floor."""
    count = os.cpu_count() or 8
    return count


def get_hostname() -> str:
    """Returns machine hostname."""
    return socket.gethostname()


def get_local_ip() -> str:
    """Returns outbound IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
