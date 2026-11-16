"""Strict structured outputs for Gemini agents."""

from enum import StrEnum

from pydantic import BaseModel, Field


class TradeDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class MacroSentimentOutput(BaseModel):
    high_impact_event_within_4h: bool
    event_name: str | None = Field(default=None, max_length=50)
    market_bias: TradeDirection
    summary_bullets: list[str] = Field(default_factory=list, max_length=3)


class AnalystProposalOutput(BaseModel):
    decision: TradeDirection
    confidence_score: int = Field(ge=0, le=100)
    entry_price: float
    stop_loss: float
    take_profit: float
    rationale: str = Field(max_length=200)


class RiskCritiqueOutput(BaseModel):
    approve_trade: bool
    adjusted_confidence: int = Field(ge=0, le=100)
    critical_flaws: list[str] = Field(default_factory=list, max_length=3)
