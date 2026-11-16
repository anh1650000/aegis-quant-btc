"""AegisQuant paper-mode orchestration pipeline."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from src.agents.debate_graph import DebateGraph
from src.agents.macro_sentinel import MacroSentinel
from src.data.fetcher import MarketDataFetcher
from src.data.indicators import calculate_indicators
from src.execution.paper import PaperExecution
from src.ml.gatekeeper import evaluate_gate
from src.ml.predictor import ProbabilityPredictor
from src.risk.guardrails import Direction, validate_trade_signal
from src.notifications.zalo_oa import ZaloOAClient
from src.utils.audit_logger import AuditLogger

LOGGER = logging.getLogger(__name__)


async def run_once(
    fetcher: MarketDataFetcher,
    predictor: ProbabilityPredictor,
    macro: MacroSentinel,
    debate: DebateGraph,
    paper: PaperExecution,
    zalo: ZaloOAClient | None = None,
    audit: AuditLogger | None = None,
) -> dict[str, Any]:
    """Run one complete cycle; no real order is ever submitted."""
    market = await fetcher.fetch()
    candles = market.candles["1h"]
    indicators = calculate_indicators(candles)
    probability = predictor.predict_from_ohlcv(candles)
    gate = evaluate_gate(probability, indicators)
    if not gate.allowed:
        result = {"status": "EARLY_EXIT", "gate": asdict(gate)}
        if audit:
            audit.log_session(
                {"indicators": indicators, "ml_probability": probability},
                None,
                None,
                None,
                result,
                0,
                0,
            )
        return result

    macro_cache = await macro.get_or_refresh()
    context = {
        "market": market.to_minified_json(),
        "indicators": indicators,
        "ml_probability": probability,
        "macro": macro_cache["sentiment"],
    }
    debate_result = await debate.run(context)
    if debate_result["status"] != "APPROVED":
        result = {"status": debate_result["status"], "debate": debate_result}
        if audit:
            audit.log_session(context, macro_cache["sentiment"], debate_result.get("proposal"), debate_result.get("critique"), result, debate_result.get("tokens_used", 0), 0)
        return result

    proposal = debate_result["proposal"]
    validation = validate_trade_signal(
        Direction(proposal["decision"]),
        balance_usdt=1000,
        entry_price=proposal["entry_price"],
        stop_loss=proposal["stop_loss"],
        take_profit=proposal["take_profit"],
        atr=indicators.get("atr", abs(proposal["entry_price"] - proposal["stop_loss"])),
        high_impact_event=macro_cache["sentiment"]["high_impact_event_within_4h"],
    )
    if not validation.approved:
        result = {"status": "REJECTED", "reasons": validation.reasons}
        if audit:
            audit.log_session(context, macro_cache["sentiment"], proposal, debate_result.get("critique"), result, debate_result.get("tokens_used", 0), 0)
        return result
    order = paper.submit({"proposal": proposal, "validation": asdict(validation)})
    if zalo is not None:
        await zalo.send_trade_approved(
            symbol=market.symbol,
            direction=proposal["decision"],
            entry=proposal["entry_price"],
            stop_loss=proposal["stop_loss"],
            take_profit=proposal["take_profit"],
            risk_reward=validation.risk_reward,
            probability=probability,
            critique="; ".join(debate_result.get("critique", {}).get("critical_flaws", [])) or "No critical flaw",
        )
    LOGGER.info("Paper order simulated", extra={"order": order})
    result = {"status": "SIMULATED", "order": order}
    if audit:
        audit.log_session(context, macro_cache["sentiment"], proposal, debate_result.get("critique"), asdict(validation), debate_result.get("tokens_used", 0), 0)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
