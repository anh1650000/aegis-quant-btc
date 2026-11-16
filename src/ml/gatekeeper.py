"""Deterministic gate that prevents unnecessary LLM calls."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True, slots=True)
class GateDecision:
    allowed: bool
    probability: float
    confluence: bool
    reasons: tuple[str, ...]


def evaluate_gate(
    probability: float,
    indicators: Mapping[str, float],
    threshold: float = 0.65,
) -> GateDecision:
    """Allow an agent call only when probability and technical confluence pass."""
    if not isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("probability must be a finite value between 0 and 1.")
    if not 0 < threshold < 1:
        raise ValueError("threshold must be between 0 and 1.")

    rsi = indicators.get("rsi")
    close = indicators.get("close")
    lower = indicators.get("bb_lower")
    upper = indicators.get("bb_upper")
    volume_ratio = indicators.get("volume_ratio")
    confluence = (
        (rsi is not None and (rsi <= 30 or rsi >= 70))
        or (
            close is not None
            and lower is not None
            and upper is not None
            and (close <= lower or close >= upper)
        )
        or (volume_ratio is not None and volume_ratio >= 1.5)
    )
    reasons: list[str] = []
    if probability <= threshold:
        reasons.append("ml_probability_at_or_below_threshold")
    if not confluence:
        reasons.append("technical_confluence_missing")
    return GateDecision(
        allowed=probability > threshold and confluence,
        probability=probability,
        confluence=confluence,
        reasons=tuple(reasons),
    )
