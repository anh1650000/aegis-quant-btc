"""Deterministic technical indicators used by the gatekeeper."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def calculate_indicators(rows: Sequence[Sequence[float]]) -> dict[str, float]:
    """Calculate RSI, Bollinger bands, and volume ratio from OHLCV rows."""
    values = np.asarray(rows, dtype=float)
    if values.ndim != 2 or values.shape[1] < 6 or len(values) < 20:
        raise ValueError("At least 20 OHLCV rows with six columns are required.")
    close = values[:, 4]
    high = values[:, 2]
    low = values[:, 3]
    volume = values[:, 5]
    deltas = np.diff(close)
    gains = np.maximum(deltas, 0)
    losses = np.maximum(-deltas, 0)
    avg_gain = np.mean(gains[-14:])
    avg_loss = np.mean(losses[-14:])
    rsi = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    window = close[-20:]
    mean = float(np.mean(window))
    deviation = float(np.std(window))
    volume_mean = float(np.mean(volume[-20:]))
    previous_close = np.roll(close, 1)
    previous_close[0] = close[0]
    true_range = np.maximum(high - low, np.maximum(abs(high - previous_close), abs(low - previous_close)))
    return {
        "close": float(close[-1]),
        "rsi": rsi,
        "bb_lower": mean - 2 * deviation,
        "bb_upper": mean + 2 * deviation,
        "volume_ratio": float(volume[-1] / volume_mean) if volume_mean else 1.0,
        "atr": float(np.mean(true_range[-14:])),
    }
