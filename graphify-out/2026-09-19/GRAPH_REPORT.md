# Graph Report - WeAutomate  (2026-09-19)

## Corpus Check
- 48 files · ~14,534 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 422 nodes · 895 edges · 25 communities (15 shown, 10 thin omitted)
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
- get_audit_logs
- rules/graphify.md
- workflows/graphify.md
- weautomate/__init__.py
- .get_entitlement_summary
- test_agent.py
- notify_stopping
- .get_entitlement_summary
- get_audit_logs
- test_audit_logs_endpoint
- test_reconciliation_api_endpoint
- test_health_check_endpoint
- Settings
- .__init__
- get_enforcement_status

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
- `mock_hypervisor()` --calls--> `MockHypervisorAdapter`  [EXTRACTED]
  tests/conftest.py → weautomate/hypervisor/mock.py
- `test_agent_outbound_registration_and_lease()` --calls--> `VMAgent`  [EXTRACTED]
  tests/test_agent.py → weautomate/agent/agent.py
- `test_dashboard_metrics_endpoint()` --calls--> `utc_now()`  [EXTRACTED]
  tests/test_api_endpoints.py → weautomate/database/models.py
- `test_full_pool_lifecycle_10_vms()` --calls--> `MockHypervisorAdapter`  [EXTRACTED]
  tests/test_end_to_end.py → weautomate/hypervisor/mock.py
- `test_authoritative_release_releases_cores()` --calls--> `LeaseManager`  [EXTRACTED]
  tests/test_leases.py → weautomate/controller/lease_manager.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Tripartite Authority System** — project_plan_license_controller, project_plan_kms_host, project_plan_hypervisor_cloud_platform [EXTRACTED 1.00]
- **Dynamic License Core Architecture** — project_plan_license_controller, project_plan_vm_agent, project_plan_kms_host, project_plan_reconciliation_engine, project_plan_postgresql_state_store [EXTRACTED 1.00]
- **Enforcement Tiers Hierarchy** — project_plan_enforcement_tier_1, project_plan_enforcement_tier_2, project_plan_enforcement_tier_3 [EXTRACTED 1.00]

## Communities (25 total, 10 thin omitted)

### Community 0 - "State Persistence & API Management"
Cohesion: 0.09
Nodes (24): Append-Only Audit Log, Controller API (FastAPI), Tier 1: Pre-Boot Admission Control, Tier 2: Platform RBAC Gating, Tier 3: Detection & Alerting, Explicit Scope Boundaries, Flexible Virtualization Benefit (FVB), FVB Legal Eligibility Conditions (+16 more)

### Community 1 - "License Controller & Admission Policy"
Cohesion: 0.08
Nodes (22): ABC, Test that authoritative release cleanly releases cores and updates lease status., test_authoritative_release_releases_cores(), Session, HypervisorAdapter, HypervisorPowerState, HypervisorVMInfo, str (+14 more)

### Community 2 - "Hypervisor Reconciliation & VM State Engine"
Cohesion: 0.18
Nodes (11): allocate_lease(), heartbeat(), list_active_leases(), list_all_leases(), Session, Allocates a dynamic core lease. Guaranteed idempotent via request_id., Agent heartbeat renewal. Extends lease duration., Authoritative release. Released only if hypervisor confirms STOPPED or explicitl (+3 more)

### Community 3 - "VM Agent & KMS Activation Infrastructure"
Cohesion: 0.08
Nodes (61): datetime, FastAPI, Tests for Controller API routes: dashboard metrics, audit logs, VM listing, and, Test GET /api/v1/dashboard/metrics aggregates core and VM counts accurately., test_dashboard_metrics_endpoint(), End-to-end integration test simulating the entire 10-VM pool lifecycle.  Covers:, Tests for Tier 1 & Tier 2 admission control and enforcement API., Tier 1/2 start gate permits boot when cores are available. (+53 more)

### Community 4 - "Licensing Compliance & Legal Entitlement"
Cohesion: 0.08
Nodes (25): Client, get_windows_activation_status(), Any, Windows activation telemetry and KMS status queries.  CRITICAL ARCHITECTURAL POL, Queries Windows licensing status via CIM/WMI without modifying activation state., Any, Outbound-only VM Agent service for Windows Server 2025., Requests dynamic core lease from controller using idempotent request_id. (+17 more)

### Community 5 - "models.py"
Cohesion: 0.06
Nodes (43): test_full_pool_lifecycle_10_vms(), Verifies that calling allocate_lease multiple times with the same request_id doe, test_idempotent_allocation_same_request_id(), Test full cycle of allocation and heartbeat extension., Test that graceful stopping signal marks VM STOPPING but keeps core lease reserv, test_graceful_stopping_reserves_lease(), test_lease_allocation_and_heartbeat(), Tests for the 3-way Reconciliation Engine. (+35 more)

### Community 6 - "app.js"
Cohesion: 0.07
Nodes (42): currentVms, elActiveVmsCount, elAllocatedCores, elAuditTimeline, elAuditTotalCount, elAvailableCores, elBtnConfirmStart, elBtnReconcileNow (+34 more)

### Community 7 - "session.py"
Cohesion: 0.09
Nodes (28): DeclarativeBase, client(), db_engine(), db_session(), mock_hypervisor(), Pytest configuration and shared fixtures for WeAutomate., In-memory SQLite engine with StaticPool for cross-thread consistency., Provides an isolated database session with default 80-core entitlement. (+20 more)

### Community 9 - "get_audit_logs"
Cohesion: 0.67
Nodes (3): list_entitlements(), Session, Lists registered core licensing entitlements.

### Community 13 - ".get_entitlement_summary"
Cohesion: 0.06
Nodes (31): 1. Boot & Admission Control (Gating Starts), 1. Check Controller Health, 2. In-Guest Registration & Idempotent Lease Acquisition, 2. Trigger On-Demand 3-Way Reconciliation, 3. Continuous Heartbeat Renewal, 3. View Recent Audit Logs, 4. Check Agent Status on Target VM, 4. Network Partition / Unreachable Safety (Strict Rule) (+23 more)

### Community 14 - "test_agent.py"
Cohesion: 0.17
Nodes (13): Tests for the outbound-only VM Agent., Test VM agent registering and acquiring lease via outbound HTTP., Verify that the official Windows Server 2025 Standard GVLK key matches Microsoft, test_agent_outbound_registration_and_lease(), test_windows_2025_standard_gvlk_format(), check_kms_host_connectivity(), get_kms_configuration_summary(), Any (+5 more)

### Community 15 - "notify_stopping"
Cohesion: 0.22
Nodes (9): get_vm(), list_vms(), notify_stopping(), Session, Registers a VM identity. Outbound only; idempotent., Lists all registered virtual machines., Fetches details for a specific VM., Graceful shutdown notification from VM agent. (+1 more)

### Community 17 - "get_audit_logs"
Cohesion: 0.67
Nodes (3): get_audit_logs(), Session, Retrieves immutable append-only audit log records.

## Knowledge Gaps
- **64 isolated node(s):** `currentVms`, `elAllocatedCores`, `elTotalCores`, `elAvailableCores`, `elGaugeFill` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LeaseManager` connect `models.py` to `License Controller & Admission Policy`, `Hypervisor Reconciliation & VM State Engine`, `VM Agent & KMS Activation Infrastructure`, `session.py`, `notify_stopping`?**
  _High betweenness centrality (0.128) - this node is a cross-community bridge._
- **Why does `VMAgent` connect `Licensing Compliance & Legal Entitlement` to `test_agent.py`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `HypervisorAdapter` connect `License Controller & Admission Policy` to `VM Agent & KMS Activation Infrastructure`, `models.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `LeaseManager` (e.g. with `LicensingPolicyEngine` and `PolicyEvaluationResult`) actually correct?**
  _`LeaseManager` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `LeaseStatus` (e.g. with `LeaseManager` and `LicensingPolicyEngine`) actually correct?**
  _`LeaseStatus` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `VMState` (e.g. with `LeaseManager` and `LicensingPolicyEngine`) actually correct?**
  _`VMState` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `VirtualMachine` (e.g. with `LeaseManager` and `LicensingPolicyEngine`) actually correct?**
  _`VirtualMachine` has 6 INFERRED edges - model-reasoned connections that need verification._