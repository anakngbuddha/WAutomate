"""Pydantic schemas for the WeAutomate Controller API."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from weautomate.database.models import VMState, LeaseStatus, LicenseType


class VMRegisterRequest(BaseModel):
    hostname: str
    hypervisor_uuid: str
    core_count: int = Field(default=8, ge=8)
    server_farm: Optional[str] = None
    ip_address: Optional[str] = None
    os_version: Optional[str] = "Windows Server 2025 Standard"
    activation_status: Optional[str] = "Licensed"


class VMResponse(BaseModel):
    id: int
    hostname: str
    hypervisor_uuid: str
    core_count: int
    server_farm: str
    current_state: VMState
    ip_address: Optional[str] = None
    os_version: Optional[str] = None
    activation_status: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    last_reconciled: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LeaseAllocateRequest(BaseModel):
    hypervisor_uuid: str
    request_id: str = Field(..., description="Idempotency key")
    requested_cores: Optional[int] = Field(default=None, ge=8)


class LeaseResponse(BaseModel):
    id: int
    entitlement_id: int
    vm_id: int
    request_id: str
    cores_allocated: int
    status: LeaseStatus
    granted_at: datetime
    expires_at: datetime
    released_at: Optional[datetime] = None
    release_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HeartbeatRequest(BaseModel):
    hypervisor_uuid: str


class StoppingRequest(BaseModel):
    hypervisor_uuid: str


class ReleaseRequest(BaseModel):
    hypervisor_uuid: str
    reason: str
    force: bool = False


class RequestStartVM(BaseModel):
    hypervisor_uuid: str
    requested_cores: Optional[int] = Field(default=None, ge=8)
    actor: str = "operator"


class EntitlementResponse(BaseModel):
    id: int
    product: str
    edition: str
    version: str
    license_type: LicenseType
    core_quantity: int
    agreement_ref: str

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    vm_id: Optional[int]
    action: str
    actor: str
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class DashboardMetrics(BaseModel):
    total_cores: int
    allocated_cores: int
    available_cores: int
    utilization_percentage: float
    total_vms: int
    vms_by_state: Dict[str, int]
    active_leases_count: int
    latest_reconciliation: Optional[Dict[str, Any]]
