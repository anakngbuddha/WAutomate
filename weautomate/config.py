"""Configuration module for WeAutomate."""

import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///weautomate.db")
    )
    server_farm_name: str = Field(
        default_factory=lambda: os.getenv("SERVER_FARM_NAME", "primary-server-farm")
    )
    
    # Timing & Lease parameters
    heartbeat_interval_seconds: int = Field(default=30)
    lease_duration_seconds: int = Field(default=90)
    unreachable_grace_period_seconds: int = Field(default=60)
    reconciliation_interval_seconds: int = Field(default=60)
    
    # Licensing compliance rules (FVB)
    min_cores_per_vm: int = Field(default=8)
    min_org_cores: int = Field(default=16)
    
    # Windows Server 2025 Standard details
    default_product: str = "Windows Server"
    default_edition: str = "Standard"
    default_version: str = "2025"
    windows_2025_gvlk: str = "TVRH6-WHNXV-R9WG3-9XRFY-MY832"
    
    # Enforcement Tier: 1 (pre-boot admission), 2 (platform RBAC gating), 3 (detection/alerting)
    enforcement_tier: int = Field(
        default_factory=lambda: int(os.getenv("ENFORCEMENT_TIER", "1"))
    )
    
    controller_host: str = Field(
        default_factory=lambda: os.getenv("CONTROLLER_HOST", "0.0.0.0")
    )
    controller_port: int = Field(
        default_factory=lambda: int(os.getenv("CONTROLLER_PORT", "8000"))
    )
    api_token: str = Field(
        default_factory=lambda: os.getenv("API_TOKEN", "weautomate-secret-token")
    )


settings = Settings()
