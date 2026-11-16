import pytest

from src.risk.guardrails import (
    Direction,
    calculate_liquidation_price,
    calculate_position_size,
    validate_trade_signal,
)


def test_position_size_caps_loss_at_one_point_five_percent() -> None:
    position = calculate_position_size(1000, 100, 98)
    assert position.quantity_btc == pytest.approx(7.5)
    assert position.margin_usdt == pytest.approx(75)
    assert position.risk_amount_usdt == pytest.approx(15)


def test_low_risk_reward_is_rejected() -> None:
    result = validate_trade_signal(Direction.LONG, 1000, 100, 98, 101, 2)
    assert not result.approved
    assert "risk_reward_below_1.8" in result.reasons


def test_stop_at_liquidation_is_rejected() -> None:
    liquidation = calculate_liquidation_price(100, Direction.LONG, 10)
    result = validate_trade_signal(Direction.LONG, 1000, 100, liquidation, 120, 1)
    assert not result.approved
    assert "stop_loss_at_or_beyond_liquidation" in result.reasons


def test_valid_signal_is_approved() -> None:
    result = validate_trade_signal(Direction.LONG, 1000, 100, 98, 104, 2)
    assert result.approved
    assert result.position is not None
    assert result.risk_reward == pytest.approx(2)


def test_macro_circuit_breaker_rejects_signal() -> None:
    result = validate_trade_signal(
        Direction.SHORT, 1000, 100, 102, 96, 2, high_impact_event=True
    )
    assert not result.approved
    assert "high_impact_macro_event" in result.reasons
