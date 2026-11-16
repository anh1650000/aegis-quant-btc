"""Zalo OA v3 notification client with refresh-token rotation."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

import httpx


class ZaloOAError(RuntimeError):
    """Raised when Zalo OAuth or OA message delivery fails."""


class ZaloOAClient:
    """Refresh and send Zalo OA messages without exposing credentials."""

    def __init__(
        self,
        app_id: str,
        secret_key: str,
        refresh_token: str,
        admin_user_id: str,
        token_path: str | Path = "data/zalo_tokens.json",
        http_client: Any | None = None,
        token_url: str = "https://oauth.zaloapp.com/v4/oa/access_token",
        message_url: str = "https://openapi.zalo.me/v3.0/oa/message/cs",
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.app_id = app_id
        self.secret_key = secret_key
        self.refresh_token = refresh_token
        self.admin_user_id = admin_user_id
        self.token_path = Path(token_path)
        self.http_client = http_client
        self.token_url = token_url
        self.message_url = message_url
        self.clock = clock

    @classmethod
    def from_env(cls, **overrides: Any) -> "ZaloOAClient":
        """Create a client from environment variables without logging secrets."""
        required = {
            "app_id": os.getenv("ZALO_APP_ID"),
            "secret_key": os.getenv("ZALO_SECRET_KEY"),
            "refresh_token": os.getenv("ZALO_REFRESH_TOKEN"),
            "admin_user_id": os.getenv("ZALO_ADMIN_USER_ID"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing Zalo configuration: {', '.join(missing)}")
        return cls(
            **required,
            token_path=os.getenv("ZALO_TOKEN_PATH", "data/zalo_tokens.json"),
            **overrides,
        )

    def _load_token(self) -> dict[str, Any] | None:
        if not self.token_path.exists():
            return None
        try:
            return json.loads(self.token_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return None

    def _save_token(self, payload: dict[str, Any]) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.token_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        temporary.replace(self.token_path)

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        client = self.http_client or httpx.AsyncClient(timeout=10)
        owns_client = self.http_client is None
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ZaloOAError("Zalo request failed.") from exc
        finally:
            if owns_client:
                await client.aclose()
        if not isinstance(payload, dict):
            raise ZaloOAError("Zalo returned a non-object response.")
        return payload

    async def _access_token(self) -> str:
        cached = self._load_token()
        if cached and float(cached.get("expires_at", 0)) > self.clock() + 60:
            return str(cached["access_token"])
        payload = await self._request(
            "POST",
            self.token_url,
            headers={"secret_key": self.secret_key, "content-type": "application/x-www-form-urlencoded"},
            data={
                "app_id": self.app_id,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if not payload.get("access_token"):
            raise ZaloOAError("Zalo refresh response did not contain access_token.")
        new_refresh = str(payload.get("refresh_token", self.refresh_token))
        self.refresh_token = new_refresh
        self._save_token({
            "access_token": payload["access_token"],
            "refresh_token": new_refresh,
            "expires_at": self.clock() + int(payload.get("expires_in", 86400)),
        })
        return str(payload["access_token"])

    async def send_text(self, text: str) -> dict[str, Any]:
        if not text.strip():
            raise ValueError("Zalo message cannot be empty.")
        token = await self._access_token()
        payload = await self._request(
            "POST",
            self.message_url,
            headers={"access_token": token, "content-type": "application/json"},
            json={"recipient": {"user_id": self.admin_user_id}, "message": {"text": text[:2000]}},
        )
        if payload.get("error", 0) not in (0, "0", None):
            raise ZaloOAError(f"Zalo rejected message: {payload.get('error')}.")
        return payload

    async def send_trade_approved(
        self,
        symbol: str,
        direction: str,
        entry: float,
        stop_loss: float,
        take_profit: float,
        risk_reward: float,
        probability: float,
        critique: str,
    ) -> dict[str, Any]:
        return await self.send_text(
            f"[AegisQuant] TRADE APPROVED\n{symbol} {direction}\n"
            f"Entry: {entry}\nSL: {stop_loss}\nTP: {take_profit}\n"
            f"R:R: {risk_reward:.2f}\nML probability: {probability:.2%}\n"
            f"Devil's Advocate: {critique}"
        )

    async def send_kill_switch(self, reason: str) -> dict[str, Any]:
        return await self.send_text(f"[AegisQuant] KILL SWITCH ACTIVATED\nReason: {reason}")
