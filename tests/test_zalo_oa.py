import pytest

from src.notifications.zalo_oa import ZaloOAClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self):
        self.calls = []

    async def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if "access_token" in url:
            return FakeResponse({"access_token": "new-token", "refresh_token": "rotated", "expires_in": 3600})
        return FakeResponse({"error": 0, "message": "Success"})


@pytest.mark.asyncio
async def test_refreshes_token_persists_rotation_and_sends_admin_message() -> None:
    http = FakeHttpClient()
    token_path = "data/test_zalo_tokens.json"
    client = ZaloOAClient("app", "secret", "refresh", "admin", token_path, http, clock=lambda: 1000)
    try:
        await client.send_trade_approved("BTC/USDT", "LONG", 100, 98, 104, 2, 0.8, "No flaw")
        token_file = open(token_path, encoding="utf-8").read()
        assert '"refresh_token":"rotated"' in token_file
        assert len(http.calls) == 2
        assert http.calls[1][2]["headers"]["access_token"] == "new-token"
        assert "Entry: 100" in http.calls[1][2]["json"]["message"]["text"]
    finally:
        import os
        if os.path.exists(token_path):
            os.remove(token_path)


@pytest.mark.asyncio
async def test_uses_cached_token_without_refresh() -> None:
    token_path = "data/test_zalo_tokens_cached.json"
    with open(token_path, "w", encoding="utf-8") as handle:
        handle.write('{"access_token":"cached","expires_at":5000}')
    http = FakeHttpClient()
    client = ZaloOAClient("app", "secret", "refresh", "admin", token_path, http, clock=lambda: 1000)
    try:
        await client.send_kill_switch("manual test")
        assert len(http.calls) == 1
        assert http.calls[0][2]["headers"]["access_token"] == "cached"
    finally:
        import os
        if os.path.exists(token_path):
            os.remove(token_path)
