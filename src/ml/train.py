"""Download Binance history and train a local sample LightGBM model."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from src.data.fetcher import MarketDataFetcher
from src.ml.predictor import train_sample_model


async def train_from_binance(
    output_path: str | Path | None = None,
    candle_limit: int = 1000,
) -> Path:
    """Fetch public 1h history and save a sample model locally."""
    data = await MarketDataFetcher(timeframes=("1h",), candle_limit=candle_limit).fetch()
    destination = output_path or os.getenv("MODEL_PATH", "data/model_btc.txt")
    return train_sample_model(data.candles["1h"], destination)


if __name__ == "__main__":
    asyncio.run(train_from_binance())
