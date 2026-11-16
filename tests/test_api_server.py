from fastapi.testclient import TestClient

from src.api.server import RuntimeState, create_app


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send_kill_switch(self, reason: str) -> None:
        self.messages.append(reason)


def test_vue_spa_served_at_root() -> None:
    client = TestClient(create_app())
    resp = client.get("/")
    assert resp.status_code == 200
    assert "AEGISQUANT // BTC-PERP" in resp.text
    assert '<div id="app"></div>' in resp.text
    assert "/assets/" in resp.text


def test_rest_status_portfolio_and_history_schemas() -> None:
    client = TestClient(create_app())

    status = client.get("/api/status").json()
    assert set(status.keys()) >= {"gatekeeper", "remaining_daily_quota_estimate", "kill_switch"}
    assert status["kill_switch"] is False

    portfolio = client.get("/api/portfolio").json()
    assert portfolio["mode"] == "PAPER"
    assert portfolio["margin_mode"] == "ISOLATED"
    assert portfolio["max_risk_pct"] == 1.5
    assert portfolio["leverage"] <= 10
    assert portfolio["vnd_rate"] > 10000

    history_payload = client.get("/api/history").json()
    assert "history" in history_payload
    statuses = {entry["status"] for entry in history_payload["history"]}
    assert "APPROVED" in statuses
    assert "REJECTED" in statuses
    for entry in history_payload["history"]:
        if entry["entry"] is not None:
            assert 50000 <= entry["entry"] <= 80000


def test_kill_switch_activation_and_reset() -> None:
    notifier = FakeNotifier()
    state = RuntimeState(notifier=notifier)
    client = TestClient(create_app(state))

    activated = client.post("/api/kill-switch", params={"enabled": True})
    assert activated.status_code == 200
    assert activated.json() == {"kill_switch": True}
    assert state.kill_switch is True
    assert state.status["gatekeeper"] is False
    assert state.portfolio["open_positions"] == 0
    assert notifier.messages == ["API kill-switch activated"]

    disarmed = client.post("/api/kill-switch", json={"enabled": False})
    assert disarmed.status_code == 200
    assert disarmed.json() == {"kill_switch": False}
    assert state.kill_switch is False


def test_mode_toggle_and_preset_simulation() -> None:
    client = TestClient(create_app())

    mode_res = client.post("/api/mode", params={"mode": "TESTNET"})
    assert mode_res.status_code == 200
    assert mode_res.json() == {"mode": "TESTNET"}

    sim_res = client.post("/api/simulate/short_rejected")
    assert sim_res.status_code == 200
    payload = sim_res.json()
    assert payload["preset"] == "short_rejected"
    snap = payload["snapshot"]["market_snapshot"]
    assert 60000 <= snap["price"] <= 70000
    assert snap["rr_ratio"] < 1.8
    assert payload["snapshot"]["agent_debate_stream"][2]["approve_trade"] is False


def test_websocket_stream_emits_contract_payload() -> None:
    client = TestClient(create_app())
    with client.websocket_connect("/ws/stream") as ws:
        msg = ws.receive_json()

    assert set(msg.keys()) == {"market_snapshot", "agent_debate_stream", "system_status"}
    assert set(msg["market_snapshot"].keys()) == {
        "symbol",
        "price",
        "entry",
        "sl",
        "tp",
        "liquidation_price",
        "rr_ratio",
    }
    assert 60000 <= msg["market_snapshot"]["price"] <= 70000
    assert len(msg["agent_debate_stream"]) == 3
    assert [a["agent"] for a in msg["agent_debate_stream"]] == [
        "hydrogen",
        "argon_analyst",
        "argon_critic",
    ]
    assert set(msg["system_status"].keys()) == {
        "gatekeeper",
        "remaining_daily_quota_estimate",
        "kill_switch",
    }
