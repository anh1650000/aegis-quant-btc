<template>
  <div class="relative min-h-screen overflow-x-hidden bg-[#09090B] text-zinc-100">
    <!-- Ambient OLED Backdrop -->
    <div class="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden="true">
      <div
        class="absolute -left-32 -top-40 h-[560px] w-[560px] rounded-full blur-[135px] transition-all duration-700"
        :class="ambientOrbClass"
      ></div>
      <div
        class="absolute -bottom-48 -right-32 h-[520px] w-[520px] rounded-full bg-cyan-500/10 blur-[135px]"
      ></div>
      <div class="grid-backdrop absolute inset-0"></div>
    </div>

    <div class="relative z-10 mx-auto flex max-w-[1680px] flex-col gap-4 px-4 py-4 sm:px-6">
      <!-- TOP NAVIGATION BAR -->
      <header
        class="glass-panel flex flex-wrap items-center justify-between gap-3 rounded-2xl px-4 py-3"
      >
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex items-center gap-2.5">
            <span
              class="h-2.5 w-2.5 animate-pulse rounded-full"
              :class="stateAccentDotClass"
            ></span>
            <h1 class="text-sm font-bold tracking-[0.09em] text-zinc-100 sm:text-[15px]">
              AEGISQUANT <span :class="stateAccentTextClass">//</span> BTC-PERP
            </h1>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <span
              class="mono-num rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[11px] text-zinc-300"
            >
              {{ market.symbol }}
            </span>

            <span
              class="mono-num inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[11px] text-zinc-300"
            >
              <span
                class="h-1.5 w-1.5 rounded-full"
                :class="binanceWsConnected || apiWsConnected ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-amber-400'"
              ></span>
              {{ wsStatusLabel }}
            </span>
          </div>
        </div>

        <!-- Zero-Hallucination Guardrails Badge -->
        <div
          class="flex items-center gap-2.5 rounded-full border px-3.5 py-1.5 transition-all"
          :class="
            systemStatus.kill_switch || hasHighImpactEvent
              ? 'border-rose-500/45 bg-rose-500/10 shadow-[0_0_24px_rgba(244,63,94,0.18)]'
              : 'border-emerald-500/30 bg-emerald-500/10 shadow-[0_0_24px_rgba(16,185,129,0.14)]'
          "
        >
          <svg
            class="h-4 w-4 shrink-0"
            :class="systemStatus.kill_switch || hasHighImpactEvent ? 'text-rose-400' : 'text-emerald-400'"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3z" />
            <path d="M9 12l2 2 4-4" />
          </svg>
          <span
            class="text-[11px] font-bold tracking-[0.07em]"
            :class="systemStatus.kill_switch || hasHighImpactEvent ? 'text-rose-300' : 'text-emerald-300'"
          >
            ZERO-HALLUCINATION GUARDRAILS ACTIVE
          </span>
          <span
            class="mono-num hidden border-l border-white/10 pl-2.5 text-[10px] text-zinc-400 xl:inline"
          >
            0% LLM MATH • DETERMINISTIC PYTHON
          </span>
        </div>

        <!-- Controls: Currency Toggle, Scenario Switcher, Countdowns, Paper Mode -->
        <div class="flex flex-wrap items-center gap-2.5">
          <!-- Currency Toggle (USDT <-> VND) -->
          <div
            class="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-2 py-1"
            title="Chuyển đổi đơn vị hiển thị giữa USDT và VND theo tỷ giá thực tế"
          >
            <div class="flex rounded-lg bg-black/40 p-0.5">
              <button
                type="button"
                @click="setCurrency('USDT')"
                class="mono-num rounded-md px-2 py-1 text-[10.5px] font-semibold transition"
                :class="
                  currency === 'USDT'
                    ? 'bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40'
                    : 'text-zinc-400 hover:text-zinc-200'
                "
              >
                USDT ($)
              </button>
              <button
                type="button"
                @click="setCurrency('VND')"
                class="mono-num rounded-md px-2 py-1 text-[10.5px] font-semibold transition"
                :class="
                  currency === 'VND'
                    ? 'bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-500/40'
                    : 'text-zinc-400 hover:text-zinc-200'
                "
              >
                VND (₫)
              </button>
            </div>
            <span class="mono-num hidden text-[10px] text-zinc-400 sm:inline">
              1$ ≈ {{ Math.round(vndRate).toLocaleString('en-US') }}₫
            </span>
          </div>

          <!-- Live Sync & Scenario Switcher -->
          <div class="flex flex-wrap items-center gap-1 rounded-xl border border-white/10 bg-white/[0.03] p-1">
            <button
              type="button"
              @click="syncLiveNow"
              :disabled="syncingLive"
              class="mono-num rounded-lg px-2 py-1 text-[10px] font-semibold text-cyan-300 transition hover:bg-cyan-500/15 disabled:opacity-50"
              title="Đồng bộ giá BTC/USDT Perpetual & tỷ giá VND trực tiếp từ Binance Futures"
            >
              {{ syncingLive ? "SYNCING..." : "↻ LIVE SYNC" }}
            </button>
            <button
              v-for="item in scenarioOptions"
              :key="item.id"
              type="button"
              @click="selectPreset(item.id)"
              class="mono-num rounded-lg px-2 py-1 text-[10px] font-semibold transition"
              :class="
                activePreset === item.id
                  ? 'bg-white/15 text-white ring-1 ring-white/20'
                  : 'text-zinc-400 hover:bg-white/5 hover:text-zinc-200'
              "
            >
              {{ item.label }}
            </button>
          </div>

          <!-- H1 / H4 Countdown Clocks -->
          <div class="flex items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-1">
            <div class="flex flex-col">
              <span class="text-[9px] font-semibold tracking-wider text-zinc-500">H1 CLOSE</span>
              <span class="mono-num text-xs font-semibold text-zinc-100">{{ h1Countdown }}</span>
            </div>
            <div class="h-5 w-px bg-white/10"></div>
            <div class="flex flex-col">
              <span class="text-[9px] font-semibold tracking-wider text-zinc-500">H4 CLOSE</span>
              <span class="mono-num text-xs font-semibold text-zinc-100">{{ h4Countdown }}</span>
            </div>
          </div>

          <!-- Paper Trading Toggle -->
          <button
            type="button"
            @click="toggleTradingMode"
            class="flex items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-1.5 text-left transition hover:border-white/20"
          >
            <span
              class="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition"
              :class="
                isPaperMode
                  ? 'border-emerald-500/60 bg-emerald-500/30'
                  : 'border-amber-500/60 bg-amber-500/30'
              "
            >
              <span
                class="inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform"
                :class="isPaperMode ? 'translate-x-4' : 'translate-x-0.5'"
              ></span>
            </span>
            <span class="flex flex-col">
              <span class="text-[11px] font-bold tracking-wide text-zinc-100">
                PAPER TRADING (DRY-RUN)
              </span>
              <span
                class="mono-num text-[9.5px]"
                :class="isPaperMode ? 'text-emerald-400' : 'text-amber-400'"
              >
                {{ isPaperMode ? "SAFE SANDBOX • NO REAL ORDERS" : "BINANCE TESTNET • LIVE API TEST" }}
              </span>
            </span>
          </button>
        </div>
      </header>

      <!-- ASYMMETRIC 12-COLUMN BENTO GRID -->
      <main class="grid grid-cols-12 gap-4">
        <!-- BENTO BOX 1: LIVE MARKET & POSITION VISUALIZER (7 COLS) -->
        <section
          class="glass-panel col-span-12 flex min-h-[500px] flex-col gap-3.5 rounded-2xl p-5 transition-all duration-300 lg:col-span-7"
          :class="marketCardGlowClass"
        >
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="flex flex-col gap-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="mono-num text-[10px] font-semibold tracking-[0.09em] text-zinc-500">
                  BENTO 01 // BINANCE FUTURES LIVE FEED
                </span>
                <span
                  class="mono-num rounded-md border px-2 py-0.5 text-[10px] font-bold tracking-wider"
                  :class="directionBadgeClass"
                >
                  {{ directionBadgeText }}
                </span>
                <span
                  class="mono-num rounded-md border border-cyan-500/25 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-cyan-300"
                >
                  {{ marketSourceLabel }}
                </span>
              </div>

              <div class="flex flex-wrap items-baseline gap-3">
                <h2 class="text-base font-semibold text-zinc-100">BTC/USDT Perpetual</h2>
                <span class="mono-num text-2xl font-bold tracking-tight text-white">
                  {{ formatMoney(liveMarkPrice, { decimals: 1 }) }}
                </span>
                <span class="mono-num text-xs text-zinc-400">
                  ({{ formatAltMoney(liveMarkPrice, 1) }})
                </span>
                <span
                  class="mono-num rounded-md px-2 py-0.5 text-xs font-semibold"
                  :class="
                    Number(portfolio.change_24h_pct || 0) >= 0
                      ? 'bg-emerald-500/15 text-emerald-300'
                      : 'bg-rose-500/15 text-rose-300'
                  "
                >
                  {{ Number(portfolio.change_24h_pct || 0) >= 0 ? "+" : ""
                  }}{{ Number(portfolio.change_24h_pct || 0).toFixed(2) }}% (24H)
                </span>
              </div>
            </div>

            <div class="flex flex-col items-end gap-2">
              <div class="flex rounded-lg border border-white/10 bg-white/[0.03] p-0.5">
                <button
                  v-for="tf in ['15m', '1h', '4h']"
                  :key="tf"
                  type="button"
                  @click="changeTimeframe(tf)"
                  class="mono-num rounded-md px-2.5 py-1 text-[11px] font-semibold uppercase transition"
                  :class="
                    timeframe === tf
                      ? 'bg-white/15 text-white'
                      : 'text-zinc-400 hover:text-zinc-200'
                  "
                >
                  {{ tf }}
                </button>
              </div>
              <div class="mono-num flex flex-wrap gap-3 text-[10.5px] text-zinc-400">
                <span>H: {{ formatMoney(portfolio.high_24h, { decimals: 1 }) }}</span>
                <span>L: {{ formatMoney(portfolio.low_24h, { decimals: 1 }) }}</span>
                <span>ATR(14): {{ formatMoney(portfolio.atr, { decimals: 1 }) }}</span>
                <span>RSI(14): {{ Number(portfolio.rsi || 0).toFixed(1) }}</span>
              </div>
            </div>
          </div>

          <!-- Lightweight Charts Container -->
          <div
            class="relative flex min-h-[325px] flex-1 flex-col overflow-hidden rounded-xl border border-white/[0.08] bg-[#07080b]"
          >
            <div
              class="mono-num pointer-events-none absolute left-3 top-2.5 z-10 flex flex-wrap gap-3 rounded-lg border border-white/10 bg-zinc-950/80 px-2.5 py-1 text-[10.5px] text-zinc-300 backdrop-blur-md"
            >
              <span class="inline-flex items-center gap-1.5">
                <span class="h-0.5 w-2.5 bg-cyan-400"></span>
                ENTRY <strong class="text-white">{{ formatMoney(market.entry, { decimals: 1 }) }}</strong>
              </span>
              <span class="inline-flex items-center gap-1.5">
                <span class="h-0.5 w-2.5 bg-emerald-400"></span>
                TP <strong class="text-emerald-300">{{ formatMoney(market.tp, { decimals: 1 }) }}</strong>
              </span>
              <span class="inline-flex items-center gap-1.5">
                <span class="h-0.5 w-2.5 bg-rose-400"></span>
                SL <strong class="text-rose-300">{{ formatMoney(market.sl, { decimals: 1 }) }}</strong>
              </span>
              <span class="inline-flex items-center gap-1.5">
                <span class="h-0.5 w-2.5 bg-amber-400"></span>
                LIQ <strong class="text-amber-300">{{ formatMoney(market.liquidation_price, { decimals: 1 }) }}</strong>
              </span>
            </div>
            <div ref="chartContainerRef" class="h-[340px] w-full flex-1"></div>
          </div>

          <!-- Market HUD Strip -->
          <div class="mono-num grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
            <div class="rounded-lg border border-white/[0.08] bg-white/[0.025] px-2.5 py-2">
              <div class="text-[9.5px] tracking-wider text-zinc-500">MARK PRICE</div>
              <div class="mt-0.5 text-xs font-semibold text-zinc-100">
                {{ formatMoney(liveMarkPrice, { decimals: 1 }) }}
              </div>
            </div>
            <div class="rounded-lg border border-white/[0.08] bg-white/[0.025] px-2.5 py-2">
              <div class="text-[9.5px] tracking-wider text-zinc-500">ENTRY PRICE</div>
              <div class="mt-0.5 text-xs font-semibold text-cyan-300">
                {{ formatMoney(market.entry, { decimals: 1 }) }}
              </div>
            </div>
            <div class="rounded-lg border border-white/[0.08] bg-white/[0.025] px-2.5 py-2">
              <div class="text-[9.5px] tracking-wider text-zinc-500">STOP-LOSS</div>
              <div class="mt-0.5 text-xs font-semibold text-rose-400">
                {{ formatMoney(market.sl, { decimals: 1 }) }}
              </div>
            </div>
            <div class="rounded-lg border border-white/[0.08] bg-white/[0.025] px-2.5 py-2">
              <div class="text-[9.5px] tracking-wider text-zinc-500">TAKE-PROFIT</div>
              <div class="mt-0.5 text-xs font-semibold text-emerald-400">
                {{ formatMoney(market.tp, { decimals: 1 }) }}
              </div>
            </div>
            <div class="rounded-lg border border-white/[0.08] bg-white/[0.025] px-2.5 py-2">
              <div class="text-[9.5px] tracking-wider text-zinc-500">EST. LIQUIDATION</div>
              <div class="mt-0.5 text-xs font-semibold text-amber-400">
                {{ formatMoney(market.liquidation_price, { decimals: 1 }) }}
              </div>
            </div>
            <div class="rounded-lg border border-white/[0.08] bg-white/[0.025] px-2.5 py-2">
              <div class="text-[9.5px] tracking-wider text-zinc-500">RISK : REWARD</div>
              <div
                class="mt-0.5 text-xs font-semibold"
                :class="
                  market.rr_ratio && Number(market.rr_ratio) >= 1.8
                    ? 'text-emerald-300'
                    : market.rr_ratio
                    ? 'text-rose-400'
                    : 'text-zinc-400'
                "
              >
                {{ market.rr_ratio ? `1 : ${Number(market.rr_ratio).toFixed(2)}` : "—" }}
              </div>
            </div>
          </div>
        </section>

        <!-- BENTO BOX 2: HARD-CODED RISK GUARDRAILS (5 COLS) -->
        <section
          class="glass-panel col-span-12 flex min-h-[500px] flex-col gap-3.5 rounded-2xl p-5 lg:col-span-5"
        >
          <div class="flex flex-wrap items-start justify-between gap-2">
            <div>
              <span class="mono-num text-[10px] font-semibold tracking-[0.09em] text-zinc-500">
                BENTO 02 // TẦNG 2 &amp; 4 PYTHON CORE
              </span>
              <h2 class="mt-0.5 text-[17px] font-semibold text-zinc-100">
                Hard-Coded Risk Guardrails
              </h2>
            </div>
            <span
              class="mono-num rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-[10px] font-semibold text-cyan-300"
            >
              PYTHON DETERMINISTIC LOCK
            </span>
          </div>

          <div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            <div class="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
              <div class="text-[11px] text-zinc-400">Tổng vốn (Total Equity)</div>
              <div class="mono-num mt-1 text-base font-bold text-white">
                {{ formatMoney(portfolio.balance_usdt) }}
              </div>
              <div class="mono-num mt-0.5 text-[10px] text-zinc-500">
                {{ formatAltMoney(portfolio.balance_usdt) }} • OPEN: {{ portfolio.open_positions }} / 1 MAX
              </div>
            </div>

            <div class="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
              <div class="text-[11px] text-zinc-400">Rủi ro tối đa / lệnh (1.5%)</div>
              <div class="mono-num mt-1 text-base font-bold text-white">
                {{ Number(portfolio.max_risk_pct || 1.5).toFixed(2) }}% ({{ formatMoney(riskAmountUsd) }})
              </div>
              <div class="mono-num mt-0.5 text-[10px] text-zinc-500">
                SIZE: {{ positionStats.qtyBtc.toFixed(4) }} BTC
              </div>
            </div>

            <div class="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
              <div class="text-[11px] text-zinc-400">Đòn bẩy (Isolated Margin)</div>
              <div class="mono-num mt-1 text-base font-bold text-white">
                {{ portfolio.leverage }}x {{ portfolio.margin_mode || "ISOLATED" }}
              </div>
              <div class="mono-num mt-0.5 text-[10px] text-zinc-500">
                MARGIN REQ: {{ formatMoney(positionStats.marginUsd) }}
              </div>
            </div>

            <div class="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
              <div class="text-[11px] text-zinc-400">Giá thanh lý ước tính</div>
              <div class="mono-num mt-1 text-base font-bold text-amber-400">
                {{ formatMoney(market.liquidation_price, { decimals: 1 }) }}
              </div>
              <div class="mono-num mt-0.5 text-[10px] text-zinc-500">
                {{ positionStats.bufferLabel }}
              </div>
            </div>

            <div class="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
              <div class="text-[11px] text-zinc-400">Tỷ lệ Risk : Reward</div>
              <div
                class="mono-num mt-1 text-base font-bold"
                :class="
                  market.rr_ratio && Number(market.rr_ratio) >= 1.8
                    ? 'text-emerald-400'
                    : market.rr_ratio
                    ? 'text-rose-400'
                    : 'text-zinc-300'
                "
              >
                {{ market.rr_ratio ? `${Number(market.rr_ratio).toFixed(2)}R` : "—" }}
              </div>
              <div class="mono-num mt-0.5 text-[10px] text-zinc-500">MIN GATE: &gt;= 1.80R</div>
            </div>

            <div class="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
              <div class="text-[11px] text-zinc-400">Quota Google AI Pro</div>
              <div class="mono-num mt-1 text-base font-bold text-white">
                {{
                  systemStatus.remaining_daily_quota_estimate !== null
                    ? `${systemStatus.remaining_daily_quota_estimate} calls`
                    : "—"
                }}
              </div>
              <div class="mono-num mt-0.5 text-[10px] text-zinc-500">DAILY REMAINING EST.</div>
            </div>
          </div>

          <!-- Gatekeeper Probability Bar -->
          <div class="mt-auto flex flex-col gap-3 rounded-xl border border-white/[0.08] bg-white/[0.025] p-3.5">
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div class="text-[13px] font-semibold text-zinc-100">
                  Gatekeeper Probability (LightGBM)
                </div>
                <div class="mono-num text-[10px] text-zinc-500">
                  Lọc 85% nhiễu thị trường • Ngưỡng kích hoạt ≥ 65.0%
                </div>
              </div>
              <span
                class="mono-num rounded-md border px-2 py-1 text-[10px] font-bold"
                :class="
                  systemStatus.gatekeeper
                    ? 'border-emerald-500/35 bg-emerald-500/15 text-emerald-300'
                    : 'border-white/15 bg-white/5 text-zinc-400'
                "
              >
                {{ systemStatus.gatekeeper ? "OPEN • ARGON INVOKED" : "CLOSED • NOISE FILTERED" }}
              </span>
            </div>

            <div class="flex items-center gap-3">
              <div class="relative h-2.5 flex-1 rounded-full bg-white/10">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="
                    systemStatus.gatekeeper
                      ? 'bg-gradient-to-r from-cyan-400 to-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.5)]'
                      : 'bg-zinc-500'
                  "
                  :style="{ width: `${mlProbabilityPct.toFixed(1)}%` }"
                ></div>
                <div
                  class="absolute -bottom-1 -top-1 w-0.5 bg-amber-400"
                  style="left: 65%"
                  title="Ngưỡng mở cổng 65%"
                >
                  <span class="mono-num absolute -left-3 -top-4 text-[9px] text-amber-400">65%</span>
                </div>
              </div>
              <span class="mono-num w-14 text-right text-xs font-bold text-white">
                {{ mlProbabilityPct.toFixed(1) }}%
              </span>
            </div>

            <div class="mono-num flex flex-wrap gap-1.5 text-[10px]">
              <span
                v-for="chk in guardrailChecks"
                :key="chk.label"
                class="rounded-md border px-2 py-0.5"
                :class="
                  chk.pass
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : 'border-rose-500/35 bg-rose-500/10 text-rose-300'
                "
              >
                {{ chk.pass ? "✓" : "✕" }} {{ chk.label }}
              </span>
            </div>
          </div>
        </section>

        <!-- BENTO BOX 3: MULTI-AGENT DEBATE STREAM (7 COLS) -->
        <section
          class="glass-panel col-span-12 flex min-h-[420px] flex-col gap-3.5 rounded-2xl p-5 lg:col-span-7"
        >
          <div class="flex flex-wrap items-start justify-between gap-2">
            <div>
              <span class="mono-num text-[10px] font-semibold tracking-[0.09em] text-zinc-500">
                BENTO 03 // GOOGLE AI PRO DUAL-MODEL REASONING
              </span>
              <h2 class="mt-0.5 text-[17px] font-semibold text-zinc-100">
                Multi-Agent Debate Stream
              </h2>
            </div>

            <div class="mono-num flex flex-wrap items-center gap-1.5 text-[10px]">
              <span
                class="rounded-md border px-2 py-0.5"
                :class="
                  systemStatus.gatekeeper
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : 'border-white/10 bg-white/5 text-zinc-400'
                "
              >
                1. ML GATE
              </span>
              <span class="text-zinc-600">→</span>
              <span
                class="rounded-md border px-2 py-0.5"
                :class="
                  hasHighImpactEvent
                    ? 'border-rose-500/35 bg-rose-500/10 text-rose-300'
                    : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                "
              >
                2. HYDROGEN
              </span>
              <span class="text-zinc-600">→</span>
              <span
                class="rounded-md border px-2 py-0.5"
                :class="
                  systemStatus.gatekeeper
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : 'border-white/10 bg-white/5 text-zinc-400'
                "
              >
                3. ARGON ANALYST
              </span>
              <span class="text-zinc-600">→</span>
              <span
                class="rounded-md border px-2 py-0.5"
                :class="
                  !systemStatus.gatekeeper
                    ? 'border-white/10 bg-white/5 text-zinc-400'
                    : criticAgent.approve_trade
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : 'border-rose-500/35 bg-rose-500/10 text-rose-300'
                "
              >
                4. DEVIL'S ADVOCATE
              </span>
            </div>
          </div>

          <div class="grid flex-1 grid-cols-1 gap-3 md:grid-cols-3">
            <!-- Agent 1: Gemini 4 Hydrogen -->
            <article
              class="flex flex-col gap-2.5 rounded-xl border border-white/[0.08] border-t-2 border-t-cyan-400 bg-black/40 p-3.5"
            >
              <div class="flex items-start justify-between gap-2">
                <div>
                  <div class="text-[13px] font-bold text-zinc-100">[Gemini 4 Hydrogen]</div>
                  <div class="text-[10.5px] text-zinc-500">Macro News &amp; Event Sentinel</div>
                </div>
                <span
                  class="mono-num rounded-md border px-2 py-0.5 text-[10px] font-bold"
                  :class="
                    hasHighImpactEvent
                      ? 'border-rose-500/40 bg-rose-500/15 text-rose-300'
                      : 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300'
                  "
                >
                  {{ hasHighImpactEvent ? "EVENT LOCK" : String(hydrogenAgent.status || "CACHED").toUpperCase() }}
                </span>
              </div>

              <ul class="flex list-disc flex-col gap-1.5 pl-4 text-xs leading-relaxed text-zinc-300">
                <li v-for="(line, idx) in hydrogenAgent.summary || []" :key="idx">
                  <template v-for="(seg, sIdx) in tokenizeText(line)" :key="sIdx">
                    <span
                      v-if="seg.isToken"
                      class="mono-num rounded bg-cyan-500/10 px-1 py-0.5 text-[11px] text-cyan-300"
                    >
                      {{ seg.text }}
                    </span>
                    <template v-else>{{ seg.text }}</template>
                  </template>
                </li>
              </ul>

              <div class="mono-num mt-auto flex justify-between border-t border-white/[0.06] pt-2 text-[10.5px]">
                <span class="text-zinc-500">MACRO BREAKER</span>
                <span :class="hasHighImpactEvent ? 'text-rose-400' : 'text-emerald-400'">
                  {{ hasHighImpactEvent ? "ARMED (LOCKED)" : "DISARMED (CLEAR)" }}
                </span>
              </div>
            </article>

            <!-- Agent 2: Gemini 4 Argon Lead Analyst -->
            <article
              class="flex flex-col gap-2.5 rounded-xl border border-white/[0.08] border-t-2 bg-black/40 p-3.5"
              :class="analystDecision === 'SHORT' ? 'border-t-rose-500' : 'border-t-emerald-500'"
            >
              <div class="flex items-start justify-between gap-2">
                <div>
                  <div class="text-[13px] font-bold text-zinc-100">
                    [Gemini 4 Argon • Lead Analyst]
                  </div>
                  <div class="text-[10.5px] text-zinc-500">Turn 1 • Setup &amp; Grounded Rationale</div>
                </div>
                <span
                  class="mono-num rounded-md border px-2 py-0.5 text-[10px] font-bold"
                  :class="
                    analystDecision === 'LONG'
                      ? 'border-emerald-500/35 bg-emerald-500/15 text-emerald-300'
                      : analystDecision === 'SHORT'
                      ? 'border-rose-500/40 bg-rose-500/15 text-rose-300'
                      : 'border-white/15 bg-white/5 text-zinc-300'
                  "
                >
                  {{ analystDecision }}
                </span>
              </div>

              <p
                class="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5 text-[11.5px] leading-relaxed text-zinc-300"
              >
                <template v-for="(seg, idx) in tokenizeText(analystAgent.rationale || '')" :key="idx">
                  <span
                    v-if="seg.isToken"
                    class="mono-num rounded bg-cyan-500/10 px-1 py-0.5 text-[11px] text-cyan-300"
                  >
                    {{ seg.text }}
                  </span>
                  <template v-else>{{ seg.text }}</template>
                </template>
              </p>

              <div class="mono-num mt-auto flex flex-col gap-1.5 border-t border-white/[0.06] pt-2">
                <div class="flex justify-between text-[10.5px] text-zinc-400">
                  <span>ANALYST CONFIDENCE</span>
                  <span>{{ Number(analystAgent.confidence_score || 0) }}/100</span>
                </div>
                <div class="h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div
                    class="h-full rounded-full transition-all duration-300"
                    :class="analystDecision === 'SHORT' ? 'bg-rose-500' : 'bg-emerald-500'"
                    :style="{ width: `${Math.min(100, Math.max(0, Number(analystAgent.confidence_score || 0)))}%` }"
                  ></div>
                </div>
              </div>
            </article>

            <!-- Agent 3: Gemini 4 Argon Devil's Advocate -->
            <article
              class="flex flex-col gap-2.5 rounded-xl border border-white/[0.08] border-t-2 bg-black/40 p-3.5"
              :class="criticAgent.approve_trade ? 'border-t-amber-400' : 'border-t-rose-500'"
            >
              <div class="flex items-start justify-between gap-2">
                <div>
                  <div class="text-[13px] font-bold text-zinc-100">
                    [Gemini 4 Argon • Devil's Advocate]
                  </div>
                  <div class="text-[10.5px] text-zinc-500">Turn 2 • Risk Critique &amp; Veto</div>
                </div>
                <span
                  class="mono-num rounded-md border px-2 py-0.5 text-[10px] font-bold"
                  :class="
                    criticAgent.approve_trade
                      ? 'border-emerald-500/35 bg-emerald-500/15 text-emerald-300'
                      : 'border-rose-500/40 bg-rose-500/15 text-rose-300'
                  "
                >
                  {{ criticAgent.approve_trade ? "APPROVED" : systemStatus.gatekeeper ? "VETO / REJECT" : "STANDBY" }}
                </span>
              </div>

              <ul class="flex list-disc flex-col gap-1.5 pl-4 text-xs leading-relaxed text-zinc-300">
                <li v-for="(flaw, idx) in criticAgent.critical_flaws || []" :key="idx">
                  <template v-for="(seg, sIdx) in tokenizeText(flaw)" :key="sIdx">
                    <span
                      v-if="seg.isToken"
                      class="mono-num rounded bg-cyan-500/10 px-1 py-0.5 text-[11px] text-cyan-300"
                    >
                      {{ seg.text }}
                    </span>
                    <template v-else>{{ seg.text }}</template>
                  </template>
                </li>
              </ul>

              <div class="mono-num mt-auto flex flex-col gap-1.5 border-t border-white/[0.06] pt-2">
                <div class="flex justify-between text-[10.5px] text-zinc-400">
                  <span>ADJUSTED CONFIDENCE</span>
                  <span>{{ Number(criticAgent.adjusted_confidence || 0) }}/100</span>
                </div>
                <div class="h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div
                    class="h-full rounded-full transition-all duration-300"
                    :class="criticAgent.approve_trade ? 'bg-emerald-500' : 'bg-rose-500'"
                    :style="{ width: `${Math.min(100, Math.max(0, Number(criticAgent.adjusted_confidence || 0)))}%` }"
                  ></div>
                </div>
              </div>
            </article>
          </div>
        </section>

        <!-- BENTO BOX 4: COMMAND & KILL SWITCH (5 COLS) -->
        <section
          class="glass-panel col-span-12 flex min-h-[420px] flex-col gap-3.5 rounded-2xl p-5 lg:col-span-5"
        >
          <div class="flex flex-wrap items-start justify-between gap-2">
            <div>
              <span class="mono-num text-[10px] font-semibold tracking-[0.09em] text-zinc-500">
                BENTO 04 // EMERGENCY &amp; AUDIT
              </span>
              <h2 class="mt-0.5 text-[17px] font-semibold text-zinc-100">
                Command &amp; Kill Switch
              </h2>
            </div>
            <span
              class="mono-num rounded-md border px-2.5 py-1 text-[10px] font-bold"
              :class="
                systemStatus.kill_switch
                  ? 'border-rose-500/45 bg-rose-500/15 text-rose-300'
                  : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
              "
            >
              {{ systemStatus.kill_switch ? "HALTED • POSITIONS CLOSED" : "SYSTEM ARMED • NORMAL" }}
            </span>
          </div>

          <button
            type="button"
            @click="toggleKillSwitch"
            class="flex w-full items-center gap-3.5 rounded-xl border px-4 py-3.5 text-left transition-all"
            :class="
              systemStatus.kill_switch
                ? 'animate-pulse border-rose-300 bg-gradient-to-r from-rose-600/80 to-red-700/80 text-white shadow-[0_0_30px_rgba(244,63,94,0.4)]'
                : 'border-rose-500/55 bg-gradient-to-r from-rose-600/35 to-rose-800/45 text-rose-50 shadow-[0_10px_28px_rgba(244,63,94,0.22)] hover:-translate-y-0.5 hover:shadow-[0_14px_34px_rgba(244,63,94,0.34)]'
            "
          >
            <span
              class="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-white/20 bg-black/30"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <path d="M12 2v10" />
                <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
              </svg>
            </span>
            <span class="flex flex-col">
              <strong class="text-xs font-bold tracking-[0.08em] sm:text-[13px]">
                {{ systemStatus.kill_switch ? "KILL SWITCH ENGAGED — CLICK TO DISARM" : "EMERGENCY KILL SWITCH" }}
              </strong>
              <span class="text-[11px] text-rose-100/85">
                {{
                  systemStatus.kill_switch
                    ? "Toàn bộ lệnh đã đóng • Bot đang tạm ngưng (POST /api/kill-switch?enabled=false)"
                    : "Đóng toàn bộ lệnh & ngắt bot ngay lập tức (POST /api/kill-switch)"
                }}
              </span>
            </span>
          </button>

          <div class="mono-num rounded-lg border border-white/[0.08] bg-white/[0.025] px-3 py-2 text-[10.5px] text-zinc-400">
            {{
              systemStatus.kill_switch
                ? "EMERGENCY STOP ACTIVE: Tất cả vị thế mở đã đóng và Gatekeeper bị khóa cho đến khi mở lại."
                : "Trạng thái an toàn: Guardrails Python giám sát liên tục 24/7 theo từng nến."
            }}
          </div>

          <div class="flex min-h-0 flex-1 flex-col gap-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold text-zinc-200">
                Lịch sử Kiểm duyệt Guardrails ({{ currency }})
              </span>
              <span class="mono-num text-[10px] text-zinc-500">{{ history.length }} SESSIONS</span>
            </div>

            <div
              class="max-h-[240px] flex-1 overflow-auto rounded-xl border border-white/[0.08] bg-[#07080b]"
            >
              <table class="mono-num w-full border-collapse text-left text-[11px]">
                <thead class="sticky top-0 bg-zinc-950/95 text-[9.5px] tracking-wider text-zinc-500">
                  <tr class="border-b border-white/[0.08]">
                    <th class="px-2.5 py-2">ID / TIME</th>
                    <th class="px-2.5 py-2">SIDE</th>
                    <th class="px-2.5 py-2">ENTRY / SL / TP</th>
                    <th class="px-2.5 py-2">R:R</th>
                    <th class="px-2.5 py-2">VERDICT</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in history"
                    :key="row.id"
                    class="border-b border-white/[0.045] last:border-none"
                  >
                    <td class="px-2.5 py-2 align-top">
                      <div class="font-semibold text-zinc-200">{{ row.id }}</div>
                      <div class="text-[9.5px] text-zinc-500">{{ row.timestamp }}</div>
                    </td>
                    <td
                      class="px-2.5 py-2 align-top font-bold"
                      :class="
                        row.direction === 'LONG'
                          ? 'text-emerald-400'
                          : row.direction === 'SHORT'
                          ? 'text-rose-400'
                          : 'text-zinc-400'
                      "
                    >
                      {{ row.direction }}
                    </td>
                    <td class="px-2.5 py-2 align-top text-zinc-300">
                      <template v-if="row.entry && row.sl && row.tp">
                        <div>{{ formatMoney(row.entry, { decimals: 1 }) }}</div>
                        <div class="text-[9.5px] text-zinc-500">
                          SL {{ formatMoney(row.sl, { decimals: 1 }) }} / TP {{ formatMoney(row.tp, { decimals: 1 }) }}
                        </div>
                      </template>
                      <span v-else class="text-zinc-500">NO ORDER LEVELS</span>
                    </td>
                    <td class="px-2.5 py-2 align-top text-zinc-300">
                      {{ row.rr_ratio ? `${Number(row.rr_ratio).toFixed(2)}R` : "—" }}
                    </td>
                    <td class="px-2.5 py-2 align-top">
                      <span
                        class="inline-block rounded px-1.5 py-0.5 text-[9.5px] font-bold"
                        :class="
                          row.status === 'APPROVED'
                            ? 'border border-emerald-500/30 bg-emerald-500/15 text-emerald-300'
                            : 'border border-rose-500/35 bg-rose-500/15 text-rose-300'
                        "
                      >
                        {{ row.status }}
                      </span>
                      <div class="mt-1 text-[9.5px] text-zinc-500">
                        {{ (row.reasons || []).join(", ") }}
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { CrosshairMode, createChart } from "lightweight-charts";
import { useCurrency } from "./composables/useCurrency";

const isFileOrigin = typeof window !== "undefined" && window.location.protocol === "file:";
const configuredApiBase = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const configuredWsBase = (import.meta.env.VITE_API_WS_URL || "").replace(/\/$/, "");
const API_BASE = isFileOrigin ? "http://localhost:8000" : configuredApiBase;
const API_WS_URL = isFileOrigin
  ? "ws://localhost:8000/ws/stream"
  : configuredWsBase ||
    (configuredApiBase
      ? `${configuredApiBase.replace(/^http/, "ws")}/ws/stream`
      : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/stream`);

const { currency, vndRate, setCurrency, setVndRate, formatMoney, formatAltMoney } =
  useCurrency(25716);

const scenarioOptions = [
  { id: "long_approved", label: "LONG APPROVED" },
  { id: "short_rejected", label: "SHORT REJECTED" },
  { id: "macro_lock", label: "MACRO LOCK" },
  { id: "neutral_standby", label: "IDLE" },
];

const activePreset = ref("long_approved");
const timeframe = ref("1h");
const syncingLive = ref(false);
const apiWsConnected = ref(false);
const binanceWsConnected = ref(false);
const liveTickPrice = ref(64590.6);
const marketSource = ref("binance_futures_live");

const market = ref({
  symbol: "BTC/USDT:USDT",
  price: 64590.6,
  entry: 64590.6,
  sl: 63829.7,
  tp: 66264.5,
  liquidation_price: 58389.9,
  rr_ratio: 2.2,
});

const agentDebateStream = ref([
  {
    agent: "hydrogen",
    status: "cached",
    summary: [
      "US Core CPI prints in-line at 0.2% MoM; no FOMC rate hike scheduled within 4h window.",
      "Spot BTC ETF flow stable while perpetual open_interest holds near session baseline.",
      "HIGH_IMPACT_EVENT flag: FALSE (Macro Circuit Breaker disarmed).",
    ],
  },
  {
    agent: "argon_analyst",
    decision: "LONG",
    confidence_score: 82,
    rationale:
      "Confluence confirmed: close=64590.6 holding intraday support, rsi_1h=45.01, ml_probability=0.74 (>0.65 gate). ATR(14)=507.25 yields entry=64590.6, sl=63829.7, tp=66264.5 (R:R=2.20).",
  },
  {
    agent: "argon_critic",
    approve_trade: true,
    adjusted_confidence: 78,
    critical_flaws: [
      "Perpetual funding_rate=+0.0012% remains muted; watch resistance near 66265.",
      "Stop distance 760.9 USDT (1.50x ATR) passes [0.5, 2.5] ATR bounds; liq at 58389.9 is >30% farther than SL.",
    ],
  },
]);

const systemStatus = ref({
  gatekeeper: true,
  remaining_daily_quota_estimate: 92,
  kill_switch: false,
});

const portfolio = ref({
  mode: "PAPER",
  open_positions: 1,
  balance_usdt: 10000.0,
  max_risk_pct: 1.5,
  leverage: 10,
  margin_mode: "ISOLATED",
  ml_probability: 0.74,
  atr: 507.25,
  rsi: 45.01,
  change_24h_pct: -1.04,
  high_24h: 65776.5,
  low_24h: 64073.7,
  vnd_rate: 25716,
  direction: "LONG",
});

const history = ref([]);

const h1Countdown = ref("--:--");
const h4Countdown = ref("--:--:--");

const chartContainerRef = ref(null);
let chartInstance = null;
let candleSeries = null;
let volumeSeries = null;
let priceLines = {};
let resizeObserver = null;
let apiSocket = null;
let binanceSocket = null;
let countdownTimer = null;

const liveMarkPrice = computed(() => liveTickPrice.value || market.value.price || 64590.6);

const hydrogenAgent = computed(
  () =>
    agentDebateStream.value.find((a) => a.agent === "hydrogen") || {
      agent: "hydrogen",
      status: "cached",
      summary: [],
    }
);

const analystAgent = computed(
  () =>
    agentDebateStream.value.find((a) => a.agent === "argon_analyst") || {
      agent: "argon_analyst",
      decision: "NEUTRAL",
      confidence_score: 0,
      rationale: "",
    }
);

const criticAgent = computed(
  () =>
    agentDebateStream.value.find((a) => a.agent === "argon_critic") || {
      agent: "argon_critic",
      approve_trade: false,
      adjusted_confidence: 0,
      critical_flaws: [],
    }
);

const analystDecision = computed(() =>
  String(analystAgent.value.decision || "NEUTRAL").toUpperCase()
);

const hasHighImpactEvent = computed(() =>
  (hydrogenAgent.value.summary || []).some((line) => {
    const up = String(line).toUpperCase();
    return up.includes("HIGH_IMPACT_EVENT: TRUE") || up.includes("HIGH_IMPACT_EVENT FLAG: TRUE");
  })
);

const isRejected = computed(
  () =>
    Boolean(systemStatus.value.kill_switch) ||
    hasHighImpactEvent.value ||
    (market.value.rr_ratio !== null && Number(market.value.rr_ratio) < 1.8) ||
    (systemStatus.value.gatekeeper && !criticAgent.value.approve_trade && analystDecision.value !== "NEUTRAL")
);

const visualState = computed(() => {
  if (systemStatus.value.kill_switch || hasHighImpactEvent.value || isRejected.value) return "short";
  if (!systemStatus.value.gatekeeper || analystDecision.value === "NEUTRAL") return "neutral";
  if (analystDecision.value === "SHORT") return "short";
  return "long";
});

const ambientOrbClass = computed(() => {
  if (visualState.value === "short") return "bg-rose-500/20";
  if (visualState.value === "neutral") return "bg-cyan-500/10";
  return "bg-emerald-500/20";
});

const stateAccentDotClass = computed(() => {
  if (visualState.value === "short") return "bg-rose-500 shadow-[0_0_12px_#f43f5e]";
  if (visualState.value === "neutral") return "bg-cyan-400 shadow-[0_0_12px_#22d3ee]";
  return "bg-emerald-400 shadow-[0_0_12px_#10b981]";
});

const stateAccentTextClass = computed(() => {
  if (visualState.value === "short") return "text-rose-400";
  if (visualState.value === "neutral") return "text-cyan-400";
  return "text-emerald-400";
});

const marketCardGlowClass = computed(() => {
  if (visualState.value === "short") return "glow-short";
  if (visualState.value === "neutral") return "glow-neutral";
  return "glow-long";
});

const wsStatusLabel = computed(() => {
  if (binanceWsConnected.value && apiWsConnected.value) return "WS: BINANCE + API LIVE";
  if (binanceWsConnected.value) return "WS: BINANCE FUTURES LIVE";
  if (apiWsConnected.value) return "WS: API STREAM LIVE";
  return "WS: CONNECTING";
});

const marketSourceLabel = computed(() =>
  marketSource.value === "binance_futures_live" ? "BINANCE FAPI LIVE" : "CACHED SNAPSHOT"
);

const directionBadgeText = computed(() => {
  if (systemStatus.value.kill_switch) return "KILL-SWITCH HALTED";
  if (hasHighImpactEvent.value) return "MACRO LOCKED";
  if (!systemStatus.value.gatekeeper || analystDecision.value === "NEUTRAL") return "FLAT • STANDBY";
  if (isRejected.value) return `${analystDecision.value} REJECTED`;
  return `${analystDecision.value} ACTIVE`;
});

const directionBadgeClass = computed(() => {
  if (systemStatus.value.kill_switch || hasHighImpactEvent.value || isRejected.value) {
    return "border-rose-500/45 bg-rose-500/15 text-rose-300";
  }
  if (!systemStatus.value.gatekeeper || analystDecision.value === "NEUTRAL") {
    return "border-white/15 bg-white/5 text-zinc-300";
  }
  if (analystDecision.value === "SHORT") {
    return "border-rose-500/45 bg-rose-500/15 text-rose-300";
  }
  return "border-emerald-500/40 bg-emerald-500/15 text-emerald-300";
});

const isPaperMode = computed(() => String(portfolio.value.mode || "PAPER").toUpperCase() === "PAPER");

const riskAmountUsd = computed(
  () => Number(portfolio.value.balance_usdt || 10000) * (Number(portfolio.value.max_risk_pct || 1.5) / 100)
);

const positionStats = computed(() => {
  const { entry, sl, liquidation_price: liq } = market.value;
  if (!entry || !sl) {
    return { qtyBtc: 0, marginUsd: 0, bufferLabel: "NO ACTIVE SETUP" };
  }
  const stopDist = Math.abs(Number(entry) - Number(sl));
  const lev = Number(portfolio.value.leverage || 10);
  const qtyBtc = stopDist > 0 ? riskAmountUsd.value / stopDist : 0;
  const marginUsd = (qtyBtc * Number(entry)) / lev;
  const liqDist = liq ? Math.abs(Number(entry) - Number(liq)) : 0;
  const bufferPct = stopDist > 0 && liqDist > 0 ? (liqDist / stopDist - 1) * 100 : 0;
  const bufferLabel =
    liqDist >= stopDist * 1.3
      ? `SL BUFFER: +${bufferPct.toFixed(1)}% OK`
      : `BUFFER FAIL: +${bufferPct.toFixed(1)}% (<30%)`;
  return { qtyBtc, marginUsd, bufferLabel };
});

const mlProbabilityPct = computed(() => {
  const prob = Number(
    portfolio.value.ml_probability ?? (systemStatus.value.gatekeeper ? 0.74 : 0.42)
  );
  return Math.max(0, Math.min(100, prob * 100));
});

const guardrailChecks = computed(() => {
  const hasLevels = Boolean(market.value.entry && market.value.sl && market.value.tp);
  const rrPass = !hasLevels || Number(market.value.rr_ratio || 0) >= 1.8;
  const atr = Number(portfolio.value.atr || 507.25);
  const stopDist = hasLevels ? Math.abs(Number(market.value.entry) - Number(market.value.sl)) : atr;
  const atrPass = !hasLevels || (stopDist >= 0.5 * atr && stopDist <= 2.5 * atr);
  const isoPass =
    Number(portfolio.value.leverage || 10) <= 10 &&
    (portfolio.value.margin_mode || "ISOLATED") === "ISOLATED";
  const macroPass = !hasHighImpactEvent.value;
  return [
    { label: "R:R ≥ 1.8", pass: rrPass },
    { label: "SL ∈ [0.5, 2.5] ATR", pass: atrPass },
    { label: "ISOLATED ≤ 10x", pass: isoPass },
    { label: macroPass ? "MACRO CLEAR" : "MACRO EVENT LOCK", pass: macroPass },
  ];
});

function tokenizeText(text) {
  const regex = /(\b[a-zA-Z0-9_()]+=[+-]?[0-9]+(?:\.[0-9]+)?x?%?|\bR:R=[0-9.]+|\b[A-Z_]{5,})/g;
  const str = String(text || "");
  const out = [];
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(str)) !== null) {
    if (match.index > lastIndex) {
      out.push({ text: str.slice(lastIndex, match.index), isToken: false });
    }
    out.push({ text: match[0], isToken: true });
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < str.length) {
    out.push({ text: str.slice(lastIndex), isToken: false });
  }
  return out;
}

function updateCountdowns() {
  const nowSec = Math.floor(Date.now() / 1000);
  const h1Rem = 3600 - (nowSec % 3600);
  const h4Rem = 14400 - (nowSec % 14400);
  h1Countdown.value = `${String(Math.floor(h1Rem / 60)).padStart(2, "0")}:${String(
    h1Rem % 60
  ).padStart(2, "0")}`;
  h4Countdown.value = `${String(Math.floor(h4Rem / 3600)).padStart(2, "0")}:${String(
    Math.floor((h4Rem % 3600) / 60)
  ).padStart(2, "0")}:${String(h4Rem % 60).padStart(2, "0")}`;
}

function applyChartPriceFormatter() {
  if (!chartInstance) return;
  chartInstance.applyOptions({
    localization: {
      priceFormatter: (price) => {
        if (currency.value === "VND") {
          return `${Math.round(price * vndRate.value).toLocaleString("en-US")} ₫`;
        }
        return `$${Number(price).toLocaleString("en-US", {
          minimumFractionDigits: 1,
          maximumFractionDigits: 1,
        })}`;
      },
    },
  });
}

function syncPriceLines() {
  if (!candleSeries) return;
  const specs = [
    { key: "entry", value: market.value.entry, title: "ENTRY", color: "#22d3ee", lineStyle: 0 },
    { key: "tp", value: market.value.tp, title: "TAKE-PROFIT", color: "#10b981", lineStyle: 2 },
    { key: "sl", value: market.value.sl, title: "STOP-LOSS", color: "#f43f5e", lineStyle: 2 },
    {
      key: "liq",
      value: market.value.liquidation_price,
      title: "LIQUIDATION",
      color: "#f59e0b",
      lineStyle: 3,
    },
  ];
  for (const spec of specs) {
    if (priceLines[spec.key]) {
      candleSeries.removePriceLine(priceLines[spec.key]);
      delete priceLines[spec.key];
    }
    if (spec.value !== null && spec.value !== undefined && Number(spec.value) > 0) {
      priceLines[spec.key] = candleSeries.createPriceLine({
        price: Number(spec.value),
        color: spec.color,
        lineWidth: spec.key === "entry" ? 2 : 1,
        lineStyle: spec.lineStyle,
        axisLabelVisible: true,
        title: spec.title,
      });
    }
  }
}

function initChart() {
  if (!chartContainerRef.value) return;
  chartInstance = createChart(chartContainerRef.value, {
    layout: {
      background: { color: "transparent" },
      textColor: "#a1a1aa",
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 11,
    },
    grid: {
      vertLines: { color: "rgba(255, 255, 255, 0.04)" },
      horzLines: { color: "rgba(255, 255, 255, 0.04)" },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: { color: "rgba(255, 255, 255, 0.2)", labelBackgroundColor: "#18181b" },
      horzLine: { color: "rgba(255, 255, 255, 0.2)", labelBackgroundColor: "#18181b" },
    },
    rightPriceScale: {
      borderColor: "rgba(255, 255, 255, 0.08)",
      scaleMargins: { top: 0.14, bottom: 0.2 },
    },
    timeScale: {
      borderColor: "rgba(255, 255, 255, 0.08)",
      timeVisible: true,
      secondsVisible: false,
    },
  });

  candleSeries = chartInstance.addCandlestickSeries({
    upColor: "#10b981",
    downColor: "#f43f5e",
    borderUpColor: "#34d399",
    borderDownColor: "#fb7185",
    wickUpColor: "#10b981",
    wickDownColor: "#f43f5e",
  });

  volumeSeries = chartInstance.addHistogramSeries({
    priceFormat: { type: "volume" },
    priceScaleId: "",
    scaleMargins: { top: 0.82, bottom: 0 },
  });

  applyChartPriceFormatter();
  syncPriceLines();

  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0 && chartInstance) {
        chartInstance.applyOptions({ width, height });
      }
    }
  });
  resizeObserver.observe(chartContainerRef.value);
}

async function loadLiveCandles() {
  let loadedCandles = [];
  try {
    const resp = await fetch(`${API_BASE}/api/market/live?timeframe=${timeframe.value}&limit=120`);
    if (resp.ok) {
      const data = await resp.json();
      if (data.vnd_rate) setVndRate(data.vnd_rate);
      if (data.ticker?.last_price) liveTickPrice.value = Number(data.ticker.last_price);
      if (data.ticker) {
        portfolio.value.change_24h_pct = data.ticker.change_24h_pct;
        portfolio.value.high_24h = data.ticker.high_24h;
        portfolio.value.low_24h = data.ticker.low_24h;
      }
      if (data.indicators?.atr) portfolio.value.atr = data.indicators.atr;
      if (data.indicators?.rsi) portfolio.value.rsi = data.indicators.rsi;
      marketSource.value = data.source || "binance_futures_live";
      if (Array.isArray(data.candles) && data.candles.length > 0) {
        loadedCandles = data.candles;
      }
    }
  } catch {
    // Fallback to direct Binance Futures public REST API below
  }

  if (loadedCandles.length === 0) {
    try {
      const [kResp, tResp] = await Promise.all([
        fetch(`https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=${timeframe.value}&limit=120`),
        fetch("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT"),
      ]);
      if (kResp.ok) {
        const raw = await kResp.json();
        loadedCandles = raw.map((r) => ({
          time: Math.floor(Number(r[0]) / 1000),
          open: Number(r[1]),
          high: Number(r[2]),
          low: Number(r[3]),
          close: Number(r[4]),
          volume: Number(r[5]),
        }));
        marketSource.value = "binance_futures_live";
      }
      if (tResp.ok) {
        const t = await tResp.json();
        liveTickPrice.value = Number(t.lastPrice);
        portfolio.value.change_24h_pct = Number(t.priceChangePercent);
        portfolio.value.high_24h = Number(t.highPrice);
        portfolio.value.low_24h = Number(t.lowPrice);
      }
    } catch {
      marketSource.value = "fallback_cached";
    }
  }

  if (loadedCandles.length > 0 && candleSeries && volumeSeries) {
    candleSeries.setData(loadedCandles);
    volumeSeries.setData(
      loadedCandles.map((c) => ({
        time: c.time,
        value: c.volume,
        color: c.close >= c.open ? "rgba(16, 185, 129, 0.24)" : "rgba(244, 63, 94, 0.24)",
      }))
    );
    chartInstance?.timeScale().fitContent();
    liveTickPrice.value = loadedCandles[loadedCandles.length - 1].close;
  }
}

function connectBinanceStream() {
  if (binanceSocket) {
    binanceSocket.close();
    binanceSocket = null;
  }
  try {
    const ws = new WebSocket(`wss://fstream.binance.com/ws/btcusdt@kline_${timeframe.value}`);
    binanceSocket = ws;
    ws.onopen = () => {
      binanceWsConnected.value = true;
    };
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const k = payload.k;
        if (!k || !candleSeries || !volumeSeries) return;
        const bar = {
          time: Math.floor(Number(k.t) / 1000),
          open: Number(k.o),
          high: Number(k.h),
          low: Number(k.l),
          close: Number(k.c),
        };
        liveTickPrice.value = bar.close;
        marketSource.value = "binance_futures_live";
        candleSeries.update(bar);
        volumeSeries.update({
          time: bar.time,
          value: Number(k.v),
          color: bar.close >= bar.open ? "rgba(16, 185, 129, 0.24)" : "rgba(244, 63, 94, 0.24)",
        });
      } catch {
        // Ignore malformed kline frame
      }
    };
    ws.onclose = () => {
      binanceWsConnected.value = false;
    };
    ws.onerror = () => {
      binanceWsConnected.value = false;
    };
  } catch {
    binanceWsConnected.value = false;
  }
}

function applyStreamSnapshot(raw) {
  const item = Array.isArray(raw) ? raw[0] : raw;
  if (!item || typeof item !== "object") return;
  if (item.market_snapshot) {
    market.value = {
      ...market.value,
      ...item.market_snapshot,
      price:
        Number(item.market_snapshot.price) > 0
          ? Number(item.market_snapshot.price)
          : liveTickPrice.value,
    };
  }
  if (Array.isArray(item.agent_debate_stream)) {
    agentDebateStream.value = item.agent_debate_stream;
  }
  if (item.system_status) {
    systemStatus.value = { ...systemStatus.value, ...item.system_status };
  }
}

function connectBackendWs() {
  try {
    const ws = new WebSocket(API_WS_URL);
    apiSocket = ws;
    ws.onopen = () => {
      apiWsConnected.value = true;
    };
    ws.onmessage = (event) => {
      try {
        applyStreamSnapshot(JSON.parse(event.data));
      } catch {
        // Ignore malformed frame
      }
    };
    ws.onclose = () => {
      apiWsConnected.value = false;
      setTimeout(connectBackendWs, 3000);
    };
    ws.onerror = () => {
      apiWsConnected.value = false;
    };
  } catch {
    apiWsConnected.value = false;
  }
}

async function fetchRestBootstrap() {
  try {
    const [pResp, hResp] = await Promise.all([
      fetch(`${API_BASE}/api/portfolio`),
      fetch(`${API_BASE}/api/history`),
    ]);
    if (pResp.ok) {
      const p = await pResp.json();
      portfolio.value = { ...portfolio.value, ...p };
      if (p.vnd_rate) setVndRate(p.vnd_rate);
    }
    if (hResp.ok) {
      const h = await hResp.json();
      history.value = Array.isArray(h) ? h : h.history || [];
    }
  } catch {
    // Keep existing reactive defaults if backend offline
  }
}

async function syncLiveNow() {
  syncingLive.value = true;
  try {
    const resp = await fetch(`${API_BASE}/api/sync-live`, { method: "POST" });
    if (resp.ok) {
      const data = await resp.json();
      if (data.snapshot) applyStreamSnapshot(data.snapshot);
      if (data.portfolio) {
        portfolio.value = { ...portfolio.value, ...data.portfolio };
        if (data.portfolio.vnd_rate) setVndRate(data.portfolio.vnd_rate);
      }
      if (data.history) history.value = data.history;
      if (data.price) liveTickPrice.value = Number(data.price);
    }
    await loadLiveCandles();
  } finally {
    syncingLive.value = false;
  }
}

async function selectPreset(presetId) {
  activePreset.value = presetId;
  try {
    const resp = await fetch(`${API_BASE}/api/simulate/${presetId}`, { method: "POST" });
    if (resp.ok) {
      const data = await resp.json();
      if (data.snapshot) applyStreamSnapshot(data.snapshot);
      if (data.portfolio) portfolio.value = { ...portfolio.value, ...data.portfolio };
      if (data.history) history.value = data.history;
    }
  } catch {
    // Ignore offline error
  }
}

async function changeTimeframe(tf) {
  timeframe.value = tf;
  await loadLiveCandles();
  connectBinanceStream();
}

async function toggleTradingMode() {
  const next = isPaperMode.value ? "TESTNET" : "PAPER";
  try {
    const resp = await fetch(`${API_BASE}/api/mode?mode=${next}`, { method: "POST" });
    if (resp.ok) {
      const data = await resp.json();
      portfolio.value.mode = data.mode || next;
      return;
    }
  } catch {
    // Fallback below
  }
  portfolio.value.mode = next;
}

async function toggleKillSwitch() {
  const nextEnabled = !systemStatus.value.kill_switch;
  try {
    const resp = await fetch(`${API_BASE}/api/kill-switch?enabled=${nextEnabled}`, {
      method: "POST",
    });
    if (resp.ok) {
      const data = await resp.json();
      systemStatus.value.kill_switch = Boolean(data.kill_switch);
      if (data.kill_switch) {
        systemStatus.value.gatekeeper = false;
        portfolio.value.open_positions = 0;
      }
      await fetchRestBootstrap();
      return;
    }
  } catch {
    // Fallback below
  }
  systemStatus.value.kill_switch = nextEnabled;
  if (nextEnabled) {
    systemStatus.value.gatekeeper = false;
    portfolio.value.open_positions = 0;
  }
}

watch([currency, vndRate], () => {
  applyChartPriceFormatter();
});

watch(
  () => [market.value.entry, market.value.sl, market.value.tp, market.value.liquidation_price],
  () => {
    syncPriceLines();
  }
);

onMounted(async () => {
  updateCountdowns();
  countdownTimer = setInterval(updateCountdowns, 1000);
  initChart();
  await fetchRestBootstrap();
  await syncLiveNow();
  connectBackendWs();
  connectBinanceStream();
});

onBeforeUnmount(() => {
  if (countdownTimer) clearInterval(countdownTimer);
  if (resizeObserver) resizeObserver.disconnect();
  if (apiSocket) apiSocket.close();
  if (binanceSocket) binanceSocket.close();
  if (chartInstance) chartInstance.remove();
});
</script>
