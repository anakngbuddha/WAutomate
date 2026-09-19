"""CLI entrypoint for running the WeAutomate VM Agent as a background service or console task."""

import argparse
import logging
import signal
import sys
import time

from weautomate.agent.agent import VMAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("weautomate.agent.cli")


def main():
    parser = argparse.ArgumentParser(description="WeAutomate Windows Server 2025 VM Agent")
    parser.add_argument(
        "--controller-url",
        default="http://127.0.0.1:8000",
        help="URL of the WeAutomate License Controller (outbound only)",
    )
    parser.add_argument(
        "--cache-path",
        default="C:\\ProgramData\\WeAutomate\\agent_cache.json",
        help="Path to local cache file",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=30,
        help="Heartbeat interval in seconds",
    )
    parser.add_argument(
        "--server-farm",
        default="primary-server-farm",
        help="Assigned server farm name",
    )
    args = parser.parse_args()

    logger.info("Starting WeAutomate VM Agent...")
    logger.info("Target Controller: %s", args.controller_url)

    agent = VMAgent(
        controller_url=args.controller_url,
        cache_path=args.cache_path,
        server_farm=args.server_farm,
    )

    # 1. Register VM identity
    logger.info("Registering VM %s (UUID: %s, Cores: %d)...", agent.hostname, agent.hypervisor_uuid, agent.core_count)
    if not agent.register():
        logger.error("Failed to register with controller. Retrying in background...")

    # 2. Acquire core lease
    logger.info("Requesting core lease from controller...")
    if agent.acquire_lease():
        logger.info("Lease acquired successfully! Lease ID: %s", agent.active_lease_id)
    else:
        logger.warning("Could not acquire lease immediately (capacity may be full). Agent will keep trying via heartbeats.")

    # Graceful shutdown handler
    def handle_exit(signum, frame):
        logger.info("Termination signal received. Notifying controller of graceful shutdown...")
        agent.notify_stopping()
        agent.close()
        logger.info("Agent stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # 3. Heartbeat loop
    logger.info("Entering heartbeat loop (interval: %ds)...", args.heartbeat_interval)
    while True:
        try:
            if not agent.active_lease_id:
                agent.acquire_lease()
            else:
                agent.send_heartbeat()
        except Exception as e:
            logger.warning("Heartbeat loop exception: %s", e)
        time.sleep(args.heartbeat_interval)


if __name__ == "__main__":
    main()
