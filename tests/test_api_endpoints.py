"""Tests for Controller API routes: dashboard metrics, audit logs, VM listing, and reconciliation."""

import pytest
from fastapi import status
from weautomate.database.models import VirtualMachine, VMState, Lease, LeaseStatus, utc_now
from weautomate.config import settings


def test_dashboard_metrics_endpoint(client, db_session):
    """Test GET /api/v1/dashboard/metrics aggregates core and VM counts accurately."""
    # Register and allocate 1 VM with 8 cores
    vm = VirtualMachine(
        hostname="metrics-node-01",
        hypervisor_uuid="uuid-metrics-01",
        core_count=8,
        server_farm=settings.server_farm_name,
        current_state=VMState.RUNNING,
    )
    db_session.add(vm)
    db_session.flush()

    lease = Lease(
        entitlement_id=1,
        vm_id=vm.id,
        request_id="req-metrics-01",
        cores_allocated=8,
        status=LeaseStatus.ACTIVE,
        granted_at=utc_now(),
        expires_at=utc_now(),
    )
    db_session.add(lease)
    db_session.commit()

    resp = client.get("/api/v1/dashboard/metrics")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total_cores"] == 80
    assert data["allocated_cores"] == 8
    assert data["available_cores"] == 72
    assert data["utilization_percentage"] == 10.0
    assert data["active_leases_count"] == 1
    assert data["vms_by_state"]["RUNNING"] == 1


def test_audit_logs_endpoint(client, db_session):
    """Test GET /api/v1/audit returns ordered append-only records."""
    # Allocate via API to produce an audit log
    client.post(
        "/api/v1/vms/register",
        json={"hostname": "audit-node-01", "hypervisor_uuid": "uuid-audit-01", "core_count": 8},
    )
    client.post(
        "/api/v1/leases/allocate",
        json={"hypervisor_uuid": "uuid-audit-01", "request_id": "req-audit-test", "requested_cores": 8},
    )

    resp = client.get("/api/v1/audit?limit=10")
    assert resp.status_code == status.HTTP_200_OK
    logs = resp.json()
    assert len(logs) >= 2
    actions = [log["action"] for log in logs]
    assert "ALLOCATE_SUCCESS" in actions
    assert "VM_REGISTERED" in actions


def test_reconciliation_api_endpoint(client, db_session):
    """Test POST /api/v1/reconciliation/run executes 3-way check."""
    resp = client.post("/api/v1/reconciliation/run?auto_release_ghost=true")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "matched_count" in data
    assert "discrepancies" in data
    assert "summary" in data


def test_health_check_endpoint(client):
    """Test GET /health returns 200 OK."""
    resp = client.get("/health")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "healthy"


def test_agent_bundle_download(client):
    """Test GET /api/v1/agent/bundle.zip returns a valid zip file containing the agent code."""
    import zipfile
    import io
    resp = client.get("/api/v1/agent/bundle.zip")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert "weautomate/agent/agent.py" in names
    assert "weautomate/agent/cli.py" in names


def test_installer_script_endpoint(client):
    """Test GET /install.ps1 serves the PowerShell installation script."""
    resp = client.get("/install.ps1")
    assert resp.status_code == status.HTTP_200_OK
    assert "WeAutomate" in resp.text
    assert "WeAutomateVMAgent" in resp.text

