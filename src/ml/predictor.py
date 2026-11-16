"""LightGBM probability prediction with explicit feature contracts."""

from __future__ import annotations

from pathlib import Path
import os
from typing import Sequence

import numpy as np

try:
    import lightgbm as lgb
except ImportError as exc:  # pragma: no cover - environment setup concern
    raise ImportError("Install lightgbm to use the ML predictor.") from exc


FEATURE_NAMES = ("return_1", "volatility", "volume_ratio", "distance_ema")


def build_features(rows: Sequence[Sequence[float]]) -> np.ndarray:
    """Build deterministic features from OHLCV rows.

    Rows must contain ``timestamp, open, high, low, close, volume``.
    """
    values = np.asarray(rows, dtype=float)
    if values.ndim != 2 or values.shape[1] < 6 or len(values) < 3:
        raise ValueError("At least three OHLCV rows with six columns are required.")
    close = values[:, 4]
    volume = values[:, 5]
    returns = np.diff(np.log(close), prepend=np.log(close[0]))
    volatility = np.array(
        [np.std(returns[max(0, i - 19): i + 1]) for i in range(len(values))]
    )
    volume_mean = np.array(
        [np.mean(volume[max(0, i - 19): i + 1]) for i in range(len(values))]
    )
    volume_ratio = np.divide(volume, volume_mean, out=np.ones_like(volume), where=volume_mean != 0)
    ema = np.empty_like(close)
    ema[0] = close[0]
    alpha = 2 / 21
    for index in range(1, len(close)):
        ema[index] = alpha * close[index] + (1 - alpha) * ema[index - 1]
    distance_ema = np.divide(close - ema, ema, out=np.zeros_like(close), where=ema != 0)
    return np.column_stack((returns, volatility, volume_ratio, distance_ema))


class ProbabilityPredictor:
    """Load a LightGBM binary classifier and predict upward-move probability."""

    def __init__(self, model_path: str | Path) -> None:
        self.model = lgb.Booster(model_file=str(model_path))
        missing = set(FEATURE_NAMES) - set(self.model.feature_name())
        if missing:
            raise ValueError(f"Model is missing features: {sorted(missing)}")

    def predict_probability(self, features: Sequence[float]) -> float:
        """Return a bounded probability for one feature vector."""
        values = np.asarray(features, dtype=float)
        if values.shape != (len(FEATURE_NAMES),) or not np.isfinite(values).all():
            raise ValueError(f"features must be {len(FEATURE_NAMES)} finite values.")
        prediction = float(self.model.predict(values.reshape(1, -1))[0])
        return min(1.0, max(0.0, prediction))

    def predict_from_ohlcv(self, rows: Sequence[Sequence[float]]) -> float:
        """Predict from the latest OHLCV-derived feature vector."""
        return self.predict_probability(build_features(rows)[-1])


def train_sample_model(
    rows: Sequence[Sequence[float]],
    output_path: str | Path | None = None,
    horizon: int = 4,
    move_threshold: float = 0.005,
) -> Path:
    """Train a small local sample model from historical OHLCV data."""
    features = build_features(rows)
    closes = np.asarray(rows, dtype=float)[:, 4]
    if horizon <= 0 or len(closes) <= horizon:
        raise ValueError("Not enough rows for the requested horizon.")
    labels = np.zeros(len(closes), dtype=int)
    labels[:-horizon] = (
        (closes[horizon:] / closes[:-horizon] - 1) >= move_threshold
    ).astype(int)
    usable = slice(20, len(closes) - horizon)
    if labels[usable].sum() == 0 or labels[usable].sum() == len(labels[usable]):
        raise ValueError("Training data must contain both target classes.")
    dataset = lgb.Dataset(features[usable], label=labels[usable], feature_name=list(FEATURE_NAMES))
    model = lgb.train(
        {"objective": "binary", "metric": "binary_logloss", "verbosity": -1, "seed": 42},
        dataset,
        num_boost_round=40,
    )
    destination = Path(output_path or os.getenv("MODEL_PATH", "data/model_btc.txt"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(destination))
    return destination
