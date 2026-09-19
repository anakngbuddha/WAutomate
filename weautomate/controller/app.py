"""Main FastAPI application for WeAutomate License Controller."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from weautomate.config import settings
from weautomate.database.session import init_db, seed_default_entitlements, SessionLocal
from weautomate.controller.routes import (
    vms_router,
    leases_router,
    enforcement_router,
    reconciliation_router,
    audit_router,
    dashboard_router,
)
from weautomate.controller.routes.agent_download import router as agent_download_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    init_db()
    # Seed default entitlement pool (e.g. 80 cores for 10 VMs)
    with SessionLocal() as session:
        seed_default_entitlements(session, core_quantity=80)
    yield


app = FastAPI(
    title="WeAutomate License Controller",
    description="Dynamic core licensing controller for Windows Server 2025 under Microsoft Flexible Virtualization Benefit (FVB)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers under /api/v1
api_v1_prefix = "/api/v1"
app.include_router(vms_router, prefix=api_v1_prefix)
app.include_router(leases_router, prefix=api_v1_prefix)
app.include_router(enforcement_router, prefix=api_v1_prefix)
app.include_router(reconciliation_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)
app.include_router(dashboard_router, prefix=api_v1_prefix)
app.include_router(agent_download_router, prefix=api_v1_prefix)
app.include_router(agent_download_router)  # Also mount root /install.ps1


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "WeAutomate License Controller",
        "version": "1.0.0",
    }


# Mount dashboard static assets if directory exists
static_dir = os.path.join(os.path.dirname(__file__), "..", "dashboard", "static")
if os.path.exists(static_dir):
    app.mount("/dashboard", StaticFiles(directory=static_dir, html=True), name="dashboard")

    @app.get("/")
    def root_redirect():
        return RedirectResponse(url="/dashboard/")
