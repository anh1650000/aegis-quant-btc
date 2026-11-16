"""Dry-run execution that never sends an order to an exchange."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PaperExecution:
    """Record the last approved signal as a simulated order."""

    last_order: dict[str, Any] | None = None

    def submit(self, signal: dict[str, Any]) -> dict[str, Any]:
        order = {"mode": "PAPER", "status": "SIMULATED", "signal": signal}
        self.last_order = order
        return order
