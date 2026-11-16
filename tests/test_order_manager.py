import pytest

from src.execution.order_manager import OrderManager, OrderRequest


class FakeExchange:
    def __init__(self):
        self.calls = []

    async def set_margin_mode(self, margin_mode, symbol, params=None):
        self.calls.append(("margin", margin_mode, symbol))

    async def set_leverage(self, leverage, symbol, params=None):
        self.calls.append(("leverage", leverage, symbol))

    async def create_order(self, symbol, order_type, side, amount, price=None, params=None):
        self.calls.append(("order", symbol, order_type, side, amount, price, params))
        return {"id": f"order-{len(self.calls)}", "type": order_type}

    async def cancel_order(self, order_id, symbol, params=None):
        self.calls.append(("cancel", order_id, symbol))

    async def close(self):
        return None


def request() -> OrderRequest:
    return OrderRequest("BTC/USDT:USDT", "buy", 0.01, None, 95, 110)


@pytest.mark.asyncio
async def test_dry_run_never_calls_exchange() -> None:
    exchange = FakeExchange()
    result = await OrderManager("DRY_RUN", exchange).submit_atomic(request())
    assert result["status"] == "SIMULATED"
    assert exchange.calls == []


@pytest.mark.asyncio
async def test_testnet_sets_isolated_leverage_and_protective_orders() -> None:
    exchange = FakeExchange()
    result = await OrderManager("TESTNET", exchange).submit_atomic(request())
    assert result["status"] == "SUBMITTED"
    assert exchange.calls[0] == ("margin", "isolated", "BTC/USDT:USDT")
    assert exchange.calls[1] == ("leverage", 10, "BTC/USDT:USDT")
    assert exchange.calls[2][2] == "MARKET"
    assert exchange.calls[3][2] == "STOP_MARKET"
    assert exchange.calls[4][2] == "TAKE_PROFIT_MARKET"
    assert exchange.calls[3][6]["reduceOnly"] is True
