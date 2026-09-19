"""Database package for WeAutomate."""

from weautomate.database.models import (
    Base,
    Entitlement,
    VirtualMachine,
    Lease,
    AuditLog,
    LicenseType,
    VMState,
    LeaseStatus,
)
from weautomate.database.session import (
    get_engine,
    init_db,
    seed_default_entitlements,
    get_db,
    get_db_context,
    SessionLocal,
)

__all__ = [
    "Base",
    "Entitlement",
    "VirtualMachine",
    "Lease",
    "AuditLog",
    "LicenseType",
    "VMState",
    "LeaseStatus",
    "get_engine",
    "init_db",
    "seed_default_entitlements",
    "get_db",
    "get_db_context",
    "SessionLocal",
]
