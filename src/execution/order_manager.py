"""Binance Futures order management with dry-run and testnet isolation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

import ccxt.async_support as ccxt


class TradingMode(StrEnum):
    DRY_RUN = "DRY_RUN"
    TESTNET = "TESTNET"


class Exchange(Protocol):
    async def set_margin_mode(self, margin_mode: str, symbol: str, params: dict[str, Any] | None = None) -> Any:
        ...

    async def set_leverage(self, leverage: int, symbol: str, params: dict[str, Any] | None = None) -> Any:
        ...

    async def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: float | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        ...

    async def cancel_order(self, order_id: str, symbol: str, params: dict[str, Any] | None = None) -> Any:
        ...

    async def close(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class OrderRequest:
    symbol: str
    side: str
    amount: float
    entry_price: float | None
    stop_loss: float
    take_profit: float
    leverage: int = 10
    entry_type: str = "MARKET"


class OrderManager:
    """Submit one entry and two reduce-only protective orders."""

    def __init__(
        self,
        mode: TradingMode | str | None = None,
        exchange: Exchange | None = None,
    ) -> None:
        self.mode = TradingMode(mode or os.getenv("TRADING_MODE", TradingMode.DRY_RUN))
        if self.mode is TradingMode.TESTNET and exchange is None:
            if not os.getenv("BINANCE_API_KEY") or not os.getenv("BINANCE_SECRET"):
                raise ValueError("TESTNET mode requires BINANCE_API_KEY and BINANCE_SECRET.")
            self._exchange = ccxt.binance(
                {
                    "apiKey": os.getenv("BINANCE_API_KEY", ""),
                    "secret": os.getenv("BINANCE_SECRET", ""),
                    "enableRateLimit": True,
                    "options": {"defaultType": "future"},
                }
            )
            self._exchange.set_sandbox_mode(True)
            self._owns_exchange = True
        else:
            self._exchange = exchange
            self._owns_exchange = False

    async def submit_atomic(self, request: OrderRequest) -> dict[str, Any]:
        """Submit entry/SL/TP or return a fully local dry-run result."""
        self._validate_request(request)
        if self.mode is TradingMode.DRY_RUN:
            return {
                "mode": self.mode.value,
                "status": "SIMULATED",
                "entry": request.__dict__ if hasattr(request, "__dict__") else {
                    "symbol": request.symbol,
                    "side": request.side,
                    "amount": request.amount,
                    "entry_price": request.entry_price,
                    "stop_loss": request.stop_loss,
                    "take_profit": request.take_profit,
                    "leverage": request.leverage,
                    "entry_type": request.entry_type,
                },
            }
        if self._exchange is None:
            raise RuntimeError("TESTNET mode requires an exchange client.")

        opposite = "sell" if request.side.lower() == "buy" else "buy"
        entry: dict[str, Any] | None = None
        protective: list[dict[str, Any]] = []
        try:
            await self._exchange.set_margin_mode("isolated", request.symbol)
            await self._exchange.set_leverage(request.leverage, request.symbol)
            entry = await self._exchange.create_order(
                request.symbol,
                request.entry_type,
                request.side.lower(),
                request.amount,
                request.entry_price if request.entry_type.upper() == "LIMIT" else None,
            )
            protective.append(await self._exchange.create_order(
                request.symbol,
                "STOP_MARKET",
                opposite,
                request.amount,
                None,
                {"stopPrice": request.stop_loss, "reduceOnly": True, "closePosition": True},
            ))
            protective.append(await self._exchange.create_order(
                request.symbol,
                "TAKE_PROFIT_MARKET",
                opposite,
                request.amount,
                None,
                {"stopPrice": request.take_profit, "reduceOnly": True, "closePosition": True},
            ))
            return {"mode": self.mode.value, "status": "SUBMITTED", "entry": entry, "protective": protective}
        except (ccxt.BaseError, OSError, RuntimeError, ValueError):
            for order in protective:
                if order.get("id"):
                    await self._exchange.cancel_order(order["id"], request.symbol)
            if entry and entry.get("id"):
                await self._exchange.cancel_order(entry["id"], request.symbol)
            raise

    async def close(self) -> None:
        if self._owns_exchange and self._exchange is not None:
            await self._exchange.close()

    @staticmethod
    def _validate_request(request: OrderRequest) -> None:
        if request.side.lower() not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell.")
        if request.entry_type.upper() not in {"MARKET", "LIMIT"}:
            raise ValueError("entry_type must be MARKET or LIMIT.")
        if request.amount <= 0 or request.stop_loss <= 0 or request.take_profit <= 0:
            raise ValueError("amount and protective prices must be positive.")
        if request.leverage <= 0 or request.leverage > 10:
            raise ValueError("leverage must be between 1x and 10x.")
        if request.entry_type.upper() == "LIMIT" and (request.entry_price is None or request.entry_price <= 0):
            raise ValueError("LIMIT orders require a positive entry_price.")
