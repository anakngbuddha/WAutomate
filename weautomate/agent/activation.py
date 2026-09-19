"""Windows activation telemetry and KMS status queries.

CRITICAL ARCHITECTURAL POLICY:
Release never touches Windows' activation state (slmgr /upk is strictly forbidden).
Reclaiming core entitlements is governed by hypervisor power state, not in-guest activation changes.
"""

import subprocess
from typing import Dict, Any


def get_windows_activation_status() -> Dict[str, Any]:
    """Queries Windows licensing status via CIM/WMI without modifying activation state."""
    ps_cmd = (
        "Get-CimInstance -ClassName SoftwareLicensingProduct -Filter 'PartialProductKey is not null' | "
        "Where-Object { $_.Name -like '*Windows*' } | "
        "Select-Object -Property LicenseStatus, Description, Name | "
        "ConvertTo-Json -Compress"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = res.stdout.strip()
        if output:
            # LicenseStatus 1 = Licensed, 2 = OOBGrace, 3 = OOTGrace, 4 = NonGenuine, 5 = Notification
            return {"raw": output, "status": "QuerySuccess"}
    except Exception as e:
        return {"raw": str(e), "status": "QueryUnavailable"}

    return {"status": "Simulated/Licensed", "channel": "Volume:GVLK"}
