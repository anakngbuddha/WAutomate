"""Controller routes package."""

from weautomate.controller.routes.vms import router as vms_router
from weautomate.controller.routes.leases import router as leases_router
from weautomate.controller.routes.enforcement import router as enforcement_router
from weautomate.controller.routes.reconciliation import router as reconciliation_router
from weautomate.controller.routes.audit import router as audit_router
from weautomate.controller.routes.dashboard import router as dashboard_router

__all__ = [
    "vms_router",
    "leases_router",
    "enforcement_router",
    "reconciliation_router",
    "audit_router",
    "dashboard_router",
]
