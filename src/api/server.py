"""Typed API surface, live Binance Futures sync, and Vue SPA host for AegisQuant."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import Body, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.data.indicators import calculate_indicators
from src.risk.guardrails import Direction, calculate_liquidation_price

LOGGER = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"

DEFAULT_BTC_PRICE = 64590.6
DEFAULT_ATR = 507.25
DEFAULT_RSI = 45.01
DEFAULT_FUNDING = 0.0000115
DEFAULT_OI = 93834.4
DEFAULT_VND_RATE = 25716.0


class KillSwitchPayload(BaseModel):
    enabled: bool = True


class ModePayload(BaseModel):
    mode: str


def _utc_time() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


def _build_presets(
    base_price: float = DEFAULT_BTC_PRICE,
    atr: float = DEFAULT_ATR,
    rsi: float = DEFAULT_RSI,
    funding_rate: float = DEFAULT_FUNDING,
    open_interest: float = DEFAULT_OI,
) -> dict[str, dict[str, Any]]:
    price = round(base_price, 1)
    safe_atr = max(atr, 50.0)
    funding_pct = round(funding_rate * 100, 4)

    long_entry = price
    long_sl = round(long_entry - 1.5 * safe_atr, 1)
    long_tp = round(long_entry + 3.3 * safe_atr, 1)
    long_liq = round(calculate_liquidation_price(long_entry, Direction.LONG, 10), 1)
    long_rr = round(abs(long_tp - long_entry) / abs(long_entry - long_sl), 2)

    short_entry = price
    short_sl = round(short_entry + 1.3 * safe_atr, 1)
    short_tp = round(short_entry - 1.8 * safe_atr, 1)
    short_liq = round(calculate_liquidation_price(short_entry, Direction.SHORT, 10), 1)
    short_rr = round(abs(short_entry - short_tp) / abs(short_sl - short_entry), 2)

    return {
        "long_approved": {
            "market_snapshot": {
                "symbol": "BTC/USDT:USDT",
                "price": price,
                "entry": long_entry,
                "sl": long_sl,
                "tp": long_tp,
                "liquidation_price": long_liq,
                "rr_ratio": long_rr,
            },
            "agent_debate_stream": [
                {
                    "agent": "hydrogen",
                    "status": "cached",
                    "summary": [
                        "US Core CPI prints in-line at 0.2% MoM; no FOMC rate hike scheduled within 4h window.",
                        "Spot BTC ETF flow stable while perpetual open_interest holds near session baseline.",
                        "HIGH_IMPACT_EVENT flag: FALSE (Macro Circuit Breaker disarmed).",
                    ],
                },
                {
                    "agent": "argon_analyst",
                    "decision": "LONG",
                    "confidence_score": 82,
                    "rationale": (
                        f"Confluence confirmed: close={price} holding intraday support, "
                        f"rsi_1h={rsi:.2f}, funding_rate={funding_pct:+.4f}%, open_interest={open_interest:.1f}, "
                        f"ml_probability=0.74 (>0.65 gate). ATR(14)={safe_atr:.2f} yields "
                        f"entry={long_entry}, sl={long_sl} (1.50x ATR), tp={long_tp} (R:R={long_rr:.2f})."
                    ),
                },
                {
                    "agent": "argon_critic",
                    "approve_trade": True,
                    "adjusted_confidence": 78,
                    "critical_flaws": [
                        f"Perpetual funding_rate={funding_pct:+.4f}% remains muted; watch resistance near {round(long_tp, 0):.0f}.",
                        f"Stop distance {round(long_entry - long_sl, 1)} USDT (1.50x ATR) passes [0.5, 2.5] ATR bounds; liq at {long_liq} is >30% farther than SL.",
                    ],
                },
            ],
            "status": {
                "gatekeeper": True,
                "remaining_daily_quota_estimate": 92,
                "kill_switch": False,
            },
            "portfolio": {
                "open_positions": 1,
                "ml_probability": 0.74,
                "atr": round(safe_atr, 2),
                "rsi": round(rsi, 2),
                "funding_rate": funding_rate,
                "open_interest": open_interest,
                "direction": "LONG",
            },
        },
        "short_rejected": {
            "market_snapshot": {
                "symbol": "BTC/USDT:USDT",
                "price": price,
                "entry": short_entry,
                "sl": short_sl,
                "tp": short_tp,
                "liquidation_price": short_liq,
                "rr_ratio": short_rr,
            },
            "agent_debate_stream": [
                {
                    "agent": "hydrogen",
                    "status": "cached",
                    "summary": [
                        "DXY index ticking +0.18% intraday; risk-asset momentum cooling near session highs.",
                        "No CPI/FOMC/NFP releases scheduled in next 4h; macro news calendar clear.",
                        "HIGH_IMPACT_EVENT flag: FALSE (Macro Circuit Breaker disarmed).",
                    ],
                },
                {
                    "agent": "argon_analyst",
                    "decision": "SHORT",
                    "confidence_score": 68,
                    "rationale": (
                        f"Intraday fade setup: close={price}, rsi_1h={rsi:.2f}, "
                        f"ml_probability=0.69. Proposed entry={short_entry}, sl={short_sl}, tp={short_tp} "
                        f"yields R:R={short_rr:.2f}."
                    ),
                },
                {
                    "agent": "argon_critic",
                    "approve_trade": False,
                    "adjusted_confidence": 41,
                    "critical_flaws": [
                        f"VETO: R:R={short_rr:.2f} violates hard-coded minimum R:R >= 1.80 threshold (risk_reward_below_1.8).",
                        f"Short squeeze risk above {short_sl} if spot demand absorbs resting asks.",
                    ],
                },
            ],
            "status": {
                "gatekeeper": True,
                "remaining_daily_quota_estimate": 90,
                "kill_switch": False,
            },
            "portfolio": {
                "open_positions": 0,
                "ml_probability": 0.69,
                "atr": round(safe_atr, 2),
                "rsi": round(rsi, 2),
                "funding_rate": funding_rate,
                "open_interest": open_interest,
                "direction": "SHORT",
            },
        },
        "macro_lock": {
            "market_snapshot": {
                "symbol": "BTC/USDT:USDT",
                "price": price,
                "entry": long_entry,
                "sl": long_sl,
                "tp": long_tp,
                "liquidation_price": long_liq,
                "rr_ratio": long_rr,
            },
            "agent_debate_stream": [
                {
                    "agent": "hydrogen",
                    "status": "cached",
                    "summary": [
                        "HIGH_IMPACT_EVENT: US FOMC Rate Decision & Fed Chair Press Conference in 45m.",
                        "Implied 1h BTC options volatility spiked to 78%; extreme wick risk around event release.",
                        "HIGH_IMPACT_EVENT flag: TRUE (Macro Circuit Breaker ARMED — blocking new executions).",
                    ],
                },
                {
                    "agent": "argon_analyst",
                    "decision": "LONG",
                    "confidence_score": 71,
                    "rationale": (
                        f"Technical setup at close={price}, rsi_1h={rsi:.2f}, ml_probability=0.71. "
                        "Execution deferred due to Hydrogen HIGH_IMPACT_EVENT alert."
                    ),
                },
                {
                    "agent": "argon_critic",
                    "approve_trade": False,
                    "adjusted_confidence": 28,
                    "critical_flaws": [
                        "HARD CIRCUIT BREAKER: high_impact_macro_event=True locks all new futures positions within 4h window.",
                        "Stop-loss slippage risk during FOMC announcement invalidates 1.5% max risk cap.",
                    ],
                },
            ],
            "status": {
                "gatekeeper": True,
                "remaining_daily_quota_estimate": 89,
                "kill_switch": False,
            },
            "portfolio": {
                "open_positions": 0,
                "ml_probability": 0.71,
                "atr": round(safe_atr, 2),
                "rsi": round(rsi, 2),
                "funding_rate": funding_rate,
                "open_interest": open_interest,
                "direction": "NEUTRAL",
            },
        },
        "neutral_standby": {
            "market_snapshot": {
                "symbol": "BTC/USDT:USDT",
                "price": price,
                "entry": None,
                "sl": None,
                "tp": None,
                "liquidation_price": None,
                "rr_ratio": None,
            },
            "agent_debate_stream": [
                {
                    "agent": "hydrogen",
                    "status": "cached",
                    "summary": [
                        "Macro regime neutral; cached sentiment valid for next 84 minutes (0 extra tokens used).",
                        "No major Tier-1 US macro releases within the next 4h window.",
                        "HIGH_IMPACT_EVENT flag: FALSE.",
                    ],
                },
                {
                    "agent": "argon_analyst",
                    "decision": "NEUTRAL",
                    "confidence_score": 0,
                    "rationale": (
                        f"Gatekeeper closed at close={price} (ml_probability=0.42 < 0.65 threshold). "
                        "Gemini 4 Argon bypassed to preserve Google AI Pro daily quota."
                    ),
                },
                {
                    "agent": "argon_critic",
                    "approve_trade": False,
                    "adjusted_confidence": 0,
                    "critical_flaws": [
                        "Standby mode: 85% market chop filtered at LightGBM Tier 2 Gatekeeper (0 LLM tokens consumed)."
                    ],
                },
            ],
            "status": {
                "gatekeeper": False,
                "remaining_daily_quota_estimate": 95,
                "kill_switch": False,
            },
            "portfolio": {
                "open_positions": 0,
                "ml_probability": 0.42,
                "atr": round(safe_atr, 2),
                "rsi": round(rsi, 2),
                "funding_rate": funding_rate,
                "open_interest": open_interest,
                "direction": "NEUTRAL",
            },
        },
    }


def _default_history(base_price: float = DEFAULT_BTC_PRICE, atr: float = DEFAULT_ATR) -> list[dict[str, Any]]:
    p = round(base_price, 1)
    s = max(round(atr, 1), 100.0)
    return [
        {
            "id": "GRD-2048",
            "timestamp": "17:45:00 UTC",
            "symbol": "BTC/USDT:USDT",
            "direction": "LONG",
            "entry": p,
            "sl": round(p - 1.5 * s, 1),
            "tp": round(p + 3.3 * s, 1),
            "rr_ratio": 2.20,
            "status": "APPROVED",
            "reasons": ["passed_all_guardrails"],
        },
        {
            "id": "GRD-2047",
            "timestamp": "16:30:00 UTC",
            "symbol": "BTC/USDT:USDT",
            "direction": "SHORT",
            "entry": p,
            "sl": round(p + 1.3 * s, 1),
            "tp": round(p - 1.8 * s, 1),
            "rr_ratio": 1.38,
            "status": "REJECTED",
            "reasons": ["risk_reward_below_1.8"],
        },
        {
            "id": "GRD-2046",
            "timestamp": "14:15:00 UTC",
            "symbol": "BTC/USDT:USDT",
            "direction": "LONG",
            "entry": round(p - 280.0, 1),
            "sl": round(p - 400.0, 1),
            "tp": round(p + 320.0, 1),
            "rr_ratio": 5.00,
            "status": "REJECTED",
            "reasons": ["stop_distance_outside_atr_bounds"],
        },
        {
            "id": "GRD-2045",
            "timestamp": "12:00:00 UTC",
            "symbol": "BTC/USDT:USDT",
            "direction": "LONG",
            "entry": round(p - 510.0, 1),
            "sl": round(p - 510.0 - 1.5 * s, 1),
            "tp": round(p - 510.0 + 3.3 * s, 1),
            "rr_ratio": 2.20,
            "status": "APPROVED",
            "reasons": ["passed_all_guardrails"],
        },
        {
            "id": "GRD-2044",
            "timestamp": "08:00:00 UTC",
            "symbol": "BTC/USDT:USDT",
            "direction": "SHORT",
            "entry": round(p + 320.0, 1),
            "sl": round(p + 320.0 + 1.5 * s, 1),
            "tp": round(p + 320.0 - 3.3 * s, 1),
            "rr_ratio": 2.20,
            "status": "REJECTED",
            "reasons": ["high_impact_macro_event"],
        },
    ]


class RuntimeState:
    """In-memory state store for AegisQuant dashboard API, live exchange sync, and WS stream."""

    def __init__(self, notifier: Any | None = None) -> None:
        self.notifier = notifier
        self.active_preset = "long_approved"
        self.presets = _build_presets()
        initial = deepcopy(self.presets[self.active_preset])
        self.kill_switch = False
        self.status: dict[str, Any] = initial["status"]
        self.portfolio: dict[str, Any] = {
            "mode": "PAPER",
            "balance_usdt": 10000.0,
            "max_risk_pct": 1.5,
            "leverage": 10,
            "margin_mode": "ISOLATED",
            "vnd_rate": DEFAULT_VND_RATE,
            "change_24h_pct": -1.04,
            "high_24h": 65776.5,
            "low_24h": 64073.7,
            "volume_24h": 9334191051.0,
            "market_source": "binance_futures_baseline",
            **initial["portfolio"],
        }
        self.stream: dict[str, Any] = {
            "market_snapshot": initial["market_snapshot"],
            "agent_debate_stream": initial["agent_debate_stream"],
            "system_status": self.status,
        }
        self.history: list[dict[str, Any]] = _default_history()

    async def refresh_from_exchange(self) -> dict[str, Any]:
        """Fetch live BTC/USDT perpetual futures data & USD/VND rate and recompute deterministic presets."""
        base_price = float(self.stream["market_snapshot"].get("price") or DEFAULT_BTC_PRICE)
        atr = float(self.portfolio.get("atr") or DEFAULT_ATR)
        rsi = float(self.portfolio.get("rsi") or DEFAULT_RSI)
        funding_rate = float(self.portfolio.get("funding_rate") or DEFAULT_FUNDING)
        open_interest = float(self.portfolio.get("open_interest") or DEFAULT_OI)
        vnd_rate = float(self.portfolio.get("vnd_rate") or DEFAULT_VND_RATE)
        synced = False

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                klines_resp, ticker_resp, prem_resp = await asyncio.gather(
                    client.get(
                        "https://fapi.binance.com/fapi/v1/klines",
                        params={"symbol": "BTCUSDT", "interval": "1h", "limit": 60},
                    ),
                    client.get(
                        "https://fapi.binance.com/fapi/v1/ticker/24hr",
                        params={"symbol": "BTCUSDT"},
                    ),
                    client.get(
                        "https://fapi.binance.com/fapi/v1/premiumIndex",
                        params={"symbol": "BTCUSDT"},
                    ),
                )
                klines_resp.raise_for_status()
                ticker_resp.raise_for_status()
                prem_resp.raise_for_status()

                raw_klines = klines_resp.json()
                ohlcv = [
                    [
                        int(row[0]),
                        float(row[1]),
                        float(row[2]),
                        float(row[3]),
                        float(row[4]),
                        float(row[5]),
                    ]
                    for row in raw_klines
                ]
                indicators = calculate_indicators(ohlcv)
                ticker = ticker_resp.json()
                premium = prem_resp.json()

                base_price = float(ticker.get("lastPrice", indicators["close"]))
                atr = float(indicators["atr"])
                rsi = float(indicators["rsi"])
                funding_rate = float(premium.get("lastFundingRate", funding_rate))

                self.portfolio["change_24h_pct"] = round(float(ticker.get("priceChangePercent", 0.0)), 2)
                self.portfolio["high_24h"] = float(ticker.get("highPrice", base_price))
                self.portfolio["low_24h"] = float(ticker.get("lowPrice", base_price))
                self.portfolio["volume_24h"] = float(ticker.get("quoteVolume", 0.0))
                self.portfolio["market_source"] = "binance_futures_live"
                synced = True
            except Exception as exc:
                LOGGER.warning("Binance Futures sync failed; keeping cached state", extra={"error": str(exc)})

            try:
                fx_resp = await client.get("https://open.er-api.com/v6/latest/USD")
                fx_resp.raise_for_status()
                rate = float(fx_resp.json().get("rates", {}).get("VND", vnd_rate))
                if rate > 10000:
                    vnd_rate = round(rate, 2)
            except Exception as exc:
                LOGGER.warning("USD/VND rate sync failed; keeping cached rate", extra={"error": str(exc)})

        self.portfolio["vnd_rate"] = vnd_rate
        self.presets = _build_presets(
            base_price=base_price,
            atr=atr,
            rsi=rsi,
            funding_rate=funding_rate,
            open_interest=open_interest,
        )
        preset = deepcopy(self.presets[self.active_preset])
        self.stream = {
            "market_snapshot": preset["market_snapshot"],
            "agent_debate_stream": preset["agent_debate_stream"],
            "system_status": {**preset["status"], "kill_switch": self.kill_switch},
        }
        self.portfolio.update(preset["portfolio"])
        if self.kill_switch:
            self.portfolio["open_positions"] = 0
            self.status["gatekeeper"] = False
        self.history = _default_history(base_price=base_price, atr=atr)
        return {"synced": synced, "price": base_price, "vnd_rate": vnd_rate}

    def apply_preset(self, preset_name: str) -> dict[str, Any]:
        if preset_name not in self.presets:
            raise KeyError(preset_name)
        self.active_preset = preset_name
        preset = deepcopy(self.presets[preset_name])
        self.kill_switch = False
        self.status = preset["status"]
        self.portfolio.update(preset["portfolio"])
        self.stream = {
            "market_snapshot": preset["market_snapshot"],
            "agent_debate_stream": preset["agent_debate_stream"],
            "system_status": self.status,
        }
        snapshot = preset["market_snapshot"]
        if preset_name == "short_rejected":
            self.history.insert(
                0,
                {
                    "id": f"GRD-{2050 + len(self.history)}",
                    "timestamp": _utc_time(),
                    "symbol": snapshot["symbol"],
                    "direction": "SHORT",
                    "entry": snapshot["entry"],
                    "sl": snapshot["sl"],
                    "tp": snapshot["tp"],
                    "rr_ratio": snapshot["rr_ratio"],
                    "status": "REJECTED",
                    "reasons": ["risk_reward_below_1.8"],
                },
            )
        elif preset_name == "macro_lock":
            self.history.insert(
                0,
                {
                    "id": f"GRD-{2050 + len(self.history)}",
                    "timestamp": _utc_time(),
                    "symbol": snapshot["symbol"],
                    "direction": "LONG",
                    "entry": snapshot["entry"],
                    "sl": snapshot["sl"],
                    "tp": snapshot["tp"],
                    "rr_ratio": snapshot["rr_ratio"],
                    "status": "REJECTED",
                    "reasons": ["high_impact_macro_event"],
                },
            )
        elif preset_name == "long_approved":
            self.history.insert(
                0,
                {
                    "id": f"GRD-{2050 + len(self.history)}",
                    "timestamp": _utc_time(),
                    "symbol": snapshot["symbol"],
                    "direction": "LONG",
                    "entry": snapshot["entry"],
                    "sl": snapshot["sl"],
                    "tp": snapshot["tp"],
                    "rr_ratio": snapshot["rr_ratio"],
                    "status": "APPROVED",
                    "reasons": ["passed_all_guardrails"],
                },
            )
        self.history = self.history[:25]
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "market_snapshot": self.stream["market_snapshot"],
            "agent_debate_stream": self.stream["agent_debate_stream"],
            "system_status": {**self.status, "kill_switch": self.kill_switch},
        }


def create_app(state: RuntimeState | None = None) -> FastAPI:
    """Create the FastAPI app serving the Vue SPA, live exchange endpoints, and WebSocket stream."""
    runtime = state or RuntimeState()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if os.environ.get("PYTEST_CURRENT_TEST") is None:
            asyncio.create_task(runtime.refresh_from_exchange())
        yield

    app = FastAPI(title="AegisQuant API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if (DIST_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")
    elif FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def index() -> Any:
        dist_index = DIST_DIR / "index.html"
        if dist_index.exists():
            return FileResponse(dist_index)
        raw_index = FRONTEND_DIR / "index.html"
        if raw_index.exists():
            return FileResponse(raw_index)
        return JSONResponse({"service": "AegisQuant API", "status": "ok"})

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        return {**runtime.status, "kill_switch": runtime.kill_switch}

    @app.get("/api/portfolio")
    async def portfolio() -> dict[str, Any]:
        return runtime.portfolio

    @app.get("/api/history")
    async def history() -> dict[str, Any]:
        return {"history": runtime.history}

    @app.get("/api/market/live")
    async def live_market(
        timeframe: str = Query(default="1h"),
        limit: int = Query(default=120, ge=20, le=500),
    ) -> dict[str, Any]:
        if timeframe not in {"15m", "1h", "4h"}:
            raise HTTPException(status_code=400, detail="timeframe must be 15m, 1h, or 4h")

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                klines_resp, ticker_resp = await asyncio.gather(
                    client.get(
                        "https://fapi.binance.com/fapi/v1/klines",
                        params={"symbol": "BTCUSDT", "interval": timeframe, "limit": limit},
                    ),
                    client.get(
                        "https://fapi.binance.com/fapi/v1/ticker/24hr",
                        params={"symbol": "BTCUSDT"},
                    ),
                )
                klines_resp.raise_for_status()
                ticker_resp.raise_for_status()
                raw = klines_resp.json()
                ticker = ticker_resp.json()

                ohlcv = [
                    [int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])]
                    for r in raw
                ]
                candles = [
                    {
                        "time": int(r[0] // 1000),
                        "open": float(r[1]),
                        "high": float(r[2]),
                        "low": float(r[3]),
                        "close": float(r[4]),
                        "volume": float(r[5]),
                    }
                    for r in raw
                ]
                indicators = calculate_indicators(ohlcv)
                last_price = float(ticker.get("lastPrice", candles[-1]["close"]))
                runtime.stream["market_snapshot"]["price"] = round(last_price, 1)
                runtime.portfolio["change_24h_pct"] = round(float(ticker.get("priceChangePercent", 0.0)), 2)
                runtime.portfolio["high_24h"] = float(ticker.get("highPrice", last_price))
                runtime.portfolio["low_24h"] = float(ticker.get("lowPrice", last_price))
                runtime.portfolio["volume_24h"] = float(ticker.get("quoteVolume", 0.0))
                runtime.portfolio["atr"] = round(float(indicators["atr"]), 2)
                runtime.portfolio["rsi"] = round(float(indicators["rsi"]), 2)
                runtime.portfolio["market_source"] = "binance_futures_live"

                return {
                    "symbol": "BTC/USDT:USDT",
                    "timeframe": timeframe,
                    "source": "binance_futures_live",
                    "candles": candles,
                    "ticker": {
                        "last_price": last_price,
                        "change_24h_pct": runtime.portfolio["change_24h_pct"],
                        "high_24h": runtime.portfolio["high_24h"],
                        "low_24h": runtime.portfolio["low_24h"],
                        "volume_24h": runtime.portfolio["volume_24h"],
                    },
                    "indicators": {k: float(v) for k, v in indicators.items()},
                    "vnd_rate": runtime.portfolio["vnd_rate"],
                }
            except Exception as exc:
                LOGGER.warning("Live market fetch fallback triggered", extra={"error": str(exc)})
                return {
                    "symbol": "BTC/USDT:USDT",
                    "timeframe": timeframe,
                    "source": "fallback_cached",
                    "candles": [],
                    "ticker": {
                        "last_price": runtime.stream["market_snapshot"]["price"],
                        "change_24h_pct": runtime.portfolio["change_24h_pct"],
                        "high_24h": runtime.portfolio["high_24h"],
                        "low_24h": runtime.portfolio["low_24h"],
                        "volume_24h": runtime.portfolio["volume_24h"],
                    },
                    "indicators": {
                        "close": runtime.stream["market_snapshot"]["price"],
                        "atr": runtime.portfolio["atr"],
                        "rsi": runtime.portfolio["rsi"],
                    },
                    "vnd_rate": runtime.portfolio["vnd_rate"],
                }

    @app.post("/api/sync-live")
    async def sync_live() -> dict[str, Any]:
        result = await runtime.refresh_from_exchange()
        return {
            **result,
            "snapshot": runtime.snapshot(),
            "portfolio": runtime.portfolio,
            "history": runtime.history,
        }

    @app.post("/api/kill-switch")
    async def set_kill_switch(
        enabled: bool | None = Query(default=None),
        payload: KillSwitchPayload | None = Body(default=None),
    ) -> dict[str, bool]:
        target_enabled = payload.enabled if payload is not None else (True if enabled is None else enabled)
        runtime.kill_switch = target_enabled
        runtime.status["kill_switch"] = target_enabled
        if target_enabled:
            runtime.status["gatekeeper"] = False
            runtime.portfolio["open_positions"] = 0
            snapshot = runtime.stream["market_snapshot"]
            runtime.history.insert(
                0,
                {
                    "id": f"KILL-{2050 + len(runtime.history)}",
                    "timestamp": _utc_time(),
                    "symbol": snapshot.get("symbol", "BTC/USDT:USDT"),
                    "direction": runtime.portfolio.get("direction", "FLAT"),
                    "entry": snapshot.get("entry"),
                    "sl": snapshot.get("sl"),
                    "tp": snapshot.get("tp"),
                    "rr_ratio": snapshot.get("rr_ratio"),
                    "status": "REJECTED",
                    "reasons": ["emergency_kill_switch_activated"],
                },
            )
            runtime.history = runtime.history[:25]
            if runtime.notifier is not None:
                await runtime.notifier.send_kill_switch("API kill-switch activated")
        return {"kill_switch": target_enabled}

    @app.post("/api/mode")
    async def set_mode(
        mode: str | None = Query(default=None),
        payload: ModePayload | None = Body(default=None),
    ) -> dict[str, str]:
        requested = payload.mode if payload is not None else mode
        if requested is None:
            next_mode = "TESTNET" if runtime.portfolio.get("mode") == "PAPER" else "PAPER"
        else:
            next_mode = requested.upper()
            if next_mode not in {"PAPER", "TESTNET"}:
                raise HTTPException(status_code=400, detail="Mode must be PAPER or TESTNET")
        runtime.portfolio["mode"] = next_mode
        return {"mode": next_mode}

    @app.post("/api/simulate/{preset}")
    async def simulate_preset(preset: str) -> dict[str, Any]:
        try:
            snapshot = runtime.apply_preset(preset)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown preset: {preset}") from exc
        return {
            "preset": preset,
            "snapshot": snapshot,
            "portfolio": runtime.portfolio,
            "history": runtime.history,
        }

    @app.websocket("/ws/stream")
    async def stream(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(runtime.snapshot())
                await asyncio.sleep(1)
        except (WebSocketDisconnect, RuntimeError):
            return

    return app


app = create_app()
