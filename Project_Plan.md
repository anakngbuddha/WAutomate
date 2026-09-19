# Windows Server 2025 Dynamic License Automation — Final Plan

**Scope:** Allocate licensed core capacity to an eligible Windows Server 2025 Standard VM while it is running, and release that allocation when the VM stops — across a pool of VMs sharing a fixed set of core-licensed capacity, on independent (non-Azure, non-Listed-Provider) private cloud infrastructure.

**Core principle, unchanged from start to finish of this design:** the License Controller decides what is *allowed*. KMS decides what is *activated*. The hypervisor/cloud platform decides what is *actually running*. These are three different authorities and the system must never let one stand in for another.

---

## 1. Licensing Compliance Foundation — do this first

### Legal eligibility conditions (Flexible Virtualization Benefit)

| Condition | Status |
|---|---|
| Subscription licenses OR perpetual licenses with active Software Assurance | Confirmed |
| Infrastructure independent of a Microsoft Listed Provider (AWS, Azure, GCP, Alibaba) | Confirmed |
| All target VMs within the same server farm | Confirmed |
| Sufficient core entitlement per VM (8-core minimum per VM) | Confirmed |
| **16-core minimum per customer, org-wide, under the by-VM licensing model** | Confirmed satisfied — 10 VMs at an 8-core minimum each is already far above this floor. Documented here for completeness; not a practical constraint at your scale. |

### Engineering standardization choices (good practice, not legal requirements)

- Same OS edition, version, and core size across VMs
- Standardized images

**Outstanding action — still the most important item on this entire plan:** get the legal eligibility conditions above confirmed **in writing** by your Microsoft licensing rep or reseller before relying on this in production. Everything below assumes that confirmation lands the way the self-reported facts suggest it will.

---

## 2. Architecture

```
Microsoft Licensing Entitlement / FVB
                │
                ▼
        LICENSE CONTROLLER   ← "Are we allowed to allocate this entitlement?"
   (allocation, leases, policy, reconciliation, audit)
                │
       HTTPS / mTLS — agent-initiated, outbound only
                │
        VM Agent (per VM) — registers, heartbeats, reports status
                │
                ▼
              KMS          ← "Can this Windows installation activate?"
                │
                ▼
        Windows Server VM (activated)
```

The agent connects **outbound to the controller**, never the reverse — no inbound ports need to be opened on any VM, which matters given the private cloud's network posture is not fully known.

---

## 3. Enforcement Model

Everything above answers *"does our record match reality"* — heartbeats, leases, reconciliation. None of it, by itself, stops someone from starting an 11th VM when 10 are already running. That gap matters: a system that only notices over-allocation after the fact isn't preventing it. Which tier below is achievable depends entirely on what your private cloud platform supports — confirm this before committing to one.

| Tier | Mechanism | Guarantee |
|---|---|---|
| **1 — Preferred** | If the platform supports pre-boot hooks/admission control, the controller gates the actual start call: VM start requests go through the controller first, which only permits the boot if capacity is available. | True prevention |
| **2 — Practical fallback** | Restrict "start VM" capability on the platform to only the controller's own service account (via platform RBAC). Humans request starts through the controller's own interface, which then starts the VM on their behalf, gated by availability. | Prevention, enforced by access control rather than a technical hook |
| **3 — Minimum viable** | Neither of the above is available: reconciliation detects an unauthorized running VM within minutes and fires an alert immediately. | Detection only, not prevention — treat this as a stopgap, not an end state |

**Open item:** confirm which tier your infrastructure actually supports before finalizing this part of the build.

---

## 4. VM State Detection

| State | Meaning | Action |
|---|---|---|
| RUNNING | Heartbeats current | Reserve |
| STOPPING | Shutdown in progress | Reserve |
| STOPPED (confirmed by cloud/hypervisor API) | Authoritative power-off signal | Release |
| TERMINATED | VM deleted/deprovisioned | Release |
| UNREACHABLE | Heartbeat lost, no authoritative confirmation | **Do not auto-release** — flag "at risk," grace period, then manual reconciliation if still unresolved |
| UNKNOWN | Ambiguous/conflicting signals | Escalate, keep reserved |

**Why this is strict:** a VM that's actually running with a broken network connection looks identical to one that's off. Auto-releasing on heartbeat loss alone risks the exact over-allocation this project exists to prevent.

**Open item, same as above:** whether your private cloud exposes any VM power-state API (VMware, Proxmox, OpenStack, oVirt typically do) determines whether STOPPED can ever be automatically confirmed, or whether it always requires manual reconciliation.

---

## 5. Components to Build

| # | Component | Notes |
|---|---|---|
| 1 | VM Agent | Windows Service (Python or .NET), PowerShell invoked only for Windows-specific calls (`Get-CimInstance`, activation status queries). Registration, heartbeat, local cache, retry logic. No routine activation changes — release never depends on touching Windows' activation state. |
| 2 | License Controller / API | FastAPI. Allocation engine, lease manager, policy engine, **idempotent** endpoints. |
| 3 | State store | PostgreSQL + SQLAlchemy/Alembic. |
| 4 | Reconciliation engine | First-class subsystem: compares expected vs. actual state on a schedule, emits match → continue or mismatch → alert. Independent of the dashboard. |
| 5 | KMS host | **Configure, not build** — Volume Activation Services role. |
| 6 | Dashboard | React + REST for MVP. The controller must keep working if the dashboard is down — never put it on the licensing-critical path. |
| 7 | Audit log | Append-only: every allocate/release/reconciliation/enforcement event, timestamp, actor, reason. |

---

## 6. Data Model

```
entitlements: id, product, edition, version, license_type (subscription | SA-perpetual),
              core_quantity, agreement_ref

vms:          id, hostname, hypervisor_uuid (immutable identity — not just hostname/IP,
              to avoid a clone or rebuild being mistaken for the same machine),
              core_count, server_farm, current_state, last_heartbeat, last_reconciled

leases:       id, entitlement_id, vm_id, request_id (idempotency key),
              granted_at, expires_at, released_at, release_reason

audit_log:    timestamp, vm_id, action, actor, notes
```

`request_id` must make every allocation call idempotent — a retried request from a flaky connection should never be able to allocate a second seat for the same intent. `hypervisor_uuid` (or equivalent platform-issued identifier) gives each VM an identity that survives a rename and isn't trivially duplicated by a clone — cheap to include now, more expensive to retrofit later.

---

## 7. Tech Stack

| Layer | Choice |
|---|---|
| Agent | Python or .NET Windows Service; PowerShell for Windows-specific calls only |
| Transport | Outbound HTTPS, mTLS or device-cert auth |
| Controller API | Python (FastAPI), idempotent endpoints |
| Database | PostgreSQL + SQLAlchemy + Alembic |
| KMS client | Windows Server 2025 Standard GVLK: `TVRH6-WHNXV-R9WG3-9XRFY-MY832` (public, goes on each VM — verify against current Microsoft docs before use) |
| KMS host | Microsoft-issued CSVLK (customer-specific — obtained from your licensing portal, never the client GVLK) |
| KMS host role | Volume Activation Services |
| Dashboard | React + REST |
| Reconciliation | Standalone subsystem; hypervisor API where available |

---

## 8. Deliberately Descoped — and why

Scale-appropriate engineering cuts both ways: these are real patterns, correctly identified in review, and deliberately left out of this version because building them now would cost more than the risk they address at your actual scale (10 VMs, single operator).

| Pattern | Why it's out, for now |
|---|---|
| Multiple controller instances / split-brain handling | Nothing in this design calls for more than one controller. Revisit only if that changes. |
| Formal lease-generation/fencing tokens for snapshot rollback | A correct distributed-systems pattern, proportionate to environments where snapshotting *these specific licensed VMs* is routine. Revisit if that becomes a regular operational practice. |
| Exhaustive 30-50 scenario failure-mode matrix | Good due diligence in principle; disproportionate effort for a project this size before anything has shipped. Test the failure modes you're actually likely to hit — agent crash, network blip, controller restart, manual VM start — before inventing more. |

VM cloning defense (the `hypervisor_uuid` field above) is the one exception kept in scope — it's cheap enough to include from day one that there's no reason not to.

---

## 9. Rollout Phases

- **Phase 0 — Legal:** get FVB eligibility confirmed in writing from Microsoft/reseller. Confirm which enforcement tier (Section 3) your platform supports.
- **Phase 1 — MVP:** Controller (with idempotency) + agent + heartbeat + lease + KMS, piloted on 2-3 VMs. No auto-release without an authoritative signal. Enforcement Tier 3 (detection/alerting) at minimum.
- **Phase 2 — Harden:** Reconciliation engine, dashboard, audit log, mTLS, whichever enforcement tier is achievable.
- **Phase 3 — Full rollout:** All 10 VMs, alerting on any mismatch or capacity approaching the limit.

---

## 10. Open Items, Ranked

1. **Written Microsoft/reseller confirmation of FVB eligibility** — not yet obtained. Blocks production reliance, not the build itself.
2. **Does the private cloud expose a VM power-state/control-plane API?** — determines whether STOPPED can be automatic (Section 4) and which enforcement tier is reachable (Section 3). The single fact that shapes the most downstream design decisions.
3. **Enforcement tier decision** (Section 3) — depends directly on #2.

---

## 11. Explicitly Out of Scope for This Pattern

- **RDS CALs** — per-seat, perpetual by design. Do not build automated float/reclaim for these.
- **VDA E3 / Windows 11-style per-user licensing** — a structurally different model (per-user concurrent-instance cap, not an org-wide core pool). If that project resumes, it needs its own design, not a copy of this one.
- **Any routine in-guest activation command (`slmgr /upk` or similar) as part of the release path** — it doesn't return anything to your entitlement pool. Release is driven entirely by confirmed VM state, never by touching Windows activation.