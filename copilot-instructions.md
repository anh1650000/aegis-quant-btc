# GitHub Copilot Custom Instructions — BTC/USDT Perpetual Futures AI Agent

## 1. Project Context & Tech Stack
- **Domain:** Quantitative Crypto Trading System (BTC/USDT Perpetual Futures).
- **Architecture:** 4-Layer Hybrid Pipeline:
  1. `Deterministic Data & Indicators` (`ccxt` async + `pandas-ta`).
  2. `Predictive ML Engine` (`LightGBM` probability filter).
  3. `Multi-Agent Debate` (`google-genai` SDK using `gemini-4-hydrogen` & `gemini-4-argon`).
  4. `Hard-coded Risk Guardrails & FastAPI/WebSocket Server` (serving a 2026+ Bento Grid Dark Glassmorphism UI).

## 2. Strict Anti-Hallucination Rules (ZERO-MATH FOR LLM)
- **NEVER** delegate mathematical calculations (Position Sizing, Stop-Loss, Take-Profit, Risk-to-Reward ratio, Liquidation Price, RSI, ATR, EMA) to an LLM. All math MUST be executed in deterministic Python functions (`numpy` / `pandas`).
- **Grounded Context Only:** LLMs only receive pre-calculated, verified indicators via minified JSON. System prompts MUST forbid inventing external prices or numbers.
- **Structured Outputs:** Every `google-genai` call MUST enforce `response_mime_type="application/json"` with strict `Pydantic` schemas (`response_schema`).

## 3. Google AI Pro Quota & Token Optimization
- **Deterministic Gatekeeper:** Never trigger LLM calls on every candle close. Only invoke Gemini agents when technical confluence AND ML probability (`> 0.65`) pass hard-coded thresholds.
- **Model Routing:**
  - Use `gemini-4-hydrogen` ONLY for background macro/news sentiment caching (max 1 call every 2 hours, saved to local JSON cache).
  - Use `gemini-4-argon` for Dual-Role analysis (Turn 1: Lead Technical Analyst, Turn 2: Devil's Advocate Risk Critic).
- **Token Compression:**
  - Always serialize prompt payloads using `json.dumps(payload, separators=(',', ':'))`.
  - Enforce `max_output_tokens <= 450` on all Gemini API calls.

## 4. Hard-Coded Risk Guardrails (Non-Negotiable)
- **Margin Mode:** Always enforce `ISOLATED` margin. Never use Cross margin.
- **Max Risk Per Trade:** Strictly cap loss at `1.5%` of total futures equity per trade.
- **Minimum R:R Ratio:** Automatically reject any trade setup where `Risk:Reward < 1.8`.
- **Macro Circuit Breaker:** If cached macro sentiment flags `HIGH_IMPACT_EVENT == True` (e.g., CPI, FOMC within 2 hours), block all new order executions.

## 5. Coding Standards & Backend-to-UI Contract
- **Python Style:** Python 3.11+, strict type hints (`typing`, `pydantic`), `asyncio` for all exchange and API I/O.
- **Logging:** Never use `print()`. Use structured `logging` (JSON format) to trace every LLM input/output for hallucination auditing.
- **Security:** Load all keys (`GEMINI_API_KEY`, `BINANCE_API_KEY`, `BINANCE_SECRET`) via `pydantic-settings` / `.env`. Never hardcode secrets.
- **UI Data Stream (For Antigravity 2026+ Dashboard):** Expose clean, typed WebSocket payloads (`/ws/stream`) containing:
  - `market_snapshot` (price, entry, sl, tp, liquidation_price, rr_ratio)
  - `agent_debate_stream` (structured logs from Hydrogen, Lead Analyst, and Devil's Advocate)
  - `system_status` (gatekeeper state, remaining daily quota estimate, kill-switch status).
