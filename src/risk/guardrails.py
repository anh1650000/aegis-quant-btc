"""Hard-coded, LLM-independent futures risk calculations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class PositionSize:
    quantity_btc: float
    margin_usdt: float
    risk_amount_usdt: float


@dataclass(frozen=True, slots=True)
class TradeValidation:
    approved: bool
    risk_reward: float
    liquidation_price: float
    position: PositionSize | None
    reasons: tuple[str, ...]


def _positive(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number.")


def calculate_position_size(
    balance_usdt: float,
    entry_price: float,
    stop_loss: float,
    leverage: float = 10,
    risk_fraction: float = 0.015,
) -> PositionSize:
    """Calculate quantity so stop loss risks at most the configured equity fraction."""
    for name, value in (("balance_usdt", balance_usdt), ("entry_price", entry_price),
                        ("leverage", leverage), ("risk_fraction", risk_fraction)):
        _positive(name, value)
    _positive("stop_loss", stop_loss)
    distance = abs(entry_price - stop_loss)
    if distance == 0 or risk_fraction > 0.015:
        raise ValueError("Stop distance must be non-zero and risk_fraction cannot exceed 1.5%.")
    risk_amount = balance_usdt * risk_fraction
    quantity = risk_amount / distance
    return PositionSize(quantity, quantity * entry_price / leverage, risk_amount)


def calculate_liquidation_price(
    entry_price: float,
    direction: Direction,
    leverage: float,
    maintenance_margin_rate: float = 0.004,
) -> float:
    """Estimate isolated-margin liquidation price using a conservative maintenance rate."""
    _positive("entry_price", entry_price)
    _positive("leverage", leverage)
    if leverage > 10:
        raise ValueError("leverage cannot exceed the hard limit of 10x.")
    if not 0 <= maintenance_margin_rate < 1:
        raise ValueError("maintenance_margin_rate must be in [0, 1).")
    if direction is Direction.LONG:
        return entry_price * (1 - 1 / leverage + maintenance_margin_rate)
    return entry_price * (1 + 1 / leverage - maintenance_margin_rate)


def validate_trade_signal(
    direction: Direction,
    balance_usdt: float,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    atr: float,
    high_impact_event: bool = False,
    leverage: float = 10,
    open_positions: int = 0,
) -> TradeValidation:
    """Apply every deterministic trade gate and return explicit rejection reasons."""
    _positive("atr", atr)
    position = calculate_position_size(balance_usdt, entry_price, stop_loss, leverage)
    liquidation = calculate_liquidation_price(entry_price, direction, leverage)
    risk = abs(entry_price - stop_loss)
    reward = abs(take_profit - entry_price)
    rr = reward / risk if risk else 0.0
    reasons: list[str] = []
    if direction is Direction.LONG and not (stop_loss < entry_price < take_profit):
        reasons.append("invalid_long_price_geometry")
    if direction is Direction.SHORT and not (take_profit < entry_price < stop_loss):
        reasons.append("invalid_short_price_geometry")
    if rr < 1.8:
        reasons.append("risk_reward_below_1.8")
    if not 0.5 * atr <= risk <= 2.5 * atr:
        reasons.append("stop_distance_outside_atr_bounds")
    if direction is Direction.LONG and stop_loss <= liquidation:
        reasons.append("stop_loss_at_or_beyond_liquidation")
    if direction is Direction.SHORT and stop_loss >= liquidation:
        reasons.append("stop_loss_at_or_beyond_liquidation")
    if risk > abs(entry_price - liquidation) / 1.3:
        reasons.append("liquidation_not_30_percent_farther_than_stop")
    if high_impact_event:
        reasons.append("high_impact_macro_event")
    if open_positions >= 1:
        reasons.append("maximum_open_positions_reached")
    return TradeValidation(not reasons, rr, liquidation, position if not reasons else None, tuple(reasons))
