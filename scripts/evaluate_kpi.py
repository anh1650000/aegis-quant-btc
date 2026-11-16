"""Evaluate dry-run KPI metrics from the bounded audit JSONL file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def evaluate(path: str | Path) -> dict[str, Any]:
    if not Path(path).exists():
        return {
            "sessions": 0,
            "winrate": 0.0,
            "max_drawdown": 0.0,
            "hallucination_rate": 0.0,
            "token_savings_rate": 0.0,
        }
    records = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    results = [float(record["trade_result"]) for record in records if record.get("trade_result") is not None]
    wins = [value for value in results if value > 0]
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for result in results:
        equity += result
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    used = sum(int(record.get("tokens_used", 0)) for record in records)
    baseline = sum(int(record.get("tokens_without_gatekeeper", 0)) for record in records)
    return {
        "sessions": len(records),
        "winrate": len(wins) / len(results) if results else 0.0,
        "max_drawdown": max_drawdown,
        "hallucination_rate": (
            sum(bool(record.get("hallucination_detected")) for record in records) / len(records)
            if records else 0.0
        ),
        "token_savings_rate": (1 - used / baseline) if baseline else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="data/audit_log.jsonl")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.path), indent=2))


if __name__ == "__main__":
    main()
