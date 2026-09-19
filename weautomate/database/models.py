"""SQLAlchemy models for WeAutomate license controller."""

import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class LicenseType(str, enum.Enum):
    SUBSCRIPTION = "subscription"
    SA_PERPETUAL = "SA-perpetual"


class VMState(str, enum.Enum):
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    TERMINATED = "TERMINATED"
    UNREACHABLE = "UNREACHABLE"
    UNKNOWN = "UNKNOWN"


class LeaseStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"


class Entitlement(Base):
    __tablename__ = "entitlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product: Mapped[str] = mapped_column(String(100), default="Windows Server", nullable=False)
    edition: Mapped[str] = mapped_column(String(50), default="Standard", nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="2025", nullable=False)
    license_type: Mapped[LicenseType] = mapped_column(
        Enum(LicenseType, native_enum=False), default=LicenseType.SUBSCRIPTION, nullable=False
    )
    core_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    agreement_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    leases: Mapped[List["Lease"]] = relationship("Lease", back_populates="entitlement")


class VirtualMachine(Base):
    __tablename__ = "vms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hypervisor_uuid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    core_count: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    server_farm: Mapped[str] = mapped_column(String(100), nullable=False)
    current_state: Mapped[VMState] = mapped_column(
        Enum(VMState, native_enum=False), default=VMState.STOPPED, nullable=False
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(100), default="Windows Server 2025 Standard")
    activation_status: Mapped[Optional[str]] = mapped_column(String(100), default="Licensed")
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reconciled: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    leases: Mapped[List["Lease"]] = relationship("Lease", back_populates="vm")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="vm")


class Lease(Base):
    __tablename__ = "leases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entitlement_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entitlements.id", ondelete="CASCADE"), nullable=False
    )
    vm_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vms.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )  # Idempotency key
    cores_allocated: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[LeaseStatus] = mapped_column(
        Enum(LeaseStatus, native_enum=False), default=LeaseStatus.ACTIVE, nullable=False
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    entitlement: Mapped["Entitlement"] = relationship("Entitlement", back_populates="leases")
    vm: Mapped["VirtualMachine"] = relationship("VirtualMachine", back_populates="leases")

    __table_args__ = (
        Index("ix_leases_vm_status", "vm_id", "status"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    vm_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("vms.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    vm: Mapped[Optional["VirtualMachine"]] = relationship("VirtualMachine", back_populates="audit_logs")
