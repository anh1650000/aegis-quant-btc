"""LangGraph-powered, structured two-turn Argon debate."""

from __future__ import annotations

import asyncio
import json
from typing import Any, TypedDict

from src.agents.prompts import ANALYST_SYSTEM_PROMPT, CRITIC_SYSTEM_PROMPT
from src.agents.schemas import AnalystProposalOutput, RiskCritiqueOutput, TradeDirection


class DebateState(TypedDict, total=False):
    market_context: dict[str, Any]
    proposal: dict[str, Any]
    critique: dict[str, Any]
    status: str


class DebateGraph:
    """Run analyst then critic nodes, stopping before critic for neutral proposals."""

    def __init__(self, client: Any) -> None:
        self.client = client
        try:
            from langgraph.graph import END, StateGraph
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install langgraph to use DebateGraph.") from exc
        graph = StateGraph(DebateState)
        graph.add_node("analyst", self._analyst)
        graph.add_node("critic", self._critic)
        graph.set_entry_point("analyst")
        graph.add_conditional_edges(
            "analyst",
            lambda state: "critic"
            if state["proposal"]["decision"] != TradeDirection.NEUTRAL.value
            and state["proposal"]["confidence_score"] >= 70
            else END,
        )
        graph.add_edge("critic", END)
        self._compiled = graph.compile()

    @staticmethod
    def _minified(payload: Any) -> str:
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    async def _generate(self, contents: str, prompt: str, schema: type[Any]) -> Any:
        try:
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install google-genai to use DebateGraph.") from exc
        config = types.GenerateContentConfig(
            system_instruction=prompt,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1 if schema is AnalystProposalOutput else 0.2,
            max_output_tokens=400,
        )
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model="gemini-4-argon",
            contents=contents,
            config=config,
        )
        return schema.model_validate_json(response.text)

    async def _analyst(self, state: DebateState) -> dict[str, Any]:
        payload = self._minified(state["market_context"])
        proposal = await self._generate(f"Market JSON:{payload}", ANALYST_SYSTEM_PROMPT, AnalystProposalOutput)
        return {"proposal": proposal.model_dump(mode="json")}

    async def _critic(self, state: DebateState) -> dict[str, Any]:
        payload = self._minified({"market": state["market_context"], "proposal": state["proposal"]})
        critique = await self._generate(f"Review JSON:{payload}", CRITIC_SYSTEM_PROMPT, RiskCritiqueOutput)
        return {
            "critique": critique.model_dump(mode="json"),
            "status": "APPROVED" if critique.approve_trade else "REJECTED",
        }

    async def run(self, market_context: dict[str, Any]) -> DebateState:
        """Execute the graph with a JSON-serializable market context."""
        result = await self._compiled.ainvoke({"market_context": market_context})
        if "status" not in result:
            result["status"] = "SKIPPED"
        return result
