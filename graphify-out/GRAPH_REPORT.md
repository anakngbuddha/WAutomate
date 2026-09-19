# Graph Report - C:\Users\markv\Desktop\WeAutomate  (2026-09-13)

## Corpus Check
- Corpus is ~1,632 words - fits in a single context window. You may not need a graph.

## Summary
- 24 nodes · 25 edges · 5 communities
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 3 edges (avg confidence: 0.88)
- Token cost: 1,632 input · 850 output

## Community Hubs (Navigation)
- State Persistence & API Management
- License Controller & Admission Policy
- Hypervisor Reconciliation & VM State Engine
- VM Agent & KMS Activation Infrastructure
- Licensing Compliance & Legal Entitlement

## God Nodes (most connected - your core abstractions)
1. `License Controller` - 8 edges
2. `Controller API (FastAPI)` - 5 edges
3. `Reconciliation Engine` - 4 edges
4. `Flexible Virtualization Benefit (FVB)` - 3 edges
5. `VM Agent` - 3 edges
6. `Windows Server 2025 Standard VM` - 3 edges
7. `PostgreSQL State Store` - 3 edges
8. `KMS Host (Activation Authority)` - 2 edges
9. `Hypervisor / Cloud Platform` - 2 edges
10. `FVB Legal Eligibility Conditions` - 2 edges

## Surprising Connections (you probably didn't know these)
- `License Controller` --implements--> `Controller API (FastAPI)`  [EXTRACTED]
  Project_Plan.md → Project_Plan.md  _Bridges community 1 → community 0_
- `License Controller` --references--> `Flexible Virtualization Benefit (FVB)`  [EXTRACTED]
  Project_Plan.md → Project_Plan.md  _Bridges community 1 → community 4_
- `License Controller` --conceptually_related_to--> `Hypervisor / Cloud Platform`  [EXTRACTED]
  Project_Plan.md → Project_Plan.md  _Bridges community 1 → community 2_
- `License Controller` --conceptually_related_to--> `KMS Host (Activation Authority)`  [EXTRACTED]
  Project_Plan.md → Project_Plan.md  _Bridges community 1 → community 3_
- `VM Agent` --calls--> `Controller API (FastAPI)`  [EXTRACTED]
  Project_Plan.md → Project_Plan.md  _Bridges community 3 → community 0_

## Hyperedges (group relationships)
- **Tripartite Authority System** — project_plan_license_controller, project_plan_kms_host, project_plan_hypervisor_cloud_platform [EXTRACTED 1.00]
- **Dynamic License Core Architecture** — project_plan_license_controller, project_plan_vm_agent, project_plan_kms_host, project_plan_reconciliation_engine, project_plan_postgresql_state_store [EXTRACTED 1.00]
- **Enforcement Tiers Hierarchy** — project_plan_enforcement_tier_1, project_plan_enforcement_tier_2, project_plan_enforcement_tier_3 [EXTRACTED 1.00]

## Communities (5 total, 0 thin omitted)

### Community 0 - "State Persistence & API Management"
Cohesion: 0.40
Nodes (5): Append-Only Audit Log, Controller API (FastAPI), Idempotent Request Key (request_id), Management Dashboard (React), PostgreSQL State Store

### Community 1 - "License Controller & Admission Policy"
Cohesion: 0.40
Nodes (5): Tier 1: Pre-Boot Admission Control, Tier 2: Platform RBAC Gating, License Controller, Scale-Appropriate Descoping, Tripartite Authority Principle

### Community 2 - "Hypervisor Reconciliation & VM State Engine"
Cohesion: 0.40
Nodes (5): Tier 3: Detection & Alerting, Hypervisor / Cloud Platform, Reconciliation Engine, Unreachable State Policy, VM State Detection Model

### Community 3 - "VM Agent & KMS Activation Infrastructure"
Cohesion: 0.40
Nodes (5): Hypervisor UUID (Immutable Identity), KMS Host (Activation Authority), Outbound HTTPS / mTLS Transport, VM Agent, Windows Server 2025 Standard VM

### Community 4 - "Licensing Compliance & Legal Entitlement"
Cohesion: 0.50
Nodes (4): Explicit Scope Boundaries, Flexible Virtualization Benefit (FVB), FVB Legal Eligibility Conditions, Written Microsoft / Reseller Confirmation

## Knowledge Gaps
- **10 isolated node(s):** `Written Microsoft / Reseller Confirmation`, `Outbound HTTPS / mTLS Transport`, `Tier 1: Pre-Boot Admission Control`, `Tier 2: Platform RBAC Gating`, `Tier 3: Detection & Alerting` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `License Controller` connect `License Controller & Admission Policy` to `State Persistence & API Management`, `Hypervisor Reconciliation & VM State Engine`, `VM Agent & KMS Activation Infrastructure`, `Licensing Compliance & Legal Entitlement`?**
  _High betweenness centrality (0.644) - this node is a cross-community bridge._
- **Why does `Controller API (FastAPI)` connect `State Persistence & API Management` to `License Controller & Admission Policy`, `VM Agent & KMS Activation Infrastructure`?**
  _High betweenness centrality (0.407) - this node is a cross-community bridge._
- **Why does `Reconciliation Engine` connect `Hypervisor Reconciliation & VM State Engine` to `State Persistence & API Management`?**
  _High betweenness centrality (0.253) - this node is a cross-community bridge._
- **What connects `Written Microsoft / Reseller Confirmation`, `Outbound HTTPS / mTLS Transport`, `Tier 1: Pre-Boot Admission Control` to the rest of the system?**
  _10 weakly-connected nodes found - possible documentation gaps or missing edges._