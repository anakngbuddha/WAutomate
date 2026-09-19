# WeAutomate: Windows Server 2025 Dynamic License Controller & Agent
## Complete End-to-End Deployment & Operations Guide

This guide details how to install, configure, and operate the **License Controller** on the Master Manager VM and the **VM Agent** on each Windows Server 2025 VM under Microsoft's Flexible Virtualization Benefit (FVB).

---

## Architecture Topology

```
                  ┌────────────────────────────────────────────────────────┐
                  │       HYPERVISOR / PRIVATE CLOUD PLATFORM              │
                  │       (Hyper-V, Proxmox, VMware, or oVirt)             │
                  └──────────────┬──────────────────────────┬──────────────┘
            Authoritative Power  │                          │ Authoritative Power
            State Control API    │                          │ State Queries
                                 ▼                          │
   ┌──────────────────────────────────────────────────┐     │
   │        MASTER CONTROLLER VM (Manager VM)         │     │
   │  • License Controller API (FastAPI)              │     │
   │  • PostgreSQL / SQLite State Store               │     │
   │  • Reconciliation Engine                         │     │
   │  • Web Management Dashboard (Port 8000)          │     │
   │  • Append-Only Audit Log                         │     │
   └─────────────────────────────▲────────────────────┘     │
                                 │                          │
                 Outbound HTTPS  │ (Agent initiated only!   │
                 Heartbeats      │  NO inbound ports on VM) │
                                 │                          ▼
                    ┌────────────┴─────────────────────────────────────┐
                    │     TARGET WINDOWS SERVER 2025 VMs (Pool)        │
                    │                                                  │
                    │   ┌──────────────────────────────────────────┐   │
                    │   │ VM 01 (8 Cores)                          │   │
                    │   │ • GVLK: TVRH6-WHNXV-R9WG3-9XRFY-MY832    │   │
                    │   │ • WeAutomate Agent (Scheduled Task)      │   │
                    │   └────────────────────┬─────────────────────┘   │
                    │                        │                         │
                    │   ┌────────────────────┴─────────────────────┐   │
                    │   │ VM 02 (8 Cores)                          │   │
                    │   │ • GVLK: TVRH6-WHNXV-R9WG3-9XRFY-MY832    │   │
                    │   │ • WeAutomate Agent (Scheduled Task)      │   │
                    │   └────────────────────┬─────────────────────┘   │
                    └────────────────────────┼─────────────────────────┘
                                             │
                                             ▼
                    ┌──────────────────────────────────────────────────┐
                    │     KMS ACTIVATION HOST (Port 1688)              │
                    │     Volume Activation Services (CSVLK Host)      │
                    └──────────────────────────────────────────────────┘
```

---

## Roles & Network Requirements

| Node | Software / Role | Inbound Ports | Outbound Ports |
|---|---|---|---|
| **Manager VM (Controller)** | Python 3.10+, FastAPI, Uvicorn, SQLite/PostgreSQL | **TCP 8000** (API / Dashboard) | Hypervisor API (e.g. WMI / REST) |
| **Worker VMs (Targets)** | Windows Server 2025 Standard, WeAutomate Agent | **None required** | **TCP 8000** (to Controller), **TCP 1688** (to KMS) |
| **KMS Host** | Volume Activation Services | **TCP 1688** (KMS protocol) | None |

---

## Part 1: Setting Up the Master Controller (Manager VM)

### Step 1.1: System Requirements on Manager VM
- Windows Server 2022/2025 or Ubuntu 22.04+ / Debian 12.
- Python 3.10 or higher installed.

### Step 1.2: Deploy Controller Files & Dependencies
1. Place the `WeAutomate` codebase into `C:\WeAutomate` (or `/opt/weautomate` on Linux).
2. Open PowerShell as Administrator and install required Python packages:
   ```powershell
   cd C:\WeAutomate
   python -m pip install -r requirements.txt
   # Or install core dependencies:
   python -m pip install fastapi uvicorn sqlalchemy alembic pydantic httpx
   ```

### Step 1.3: Initialize the Database
The Controller automatically initializes its tables and default 80-core FVB entitlement on startup. If using PostgreSQL in production:
```powershell
# Set environment variables (Optional, defaults to local SQLite):
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/weautomate"
$env:SERVER_FARM_NAME = "primary-server-farm"
$env:ENFORCEMENT_TIER = "1"
```

### Step 1.4: Run the Controller as a Persistent Windows Service
You can run the controller as a Windows background task or Windows Service using PowerShell:

#### Option A: Windows Task Scheduler (Runs on Boot as SYSTEM)
```powershell
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "-m uvicorn weautomate.controller.app:app --host 0.0.0.0 --port 8000" -WorkingDirectory "C:\WeAutomate"
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "WeAutomateController" -Action $Action -Trigger $Trigger -Principal $Principal
Start-ScheduledTask -TaskName "WeAutomateController"
```

#### Option B: NSSM (Non-Sucking Service Manager)
```powershell
nssm install WeAutomateController "C:\Python312\python.exe" "-m uvicorn weautomate.controller.app:app --host 0.0.0.0 --port 8000"
nssm set WeAutomateController AppDirectory "C:\WeAutomate"
nssm start WeAutomateController
```

### Step 1.5: Configure Firewall on Manager VM
Allow inbound traffic on port 8000:
```powershell
New-NetFirewallRule -DisplayName "WeAutomate License Controller" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### Step 1.6: Verify Controller & Dashboard
Open your browser on your workstation:
```
http://<MANAGER-VM-IP>:8000/dashboard/
```
You will see the live glassmorphic dashboard showing **80 Total Cores**, **0 Allocated Cores**, **80 Available Cores**, and the Tripartite Authority badges.

---

## Part 2: Setting Up the KMS Activation Host

Per Section 5 of the plan, KMS is configured using Microsoft standard Volume Activation Services:

1. **Install Volume Activation Role** on your designated KMS Host VM:
   ```powershell
   Install-WindowsFeature -Name VolumeActivation -IncludeManagementTools
   ```
2. **Install your Customer-Specific CSVLK** (obtained from the Microsoft Volume Licensing Service Center / M365 Admin Portal):
   ```cmd
   slmgr.vbs /ipk <YOUR-MICROSOFT-CSVLK-KEY>
   slmgr.vbs /ato
   ```
3. **Verify DNS SRV publishing**:
   KMS automatically creates a DNS record: `_vlmcs._tcp.<your-domain>`.
   Verify from any client VM:
   ```powershell
   Resolve-DnsName -Type SRV _vlmcs._tcp
   ```

---

## Part 3: Installing the Agent on Each Target Windows Server 2025 VM

Each target VM runs the lightweight outbound agent.

### Step 3.1: Configure Windows Server 2025 GVLK
Ensure the public Windows Server 2025 Standard Client Setup Key (GVLK) is installed:
```cmd
slmgr.vbs /ipk TVRH6-WHNXV-R9WG3-9XRFY-MY832
slmgr.vbs /skms <KMS-HOST-IP-OR-FQDN>:1688
slmgr.vbs /ato
```

### Step 3.2: Automated Agent Installation
Run the provided installer script as Administrator on each VM:
```powershell
# Run from repository or network share:
.\scripts\install-agent.ps1 -ControllerUrl "http://<MANAGER-VM-IP>:8000" -ServerFarm "primary-server-farm"
```

What the script does automatically:
1. Copies agent binaries to `C:\Program Files\WeAutomate\Agent`.
2. Creates `C:\ProgramData\WeAutomate\` for the local cache (`agent_cache.json`).
3. Extracts the immutable hardware BIOS/hypervisor UUID (`(Get-CimInstance Win32_ComputerSystemProduct).UUID`).
4. Registers a persistent background task (`WeAutomateVMAgent`) that executes on system startup.
5. Sends an outbound registration request to the Controller.

---

## Part 4: How It Works & Functional Lifecycle

### 1. Boot & Admission Control (Gating Starts)
```
Operator/Automation                     Controller API                           Hypervisor / Cloud
        │                                     │                                          │
        ├─── POST /enforcement/request-start ─►                                          │
        │    (Check available cores)          │                                          │
        │                                     ├── Evaluate Policy (8 core min, capacity) │
        │                                     │                                          │
        │                                     ├── [If Capacity Exceeded] ────────────────► DENY (HTTP 403)
        │                                     │                                          │
        │                                     └── [If Capacity Available] ───────────────► Start VM
        ◄─── 200 OK (Admission Granted) ──────┘                                          ▼
                                                                                   VM Powers On
```

- **Tier 1 (Pre-Boot Hook)**: When an admin or script calls `POST /api/v1/enforcement/request-start`, the Controller evaluates the core balance. If available, it issues a reservation and powers on the VM. If the 80 cores are full, the start is **blocked** immediately.

### 2. In-Guest Registration & Idempotent Lease Acquisition
- Once Windows boots, the agent reads its hardware UUID and contacts the Controller via outbound HTTP/HTTPS:
  - `POST /api/v1/vms/register`: Registers hostname, UUID, core count (8), and server farm.
  - `POST /api/v1/leases/allocate`: Uses a persisted `request_id` (`agent_cache.json`).
  - **Idempotency Guarantee**: If the agent restarts or connectivity blips, re-sending the same `request_id` returns the existing lease without consuming extra cores.

### 3. Continuous Heartbeat Renewal
- Every 30 seconds, the agent sends:
  - `POST /api/v1/leases/heartbeat` with its UUID.
- The controller extends `expires_at = now + 90s` and updates `last_heartbeat`.

### 4. Network Partition / Unreachable Safety (Strict Rule)
- If a VM loses network connectivity, its heartbeat stops reaching the controller.
- After 90 seconds, the Controller flags the VM as **`UNREACHABLE`**.
- **CRITICAL COMPLIANCE GUARANTEE**: The Controller **DOES NOT AUTO-RELEASE** the core lease.
- Why? A running VM with a broken network cable is still consuming licensed cores. Auto-releasing on heartbeat loss would cause over-allocation. The cores remain safely reserved.
- When network connectivity returns, the next heartbeat automatically recovers the VM back to **`RUNNING`**.

### 5. Graceful Shutdown & Authoritative Release
```
VM Guest Agent                          Controller API                           Hypervisor / Cloud
      │                                       │                                          │
      ├─── POST /vms/stopping ────────────────►                                          │
      │    (Shutdown initiated)               ├── Mark VM "STOPPING"                     │
      │                                       │   (Keep cores reserved)                  │
      ▼                                       │                                          ▼
[VM Powers Off]                               │                                   [Status: STOPPED]
                                              │                                          ▲
                                              ├── Query Authoritative Power State ───────┘
                                              │   (Confirmed STOPPED)
                                              ▼
                                      Release Lease (#123)
                                      Return 8 Cores to Pool
                                      Log Compliance Audit
```

1. **In-Guest**: As Windows initiates shutdown, the agent sends `POST /api/v1/vms/stopping`. The controller marks the VM `STOPPING`, keeping the cores reserved.
2. **Hypervisor**: The hypervisor powers off the virtual machine.
3. **Reconciliation**: The Reconciliation Engine queries the hypervisor API. Once the hypervisor authoritatively confirms the power state is `STOPPED`, the controller **releases the lease**, returning 8 cores to the pool.
4. **KMS Safety**: Release **never** touches Windows activation (`slmgr /upk` is forbidden).

### 6. Dynamic License Handover (Auto-Allocation to Running Unlicensed VM)
If an 11th VM was powered on and waiting for a license:
1. As soon as VM 1 shuts down and its 8 cores are de-allocated, the pool has 8 cores free.
2. The agent running on the 11th VM (which retries every 30s) automatically claims the freed 8 cores on its next cycle.
3. Alternatively, the Reconciliation Engine detects the running unlicensed VM and **automatically auto-allocates** the freed cores to it (`RECONCILE_AUTO_ALLOCATE_RUNNING_VM`), logging the handover in the audit trail.

---

## Part 5: Verification & Day-2 Management

### Useful Verification Commands

#### 1. Check Controller Health
```powershell
Invoke-RestMethod -Uri "http://<MANAGER-VM-IP>:8000/health"
```

#### 2. Trigger On-Demand 3-Way Reconciliation
```powershell
Invoke-RestMethod -Uri "http://<MANAGER-VM-IP>:8000/api/v1/reconciliation/run" -Method Post
```

#### 3. View Recent Audit Logs
```powershell
(Invoke-RestMethod -Uri "http://<MANAGER-VM-IP>:8000/api/v1/audit?limit=10") | Format-Table timestamp, action, actor, notes
```

#### 4. Check Agent Status on Target VM
```powershell
Get-ScheduledTask -TaskName "WeAutomateVMAgent"
Get-Content "C:\ProgramData\WeAutomate\agent_cache.json"
```

#### 5. View Windows Activation Status on Target VM
```cmd
slmgr.vbs /dli
```
