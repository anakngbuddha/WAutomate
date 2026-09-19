"""KMS (Key Management Service) client GVLK and host configuration validation."""

import re
import socket
from typing import Dict, Any, List

WINDOWS_2025_STANDARD_GVLK = "TVRH6-WHNXV-R9WG3-9XRFY-MY832"
GVLK_PATTERN = re.compile(r"^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$")


def validate_gvlk(key: str) -> bool:
    """Validates 5x5 product key format."""
    return bool(GVLK_PATTERN.match(key.strip().upper()))


def check_kms_host_connectivity(host: str, port: int = 1688, timeout: float = 3.0) -> bool:
    """Checks whether the Volume Activation KMS host is reachable on TCP port 1688."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def get_kms_configuration_summary() -> Dict[str, Any]:
    """Provides reference and validation data for Windows Server 2025 KMS activation."""
    return {
        "operating_system": "Windows Server 2025 Standard",
        "client_gvlk": WINDOWS_2025_STANDARD_GVLK,
        "default_kms_port": 1688,
        "role": "Volume Activation Services",
        "guidance": (
            "1. Install GVLK on client VM: slmgr /ipk TVRH6-WHNXV-R9WG3-9XRFY-MY832\n"
            "2. Set KMS host: slmgr /skms <kms-host-ip-or-fqdn>:1688\n"
            "3. Trigger activation: slmgr /ato\n"
            "4. NEVER call 'slmgr /upk' on release (release is governed strictly by controller + hypervisor power state)."
        ),
    }
