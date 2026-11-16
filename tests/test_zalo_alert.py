import pytest

from src.alerts.zalo import ZaloAlertClient
from src.config.settings import ZaloSettings


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"error": 0, "message": "Success"}


class FakeHttpClient:
    def __init__(self):
        self.calls = []

    async def post(self, url, headers, json):
        self.calls.append((url, headers, json))
        return FakeResponse()


@pytest.mark.asyncio
async def test_zalo_alert_uses_oa_payload_without_exposing_token() -> None:
    http = FakeHttpClient()
    client = ZaloAlertClient(
        ZaloSettings(
            zalo_oa_access_token="secret-token",
            zalo_recipient_id="user-123",
        ),
        http_client=http,
    )
    result = await client.trade_rejected("BTC/USDT", ("high_impact_macro_event",))
    assert result["error"] == 0
    _, headers, payload = http.calls[0]
    assert headers["access_token"] == "secret-token"
    assert payload["recipient"]["user_id"] == "user-123"
    assert "secret-token" not in payload["message"]["text"]


@pytest.mark.asyncio
async def test_zalo_alert_rejects_empty_text() -> None:
    client = ZaloAlertClient(
        ZaloSettings(
            zalo_oa_access_token="secret-token",
            zalo_recipient_id="user-123",
        ),
        http_client=FakeHttpClient(),
    )
    with pytest.raises(ValueError):
        await client.send_text(" ")
