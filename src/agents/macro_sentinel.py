"""Quota-aware Gemini Hydrogen macro sentiment cache."""

from __future__ import annotations

import asyncio
import json
import os
import logging
import time
from pathlib import Path
from typing import Any, Callable

from src.agents.prompts import MACRO_SYSTEM_PROMPT
from src.agents.schemas import MacroSentimentOutput

LOGGER = logging.getLogger(__name__)


class MacroSentinel:
    """Refresh a local sentiment cache no more than once per two hours."""

    def __init__(
        self,
        cache_path: str | Path | None = None,
        client: Any | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.cache_path = Path(cache_path or os.getenv("NEWS_CACHE_PATH", "data/news_cache.json"))
        self.client = client
        self.clock = clock

    def _read_cache(self) -> dict[str, Any] | None:
        if not self.cache_path.exists():
            return None
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            MacroSentimentOutput.model_validate(payload["sentiment"])
            return payload
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            LOGGER.warning("Ignoring invalid macro cache", extra={"path": str(self.cache_path)})
            return None

    async def get_or_refresh(self) -> dict[str, Any]:
        """Return fresh cache or call Hydrogen when the two-hour TTL expires."""
        cached = self._read_cache()
        if cached and self.clock() - float(cached["fetched_at"]) < 7200:
            return cached
        if self.client is None:
            if cached:
                return cached
            raise RuntimeError("Gemini client is required when no usable macro cache exists.")

        try:
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install google-genai to refresh macro sentiment.") from exc

        config = types.GenerateContentConfig(
            system_instruction=MACRO_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=MacroSentimentOutput,
            max_output_tokens=300,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model="gemini-4-hydrogen",
            contents="Search current BTC and US macro news and return grounded JSON.",
            config=config,
        )
        sentiment = MacroSentimentOutput.model_validate_json(response.text)
        payload = {"fetched_at": self.clock(), "sentiment": sentiment.model_dump(mode="json")}
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        temporary.replace(self.cache_path)
        LOGGER.info("Updated macro sentiment cache", extra={"path": str(self.cache_path)})
        return payload
