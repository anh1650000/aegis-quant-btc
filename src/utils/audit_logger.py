"""Bounded JSONL audit logging for hallucination and quota review."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from uuid import uuid4


class AuditLogger:
    """Persist at most the first 50 complete pipeline sessions."""

    def __init__(self, path: str | Path | None = None, max_sessions: int = 50) -> None:
        self.path = Path(path or os.getenv("AUDIT_LOG_PATH", "data/audit_log.jsonl"))
        self.max_sessions = max_sessions

    def _count(self) -> int:
        if not self.path.exists():
            return 0
        return sum(1 for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip())

    def log_session(
        self,
        input_json: dict[str, Any],
        hydrogen_output: Any,
        argon_analyst_output: Any,
        argon_critic_output: Any,
        guardrails_decision: Any,
        tokens_used: int,
        tokens_without_gatekeeper: int,
        trade_result: float | None = None,
        hallucination_detected: bool = False,
        session_id: str | None = None,
    ) -> bool:
        """Append one audit record, returning false after the 50-session cap."""
        if self._count() >= self.max_sessions:
            return False
        record = {
            "session_id": session_id or str(uuid4()),
            "timestamp": time.time(),
            "input_json": input_json,
            "hydrogen_output": hydrogen_output,
            "argon_analyst_output": argon_analyst_output,
            "argon_critic_output": argon_critic_output,
            "guardrails_decision": guardrails_decision,
            "tokens_used": tokens_used,
            "tokens_without_gatekeeper": tokens_without_gatekeeper,
            "trade_result": trade_result,
            "hallucination_detected": hallucination_detected,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":"), default=str) + "\n")
        return True
