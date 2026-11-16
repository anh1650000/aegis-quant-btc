import pytest

from src.agents.debate_graph import DebateGraph
from src.agents.schemas import AnalystProposalOutput, RiskCritiqueOutput, TradeDirection


class UnusedClient:
    pass


@pytest.mark.asyncio
async def test_neutral_proposal_early_exits_without_critic() -> None:
    graph = DebateGraph(UnusedClient())
    calls = []

    async def fake_generate(contents, prompt, schema):
        calls.append(schema)
        if schema is AnalystProposalOutput:
            return AnalystProposalOutput(
                decision=TradeDirection.NEUTRAL,
                confidence_score=40,
                entry_price=100,
                stop_loss=98,
                take_profit=104,
                rationale="Insufficient confluence",
            )
        return RiskCritiqueOutput(
            approve_trade=False, adjusted_confidence=0, critical_flaws=["not called"]
        )

    graph._generate = fake_generate
    result = await graph.run({"indicators": {"rsi": 50}})
    assert result["status"] == "SKIPPED"
    assert calls == [AnalystProposalOutput]
    assert result["proposal"]["decision"] == "NEUTRAL"


@pytest.mark.asyncio
async def test_debate_outputs_json_serializable_structures() -> None:
    graph = DebateGraph(UnusedClient())

    async def fake_generate(contents, prompt, schema):
        if schema is AnalystProposalOutput:
            return AnalystProposalOutput(
                decision=TradeDirection.LONG,
                confidence_score=80,
                entry_price=100,
                stop_loss=98,
                take_profit=104,
                rationale="Grounded",
            )
        return RiskCritiqueOutput(
            approve_trade=True, adjusted_confidence=75, critical_flaws=[]
        )

    graph._generate = fake_generate
    result = await graph.run({"indicators": {"rsi": 25}})
    assert result["status"] == "APPROVED"
    assert result["critique"]["approve_trade"] is True
