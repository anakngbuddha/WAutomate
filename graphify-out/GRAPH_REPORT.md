# Graph Report - WeAutomate  (2026-09-19)

## Corpus Check
- 49 files · ~14,847 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 433 nodes · 907 edges · 15 communities (12 shown, 3 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 93 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- State Persistence & API Management
- License Controller & Admission Policy
- Hypervisor Reconciliation & VM State Engine
- VM Agent & KMS Activation Infrastructure
- Licensing Compliance & Legal Entitlement
- models.py
- app.js
- session.py
- rules/graphify.md
- workflows/graphify.md
- weautomate/__init__.py
- .get_entitlement_summary
- test_audit_logs_endpoint

## God Nodes (most connected - your core abstractions)
1. `LeaseManager` - 53 edges
2. `LeaseStatus` - 34 edges
3. `VMState` - 33 edges
4. `VirtualMachine` - 29 edges
5. `MockHypervisorAdapter` - 26 edges
6. `LicensingPolicyEngine` - 23 edges
7. `Lease` - 22 edges
8. `ReconciliationEngine` - 21 edges
9. `HypervisorAdapter` - 20 edges
10. `HypervisorPowerState` - 18 edges

## Surprising Connections (you probably didn't know these)
- `test_dashboard_metrics_endpoint()` --calls--> `VirtualMachine`  [EXTRACTED]
  tests/test_api_endpoints.py → weautomate/database/models.py
- `test_full_pool_lifecycle_10_vms()` --calls--> `MockHypervisorAdapter`  [EXTRACTED]
  tests/test_end_to_end.py → weautomate/hypervisor/mock.py
- `test_admission_control_denies_start_when_pool_exhausted()` --calls--> `Lease`  [EXTRACTED]
  tests/test_enforcement.py → weautomate/database/models.py
- `test_authoritative_release_releases_cores()` --calls--> `MockHypervisorAdapter`  [EXTRACTED]
  tests/test_leases.py → weautomate/hypervisor/mock.py
- `test_reconciliation_auto_releases_ghost_lease()` --calls--> `MockHypervisorAdapter`  [EXTRACTED]
  tests/test_reconciliation.py → weautomate/hypervisor/mock.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Tripartite Authority System** — project_plan_license_controller, project_plan_kms_host, project_plan_hypervisor_cloud_platform [EXTRACTED 1.00]
- **Dynamic License Core Architecture** — project_plan_license_controller, project_plan_vm_agent, project_plan_kms_host, project_plan_reconciliation_engine, project_plan_postgresql_state_store [EXTRACTED 1.00]
- **Enforcement Tiers Hierarchy** — project_plan_enforcement_tier_1, project_plan_enforcement_tier_2, project_plan_enforcement_tier_3 [EXTRACTED 1.00]

## Communities (15 total, 3 thin omitted)

### Community 0 - "State Persistence & API Management"
Cohesion: 0.09
Nodes (24): Append-Only Audit Log, Controller API (FastAPI), Tier 1: Pre-Boot Admission Control, Tier 2: Platform RBAC Gating, Tier 3: Detection & Alerting, Explicit Scope Boundaries, Flexible Virtualization Benefit (FVB), FVB Legal Eligibility Conditions (+16 more)

### Community 1 - "License Controller & Admission Policy"
Cohesion: 0.08
Nodes (22): ABC, mock_hypervisor(), Provides a fresh mock hypervisor adapter., Session, HypervisorAdapter, HypervisorPowerState, HypervisorVMInfo, str (+14 more)

### Community 2 - "Hypervisor Reconciliation & VM State Engine"
Cohesion: 0.10
Nodes (46): get_dashboard_metrics(), list_entitlements(), Session, Dashboard telemetry and aggregated metrics endpoints., Lists registered core licensing entitlements., Aggregated core capacity, VM state breakdown, and lease telemetry for the web da, Controller routes package., allocate_lease() (+38 more)

### Community 3 - "VM Agent & KMS Activation Infrastructure"
Cohesion: 0.08
Nodes (34): Tests for Tier 1 & Tier 2 admission control and enforcement API., Tier 1/2 start gate permits boot when cores are available., Tier 1/2 start gate denies boot when core pool is exhausted., test_admission_control_denies_start_when_pool_exhausted(), test_admission_control_permits_start_when_capacity_available(), Tests for Microsoft Flexible Virtualization Benefit (FVB) licensing policy compl, Test that requesting fewer than 8 cores per VM is rejected under FVB., Test that an organization entitlement pool under 16 cores is rejected. (+26 more)

### Community 4 - "Licensing Compliance & Legal Entitlement"
Cohesion: 0.06
Nodes (38): Client, Tests for the outbound-only VM Agent., Test VM agent registering and acquiring lease via outbound HTTP., Verify that the official Windows Server 2025 Standard GVLK key matches Microsoft, test_agent_outbound_registration_and_lease(), test_windows_2025_standard_gvlk_format(), get_windows_activation_status(), Any (+30 more)

### Community 5 - "models.py"
Cohesion: 0.06
Nodes (53): datetime, Test GET /api/v1/dashboard/metrics aggregates core and VM counts accurately., test_dashboard_metrics_endpoint(), End-to-end integration test simulating the entire 10-VM pool lifecycle.  Covers:, test_full_pool_lifecycle_10_vms(), Tests for idempotent core lease allocation via request_id., Verifies that calling allocate_lease multiple times with the same request_id doe, test_idempotent_allocation_same_request_id() (+45 more)

### Community 6 - "app.js"
Cohesion: 0.07
Nodes (42): currentVms, elActiveVmsCount, elAllocatedCores, elAuditTimeline, elAuditTotalCount, elAvailableCores, elBtnConfirmStart, elBtnReconcileNow (+34 more)

### Community 7 - "session.py"
Cohesion: 0.06
Nodes (37): DeclarativeBase, FastAPI, Request, client(), db_engine(), db_session(), Pytest configuration and shared fixtures for WeAutomate., In-memory SQLite engine with StaticPool for cross-thread consistency. (+29 more)

### Community 13 - ".get_entitlement_summary"
Cohesion: 0.06
Nodes (31): 1. Boot & Admission Control (Gating Starts), 1. Check Controller Health, 2. In-Guest Registration & Idempotent Lease Acquisition, 2. Trigger On-Demand 3-Way Reconciliation, 3. Continuous Heartbeat Renewal, 3. View Recent Audit Logs, 4. Check Agent Status on Target VM, 4. Network Partition / Unreachable Safety (Strict Rule) (+23 more)

### Community 18 - "test_audit_logs_endpoint"
Cohesion: 0.17
Nodes (11): Tests for Controller API routes: dashboard metrics, audit logs, VM listing, and, Test GET /api/v1/audit returns ordered append-only records., Test POST /api/v1/reconciliation/run executes 3-way check., Test GET /health returns 200 OK., Test GET /api/v1/agent/bundle.zip returns a valid zip file containing the agent, Test GET /install.ps1 serves the PowerShell installation script., test_agent_bundle_download(), test_audit_logs_endpoint() (+3 more)

## Knowledge Gaps
- **64 isolated node(s):** `currentVms`, `elAllocatedCores`, `elTotalCores`, `elAvailableCores`, `elGaugeFill` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LeaseManager` connect `models.py` to `License Controller & Admission Policy`, `Hypervisor Reconciliation & VM State Engine`, `VM Agent & KMS Activation Infrastructure`, `session.py`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Why does `HypervisorAdapter` connect `License Controller & Admission Policy` to `VM Agent & KMS Activation Infrastructure`, `models.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `LeaseManager` (e.g. with `LicensingPolicyEngine` and `PolicyEvaluationResult`) actually correct?**
  _`LeaseManager` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `LeaseStatus` (e.g. with `LeaseManager` and `LicensingPolicyEngine`) actually correct?**
  _`LeaseStatus` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `VMState` (e.g. with `LeaseManager` and `LicensingPolicyEngine`) actually correct?**
  _`VMState` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `VirtualMachine` (e.g. with `LeaseManager` and `LicensingPolicyEngine`) actually correct?**
  _`VirtualMachine` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `MockHypervisorAdapter` (e.g. with `HypervisorAdapter` and `HypervisorPowerState`) actually correct?**
  _`MockHypervisorAdapter` has 3 INFERRED edges - model-reasoned connections that need verification._