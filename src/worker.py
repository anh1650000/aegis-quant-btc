"""Long-running worker entry point for the containerized paper/testnet runtime."""

from __future__ import annotations

import asyncio
import logging
import os

LOGGER = logging.getLogger(__name__)


async def run_worker() -> None:
    """Keep the worker alive; pipeline wiring can be injected by the deployment."""
    interval = int(os.getenv("WORKER_INTERVAL_SECONDS", "900"))
    while True:
        LOGGER.info("AegisQuant worker heartbeat", extra={"trading_mode": os.getenv("TRADING_MODE", "DRY_RUN")})
        await asyncio.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
