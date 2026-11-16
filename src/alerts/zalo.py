"""Async Zalo Official Account alerts."""

from __future__ import annotations

from typing import Any

import httpx

from src.config.settings import ZaloSettings


class ZaloAlertError(RuntimeError):
    """Raised when the Zalo API rejects an alert."""


class ZaloAlertClient:
    """Send text alerts through the official Zalo OA customer-message API."""

    def __init__(
        self,
        settings: ZaloSettings,
        http_client: Any | None = None,
    ) -> None:
        self.settings = settings
        self._http_client = http_client

    async def send_text(self, text: str) -> dict[str, Any]:
        """Send one text message and raise on transport or API errors."""
        message = text.strip()
        if not message:
            raise ValueError("Zalo alert text cannot be empty.")
        if len(message) > 2000:
            raise ValueError("Zalo alert text cannot exceed 2000 characters.")

        payload = {
            "recipient": {"user_id": self.settings.zalo_recipient_id},
            "message": {"text": message},
        }
        headers = {
            "access_token": self.settings.zalo_oa_access_token,
            "content-type": "application/json",
        }
        client = self._http_client or httpx.AsyncClient(
            timeout=self.settings.zalo_timeout_seconds
        )
        owns_client = self._http_client is None
        try:
            response = await client.post(
                self.settings.zalo_api_url, headers=headers, json=payload
            )
            response.raise_for_status()
            result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ZaloAlertError("Zalo alert request failed.") from exc
        finally:
            if owns_client:
                await client.aclose()

        if result.get("error", 0) not in (0, "0", None):
            raise ZaloAlertError(
                f"Zalo alert rejected with error code {result.get('error')}."
            )
        return result

    async def trade_opened(self, symbol: str, direction: str, entry: float, stop_loss: float) -> dict[str, Any]:
        return await self.send_text(
            f"[AegisQuant] OPEN {direction} {symbol}\nEntry: {entry}\nSL: {stop_loss}"
        )

    async def trade_closed(self, symbol: str, result: str, pnl: float) -> dict[str, Any]:
        return await self.send_text(
            f"[AegisQuant] CLOSED {symbol}\nResult: {result}\nPnL: {pnl}"
        )

    async def trade_rejected(self, symbol: str, reasons: tuple[str, ...]) -> dict[str, Any]:
        reason_text = ", ".join(reasons) or "unspecified"
        return await self.send_text(f"[AegisQuant] REJECTED {symbol}\nReasons: {reason_text}")
