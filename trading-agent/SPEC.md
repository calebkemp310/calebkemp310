# 24/7 Trading Agent: Gate 1 (Spec + Strategy Tournament)

_Status: **waiting for Caleb's approval**. Nothing in this folder can place an order._
_Data through 2026-11-06 (UTC daily close). Numbers come from `results/research.md`, produced by `python -m research.run_research`._

## 1. System overview

- **Venue:** US spot crypto (BTC, ETH, SOL) on Kraken Pro or Coinbase Advanced. These markets are open 24/7, so the agent runs around the clock, which suits a 6 AM to 4 PM work day.
- **Regime right now:** a downtrend inside a longer uptrend. All three coins are below their 50-day average and only just above their 200-day. Short-term volatility is low. TextToQuant's regime check reads SKIP (risk off) on the 1h to 1d charts and RUN only on the weekly.
- **Approach:** five simple candidate strategies, each with an economic reason to work. Each was tuned on 2019 to 2023 data and judged once on 2024 to 2026 data it never saw. It had to pass seven gates that were written before any result was seen.
- **Result: no strategy passed, so nothing gets deployed.** The best one, a 50-day trend filter, beats buy-and-hold only when trading costs are very low. At the fees a small US account actually pays, its edge mostly disappears.

## 2. Market and venue

| Item | Value | Source / status |
|---|---|---|
| Asset class | Spot crypto, long-only, no leverage | Shorting and perps add liquidation risk; offshore perps aren't open to US residents |
| Pairs | BTC-USD, ETH-USD, SOL-USD | Most liquid US pairs |
| Hours | 24/7/365 | Exchange maintenance windows are the exception |
| Fees (entry tier, US) | Coinbase Advanced ~0.50% maker / 0.90% taker. Kraken Pro 0.40% maker / 0.80% taker | **Assumption.** Reported Oct 2026; check the order preview in your own account |
| Spread | BTC-USD bid/ask 75,809.90 / 75,809.91 (one cent) | Coinbase public book, read 2026-11-07 05:01 UTC |
| Minimum order | Coinbase BTC-USD `min_market_funds` = $1 | Coinbase public product endpoint |
| Latency need | Low. Signals are daily, so seconds don't matter | Design choice |
| API limits | Public market data has rate limits; private trading endpoints need an API key with **trade permission only, never withdraw** | Confirm the limits at build time |
| Research data | Binance spot daily and 4h candles, 2019-01-01 to 2026-11-06 (SOL from 2020-08-11). Fingerprints are stored in `results/research.json` | Binance is a research proxy only: it doesn't serve US residents |

**When to trade / stay out (proposed):** trade only while the 200-day trend is up and 30-day realized volatility is below its 90th percentile. Stay flat when the data is stale, when the exchange reports a degraded status, in the hour around major US macro releases (CPI, FOMC), and after any kill-switch event until Caleb re-arms it.

**Funding rates and open interest:** not used. They come from perps venues this account can't trade, and the container can't reach them. This is a known gap.

## 3. Current regime (2026-11-06 daily close, Binance)

| Coin | Close | vs 50-day | vs 200-day | 30-day | 90-day | 30-day vol (percentile) | Off all-time high |
|---|---|---|---|---|---|---|---|
| BTC | 75,844 | -7.6% | +3.6% | -9.0% | +16.8% | 36% (18th) | -39.2% |
| ETH | 2,238.67 | -10.5% | +3.8% | -13.0% | +16.8% | 49% (17th) | -53.7% |
| SOL | 90.13 | -16.7% | +1.2% | -22.5% | +18.6% | 48% (4th) | -65.6% |

## 4. Candidate strategies

Signals and execution are kept separate: each strategy only emits "want long" or "want flat" at a bar's close, and the engine fills at the next bar's open.

| Strategy | Edge in one sentence | Who is on the other side | Entry | Exit | Stop | Typical hold / frequency |
|---|---|---|---|---|---|---|
| `trend_sma` | Crypto trends persist because capital and attention arrive slowly | Early profit-takers and dip-sellers | Daily close > SMA(n) | Daily close < SMA(n) | The exit rule; live adds a catastrophe stop | Weeks; ~10 trades/yr/coin |
| `tsmom` | Recent winners keep winning over 1 to 6 months | Mean-reversion traders | Trailing n-day return > 0 | Return ≤ 0 | Exit rule | Weeks; ~15/yr |
| `donchian` | Breakouts to new highs pull in momentum buyers | Range traders selling the highs | Close > prior n-day high | Close < prior m-day low | Exit rule | Weeks; ~4/yr |
| `rsi2_dip` | Short panics inside uptrends get bought back | Forced and liquidating sellers | Close > SMA200 and RSI(2) < x | Close > SMA5, or 10 days | 10-day time stop | Days; ~10/yr |
| `bollinger_revert_4h` | Intraday overshoots revert to the mean | Late momentum chasers | 4h close < mid − k·sd, in an uptrend | Close > mid, or 12 bars | Time stop | Hours to 2 days |

## 5. Validation method

- **No look-ahead.** Indicators only use bars up to t, and fills happen at t+1's open. A test changes future prices and checks that nothing before the cut moves. A second test checks that a deliberately leaky strategy gets caught.
- **Time split, not random.** Train is 2019-01-01 to 2023-12-31. Held-out is 2024-01-01 to 2026-11-06 and was scored exactly once.
- **Costs.** 0.60% fee + 0.05% slippage per side as the base, with a ladder at 0.10%, 0.25%, 0.65% and 1.30% per side.
- **Parameter neighbourhoods.** Every point in each grid was swept. The pick maximizes the average Sharpe of a point and its neighbours, so a single lucky setting can't win.
- **Multiple testing.** 105 trials were counted (strategy × parameters × coin). The deflated Sharpe ratio (Bailey & López de Prado) tests each pick against the best result expected by luck from that many trials.
- **The seven gates** (in `research/run_research.py`, unchanged after the run):
  1. Mean held-out Sharpe ≥ 0.5.
  2. Every coin's Sharpe > 0.
  3. Shallower drawdown than buy-and-hold on every coin.
  4. ≥ 70% of grid points profitable on train.
  5. Mean Sharpe > 0 at 1.3% per side.
  6. ≥ 30 held-out trades.
  7. Deflated Sharpe ≥ 0.90.

## 6. Comparison table (held-out 2024-01-01 to 2026-11-06, mean of BTC/ETH/SOL)

| Strategy | Edge | Market | Timeframe | Sharpe | Max drawdown (worst coin) | Trades | Cost sensitivity (Sharpe at 0.10% → 1.30% per side) | Verdict |
|---|---|---|---|---|---|---|---|---|
| Buy & hold (benchmark) | Market beta | BTC/ETH/SOL spot | 1d | 0.41 | -76.3% | 3 | n/a | benchmark |
| `trend_sma` n=50 | Trend persistence | same | 1d | 0.44 | -69.7% | 88 | 0.71 → 0.11 | **REJECT** (fails gates 1, 2, 7) |
| `tsmom` 30d | Momentum | same | 1d | 0.10 | -71.5% | 132 | 0.52 → -0.38 | **REJECT** |
| `donchian` 40/10 | Breakout | same | 1d | 0.03 | -51.6% | 39 | 0.19 → -0.16 | **REJECT** |
| `rsi2_dip` x=10 | Panic reversal | same | 1d | -0.15 | -37.4% | 80 | 0.33 → -0.69 | **REJECT** |
| `bollinger_revert_4h` k=3 | Intraday reversion | same | 4h | -1.17 | -33.6% | 25 | -0.73 → -1.61 | **REJECT** |

Per-coin detail, win rate, profit factor and deflated Sharpe are in `results/research.md`.

**What the numbers say:**
- The three trend strategies made money on train at every grid point (100% positive). On held-out they were weak, and SOL lost money with all of them.
- `trend_sma` on ETH was the one bright spot: Sharpe 0.84 vs 0.30 for holding, with drawdown cut from -67.5% to -42.3%. That is one coin out of three, which isn't enough to deploy.
- The two mean-reversion strategies lost money held-out even at near-zero costs. Those edges aren't there in this data.
- No pick's deflated Sharpe came close to 0.90 (the best was 0.029). With 105 trials, the best result expected by chance is a Sharpe of about 2.0, and the best real full-period result was about 1.3.
- **Cost is the deciding variable.** At 0.10% per side, `trend_sma` beats buy-and-hold on BTC (0.92 vs 0.63) and ETH (1.03 vs 0.30). At the fees a US entry-tier account pays, that advantage mostly goes away.

## 7. Deployed strategies

**None.** Under the rules ("trade only what survives rigorous validation"), the correct output of Gate 1 is to deploy nothing.

The risk engine below is still the spec any future candidate must run inside.

### Execution and risk spec (hard-coded, not model-overridable)

- **No model in the order path.** An LLM may write reports, but it never creates, sizes or approves orders. Orders come only from deterministic strategy code and must pass the `RiskGate` checks in order.
- **Position size:** at most 25% of the account per coin and 50% total. Size by volatility targeting, aiming for 20% annualized volatility per position. Never use full Kelly, and cap at quarter-Kelly if Kelly is ever used.
- **Daily loss limit:** -2% of equity, measured since 00:00 UTC. Hitting it flattens everything and blocks new entries until the next UTC day.
- **Max drawdown:** -10% from the equity peak. Hitting it triggers the kill switch and needs Caleb to re-arm by hand.
- **Stale data:** if the latest closed bar is more than 2 bars old, or the price moved more than 3× ATR between ticks with no confirmation from a second feed, block entries and alert.
- **API errors:** 3 consecutive errors, or 5 in 10 minutes, trigger a pause plus an alert. An order whose result is unknown gets reconciled against the account's order history before any retry, using idempotent client order IDs.
- **Orders:** post-only limit orders (maker fee) at the touch, cancel-and-replace twice, then skip the trade. Never send a market order on entry.
- **Catastrophe stop:** a resting stop on the exchange at 3× ATR(14), so a crash is caught even if the agent is down.
- **Kill switch:** `python -m agent.kill` cancels all orders and market-sells every position. It also works from a phone through a one-line flag file or a Telegram command. A test covers it.
- **Logging:** every decision is appended to a log with its inputs (bar time, prices, indicator values), its output (target), the risk checks that ran, and the order result.
- **Money movement:** the API key has no withdraw permission. Live trading only starts after Caleb signs off on a paper-trading record, and then at $100 or less.

## 8. Bear case

- **Overfitting:** the trend family looked perfect on 2019 to 2023 (every parameter worked) because that period held two huge bull runs. A single regime can make any long-biased rule look robust. Held-out results confirmed this.
- **Look-ahead:** guarded by tests. Remaining risk: Binance daily bars close at 00:00 UTC, while a US venue's "daily close" could differ. The live engine must compute its own bars.
- **Survivorship:** only coins that are still top-10 today were tested. SOL nearly went to zero in 2022 and survived; a basket picked in 2019 would have included coins that didn't.
- **Cost sensitivity:** confirmed as the main failure. Taker fees alone (0.80% to 0.90%) wipe out the edge.
- **Regime dependence:** long-only spot strategies can't make money in a falling market, only step aside. The current regime is risk-off on daily charts.
- **Crowding:** the 50- and 200-day averages are the most-watched levels in crypto, so any edge there is widely traded.
- **Liquidity traps:** not a problem at this size for BTC/ETH. It is a problem for SOL on a weekend gap.
- **Single points of failure:** one machine, one exchange, one data feed, one API key.
- **What live result proves a strategy broken (for future candidates):** any of the following triggers an automatic stop:
  - The 30-day rolling paper Sharpe falls below -1.
  - Drawdown exceeds 1.5× the worst held-out drawdown scaled to the position size.
  - Realized cost per trade runs more than 2× the modeled cost.
  - Fewer than half the expected trades happen over 60 days.

## 9. Build plan (AgenKit gates)

I couldn't open agenkit.xyz from this environment, and no web result confirmed what it is. So its phases are used here as approval gates, and no AgenKit commands are assumed.

| Gate | Deliverable | Status |
|---|---|---|
| 1. Spec | This document, the data loader, the backtester, the tournament, and tests | **Done, waiting for approval** |
| 2. Architecture | Module boundaries, the data-feed redundancy plan, and the venue decision (Kraken vs Coinbase) | Not started |
| 3. Plan | Test list for `RiskGate`, the kill switch, the order state machine, and reconciliation | Not started |
| 4. Test-first build | Risk engine first, then paper broker, then live adapter | Not started |
| 5. Review | Independent code review and a failure drill (pull the network mid-order) | Not started |
| 6. Ship | 60 days of paper trading, then a ≤ $100 live pilot, each with sign-off | Not started |

**Repo structure:**

```
trading-agent/
  SPEC.md              this file
  agent/
    data.py            candle loader + validation (built)
    indicators.py      no-look-ahead indicators (built)
    strategies.py      candidates + parameter grids (built)
    backtest.py        next-open fills, fees, slippage (built)
    metrics.py         Sharpe, drawdown, deflated Sharpe (built)
    risk.py            RiskGate: hard limits + kill switch (gate 4, built first)
    broker_paper.py    simulated fills against the live public book (gate 4)
    broker_live.py     exchange adapter, trade-only key (gate 6, needs approval)
    runner.py          the 24/7 loop: fetch → signal → risk → order → log
  research/run_research.py   strategy tournament (built)
  tests/               look-ahead, timing, cost, time-stop tests (built: 10 passing)
  results/             research.md / research.json (generated)
```

**First module to build after approval:** `agent/risk.py`, test-first. It needs a test for each limit in section 7, plus the kill switch.

**How to start paper trading:** there is nothing to paper-trade yet, because no strategy passed. Once one does, the command will be `python -m agent.runner --mode paper`.

**To reproduce this gate:**
```
cd trading-agent
pip install -r requirements.txt
python -m pytest -q
python -m research.run_research
```

## 10. Decision needed from Caleb

Pick one:

1. **Stop here.** Keep the backtester as a research tool and don't build an autonomous trader. This is the survival-first option, and the default if nothing is chosen.
2. **Fix costs first, then a new trial.** Register one new, separately counted candidate: `trend_sma` with volatility targeting on BTC and ETH only, filled with maker orders and costed at Kraken's 0.40% maker fee, judged against the same gates. If it passes, move on to Gate 2. If not, stop.
3. **Widen the search.** Add new candidates. The obvious ones (carry, perps) are blocked for US accounts. Every new idea raises the bar the deflated Sharpe test sets.

## HOW COULD THIS SYSTEM FAIL?

1. **The edge was never there.** This is already the main finding. The simple long-only rules that looked great from 2019 to 2023 didn't hold up from 2024 to 2026 after costs. Rerunning until something passes is exactly how overfitting happens, so every new trial is counted.
2. **Fees decide the outcome.** At US entry-tier taker fees (0.80% to 0.90%), every candidate is flat or negative. Fee schedules change without notice, and Coinbase doesn't publish its schedule openly.
3. **Research data ≠ trading venue.** The backtests use Binance USDT pairs; live trading would be on Coinbase/Kraken USD pairs. Small differences in bar times, prices and wicks change trend signals near the average.
4. **Weakest assumption:** that 2024 to 2026 is a fair test. It's under 3 years and mostly one regime (a high followed by a long slide). A strategy can fail here and work later, or the reverse.
5. **Feed or exchange failure.** With one data source, a frozen or bad price can create a false signal. The stale-data check and the catastrophe stop resting on the exchange are the defences. A down exchange means positions can't be exited, which is why position caps stay small.
6. **Operational failure.** Possible causes: a lost API key, a machine that sleeps, a clock that drifts, or an order that fills twice after a retry. The defences are a trade-only key, idempotent order IDs, reconciliation before retry, and a heartbeat alert to Caleb's phone.
7. **Human override.** The biggest live risk is re-arming the kill switch or raising limits after a loss. Limits live in code, and a change needs a commit that Caleb approves.
8. **Survival beats a good backtest.** A system that stays flat and keeps the account intact is a success compared with one that blows up on a rule that only worked in the past.
