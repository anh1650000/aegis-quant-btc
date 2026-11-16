from src.ml.gatekeeper import evaluate_gate


def test_gate_requires_probability_and_confluence() -> None:
    indicators = {"rsi": 25, "close": 100, "bb_lower": 95, "bb_upper": 105}
    assert evaluate_gate(0.66, indicators).allowed
    assert not evaluate_gate(0.65, indicators).allowed
    assert not evaluate_gate(0.66, {"rsi": 50}).allowed
