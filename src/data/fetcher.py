"""Asynchronous public market-data collection for BTC/USDT futures."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

import ccxt.async_support as ccxt

LOGGER = logging.getLogger(__name__)


class ExchangeClient(Protocol):
    """Subset of the CCXT exchange interface used by the fetcher."""

    async def fetch_ohlcv(
        self, symbol: str, timeframe: str, since: int | None = None, limit: int | None = None
    ) -> list[list[float]]:
        ...

    async def fetch_funding_rate(self, symbol: str) -> dict[str, Any]:
        ...

    async def fetch_open_interest(self, symbol: str) -> dict[str, Any]:
        ...

    async def close(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class MarketData:
    """Raw market data fetched from the exchange."""

    symbol: str
    candles: dict[str, list[list[float]]]
    funding_rate: float | None
    open_interest: float | None

    def to_minified_json(self) -> str:
        """Serialize the latest market snapshot without whitespace."""
        latest_candles = {
            timeframe: rows[-1] for timeframe, rows in self.candles.items() if rows
        }
        payload = {
            "symbol": self.symbol,
            "candles": latest_candles,
            "funding_rate": self.funding_rate,
            "open_interest": self.open_interest,
        }
        return json.dumps(payload, separators=(",", ":"), allow_nan=False)


def _as_float(value: Any) -> float | None:
    """Convert an optional exchange value to a finite float."""
    if value is None:
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted


def _open_interest_value(response: dict[str, Any]) -> float | None:
    """Read the exchange's normalized open-interest amount field."""
    return _as_float(response.get("openInterestAmount", response.get("openInterest")))


class MarketDataFetcher:
    """Fetch BTC/USDT perpetual futures data from Binance's public API."""

    def __init__(
        self,
        symbol: str = "BTC/USDT:USDT",
        timeframes: tuple[str, ...] = ("15m", "1h", "4h"),
        candle_limit: int = 200,
        exchange: ExchangeClient | None = None,
    ) -> None:
        if not timeframes:
            raise ValueError("At least one timeframe is required.")
        if candle_limit <= 0:
            raise ValueError("candle_limit must be positive.")

        self.symbol = symbol
        self.timeframes = timeframes
        self.candle_limit = candle_limit
        self._exchange = exchange

    async def fetch(self) -> MarketData:
        """Fetch all configured candles and current derivatives metrics."""
        exchange = self._exchange or ccxt.binance(
            {"enableRateLimit": True, "options": {"defaultType": "future"}}
        )
        owns_exchange = self._exchange is None

        try:
            candles = {
                timeframe: await exchange.fetch_ohlcv(
                    self.symbol, timeframe, limit=self.candle_limit
                )
                for timeframe in self.timeframes
            }
            funding = await exchange.fetch_funding_rate(self.symbol)
            open_interest = await exchange.fetch_open_interest(self.symbol)
            result = MarketData(
                symbol=self.symbol,
                candles=candles,
                funding_rate=_as_float(funding.get("fundingRate")),
                open_interest=_open_interest_value(open_interest),
            )
            LOGGER.info(
                "Fetched market data",
                extra={
                    "symbol": self.symbol,
                    "timeframes": self.timeframes,
                    "candle_limit": self.candle_limit,
                },
            )
            return result
        finally:
            if owns_exchange:
                await exchange.close()
