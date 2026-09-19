"""Outbound-only VM Agent service for Windows Server 2025."""

import json
import logging
import os
import pathlib
import time
import uuid
from typing import Optional, Dict, Any
import httpx

from weautomate.agent.hardware import (
    get_hypervisor_uuid,
    get_core_count,
    get_hostname,
    get_local_ip,
)
from weautomate.agent.activation import get_windows_activation_status

logger = logging.getLogger("weautomate.agent")


class VMAgent:
    """Outbound VM Agent. Communicates exclusively outbound via HTTPS with local state caching."""

    def __init__(
        self,
        controller_url: str = "http://127.0.0.1:8000",
        cache_path: Optional[str] = None,
        custom_uuid: Optional[str] = None,
        custom_cores: Optional[int] = None,
        server_farm: Optional[str] = None,
        client: Optional[httpx.Client] = None,
    ):
        self.controller_url = controller_url.rstrip("/")
        self.cache_path = pathlib.Path(cache_path or "agent_cache.json")
        self.hypervisor_uuid = custom_uuid or get_hypervisor_uuid()
        self.core_count = custom_cores or get_core_count()
        self.hostname = get_hostname()
        self.server_farm = server_farm or "primary-server-farm"
        self.client = client or httpx.Client(timeout=10.0)
        self.active_lease_id: Optional[int] = None
        self.request_id: Optional[str] = None
        self.request_id = self._load_or_create_request_id()
        self._running = False

    def _load_or_create_request_id(self) -> str:
        """Loads cached request_id to guarantee idempotency across reboots, or creates a new one."""
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                if "request_id" in data:
                    return data["request_id"]
            except Exception:
                pass

        new_req_id = f"req-{uuid.uuid4()}"
        self._save_cache({"request_id": new_req_id, "hypervisor_uuid": self.hypervisor_uuid})
        return new_req_id

    def _save_cache(self, extra: Dict[str, Any]):
        data = {
            "request_id": extra.get("request_id") or self.request_id,
            "hypervisor_uuid": self.hypervisor_uuid,
            "hostname": self.hostname,
            "active_lease_id": self.active_lease_id,
            "updated_at": time.time(),
        }
        data.update(extra)
        try:
            self.cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save local agent cache: %s", e)

    def register(self) -> bool:
        """Registers the VM identity with the license controller."""
        payload = {
            "hostname": self.hostname,
            "hypervisor_uuid": self.hypervisor_uuid,
            "core_count": self.core_count,
            "server_farm": self.server_farm,
            "ip_address": get_local_ip(),
            "os_version": "Windows Server 2025 Standard",
            "activation_status": get_windows_activation_status().get("status", "Licensed"),
        }
        url = f"{self.controller_url}/api/v1/vms/register"
        for attempt in range(1, 4):
            try:
                resp = self.client.post(url, json=payload)
                if resp.status_code in (200, 201):
                    logger.info("Successfully registered VM %s (%s)", self.hostname, self.hypervisor_uuid)
                    return True
                logger.warning("Register response %d: %s", resp.status_code, resp.text)
            except Exception as e:
                logger.warning("Registration attempt %d failed: %s", attempt, e)
                time.sleep(attempt * 0.5)
        return False

    def acquire_lease(self) -> bool:
        """Requests dynamic core lease from controller using idempotent request_id."""
        url = f"{self.controller_url}/api/v1/leases/allocate"
        payload = {
            "hypervisor_uuid": self.hypervisor_uuid,
            "request_id": self.request_id,
            "requested_cores": self.core_count,
        }
        for attempt in range(1, 4):
            try:
                resp = self.client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    self.active_lease_id = data.get("id") or data.get("lease_id")
                    self._save_cache({"active_lease_id": self.active_lease_id})
                    logger.info("Lease acquired successfully: Lease ID #%s", self.active_lease_id)
                    return True
                else:
                    logger.warning("Lease allocation denied (%d): %s", resp.status_code, resp.text)
                    return False
            except Exception as e:
                logger.warning("Lease request attempt %d failed: %s", attempt, e)
                time.sleep(attempt * 0.5)
        return False

    def send_heartbeat(self) -> bool:
        """Renews current active lease."""
        url = f"{self.controller_url}/api/v1/leases/heartbeat"
        payload = {"hypervisor_uuid": self.hypervisor_uuid}
        try:
            resp = self.client.post(url, json=payload)
            if resp.status_code == 200:
                return True
            logger.warning("Heartbeat returned status %d: %s", resp.status_code, resp.text)
            return False
        except Exception as e:
            logger.warning("Heartbeat failed: %s", e)
            return False

    def notify_stopping(self) -> bool:
        """Notifies controller of graceful shutdown."""
        url = f"{self.controller_url}/api/v1/vms/stopping"
        payload = {"hypervisor_uuid": self.hypervisor_uuid}
        try:
            resp = self.client.post(url, json=payload)
            logger.info("Shutdown signal sent to controller.")
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Failed to send shutdown signal: %s", e)
            return False

    def close(self):
        self.client.close()
