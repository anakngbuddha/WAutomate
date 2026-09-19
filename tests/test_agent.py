"""Tests for the outbound-only VM Agent."""

import json
import pytest
from weautomate.agent.agent import VMAgent
from weautomate.config import settings
from weautomate.kms.validator import validate_gvlk, WINDOWS_2025_STANDARD_GVLK


def test_agent_outbound_registration_and_lease(client, tmp_path):
    """Test VM agent registering and acquiring lease via outbound HTTP."""
    cache_file = tmp_path / "agent_cache.json"
    agent = VMAgent(
        controller_url="http://testserver",
        cache_path=str(cache_file),
        custom_uuid="agent-uuid-001",
        custom_cores=8,
        server_farm=settings.server_farm_name,
        client=client,
    )

    # 1. Register
    reg_ok = agent.register()
    assert reg_ok

    # 2. Acquire Lease
    lease_ok = agent.acquire_lease()
    assert lease_ok
    assert agent.active_lease_id is not None

    # Check cache file exists and has request_id
    assert cache_file.exists()
    cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cache_data["request_id"] == agent.request_id
    assert cache_data["active_lease_id"] == agent.active_lease_id

    # 3. Heartbeat
    hb_ok = agent.send_heartbeat()
    assert hb_ok

    # 4. Notify stopping
    stop_ok = agent.notify_stopping()
    assert stop_ok


def test_windows_2025_standard_gvlk_format():
    """Verify that the official Windows Server 2025 Standard GVLK key matches Microsoft 5x5 format."""
    assert WINDOWS_2025_STANDARD_GVLK == "TVRH6-WHNXV-R9WG3-9XRFY-MY832"
    assert validate_gvlk(WINDOWS_2025_STANDARD_GVLK) is True
