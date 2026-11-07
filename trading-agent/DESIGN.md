# Paper Trading Design (Gates 2 + 3: Architecture and Test Plan)

_Status: **built (Gate 4)**. Caleb approved the limits, GitHub alerts and the build on 2026-11-07. The paper trader starts hourly once this is on `main`. No code in this repo can place an order, and the paper trader will never hold an API key._
_Strategy under test: `vol_target_trend` (SMA50, 30% vol target) on BTC-USD and ETH-USD. Why this one: SPEC.md section 11._

## 1. What the paper phase is for

The backtest can't prove the edge; it passed 6 of 7 gates and failed the luck test. The paper phase answers a narrower question first:

> **Does the live system do exactly what the backtest says it would, at the costs the backtest assumed?**

Over 90 days the strategy will make only about 5 or 6 trades, so paper P&L is reported but is **not** a pass/fail criterion. The pass/fail criteria are the tracking checks in section 9. Right now both BTC and ETH are below their 50-day average, so the paper book will most likely start flat in cash. That's expected behaviour.

## 2. Two checks that shaped this design (run 2026-11-07)

| Check | Result | Design consequence |
|---|---|---|
| Coinbase USD vs Binance USDT daily closes, Oct 2022 to Nov 2026 (1,495 days) | Median close gap 0.035%, 99th percentile 0.24%. SMA50 signal agreed on all but 1 day since 2024, for both BTC and ETH | Coinbase can be the primary feed (it's the venue's own price). Binance is the cross-check |
| Risk limits replayed on the backtest, 25% per coin (section 7 cap), 2019 to 2026 | Worst drawdown -18.8%; below -10% on 27% of days; a -10% kill would have fired in 6 of 8 years. Daily loss beyond -2% about 5.5 times a year, beyond -3% about 1.9 a year, worst day -6.9% | The section 7 drawdown kill (-10%) would stop the strategy during normal behaviour. **Proposed change in section 6, needs approval** |

## 3. Where it runs

**GitHub Actions on a schedule**, in this repo. It's free, needs no computer of Caleb's to stay on, and every run is logged.

- **Cron every hour** (`7 * * * *`). Each run is **idempotent**: it processes any daily bar that has closed but hasn't been handled yet. A delayed or skipped run is simply caught up by the next one, which matters because GitHub cron can be late or drop runs under load.
- `concurrency: paper-trader` so two runs can never overlap.
- **State and logs live on a separate `paper-trading` branch**, so `main` doesn't get a commit every hour. Each run checks out that branch, does its work, and commits `state.json` and the ledger.
- **No secrets.** It only reads public market data, and the workflow's token only has permission to push to the `paper-trading` branch and comment on one issue.
- **Known risk:** GitHub disables scheduled workflows in repos with no activity for 60 days. The daily state commits should count as activity. The heartbeat check (section 8) catches it if they don't.

Rejected options: Caleb's PC (sleeps, Windows updates), a paid VPS (cost, and a server to secure), and a Claude routine (an LLM would sit in the decision loop, which the spec forbids).

## 4. Components

```
trading-agent/agent/
  config.py         frozen dataclass of every limit; changes need a commit + review
  feeds.py          CoinbaseFeed (primary), BinanceFeed (cross-check): daily + hourly candles, best bid/ask
  signal.py         target_weights(candles) -> {coin: weight}; calls the SAME vol_target_trend as the backtest
  risk.py           RiskGate.check(state, intents, market) -> approved orders + rejections with reasons
  broker_paper.py   PaperBroker: simulated fills (maker + pessimistic taker), fees, positions
  ledger.py         append-only JSONL of every decision, check, order and fill
  state.py          state.json: cash, positions, peak equity, last processed bar, armed flag, error counts
  runner.py         one idempotent cycle (section 5); exit code != 0 on any unhandled error
  kill.py           flatten everything, set armed=false, write the reason
  report.py         daily summary + tracking metrics (section 9)
.github/workflows/paper-trader.yml   hourly schedule + manual "run" / "kill" buttons
```

Rules that hold everywhere:
1. **No LLM in this path.** Every decision is deterministic code.
2. **The strategy code is shared, not copied.** `signal.py` imports `agent.strategies.vol_target_trend`, so paper and backtest can't drift apart.
3. **The broker is an interface.** `broker_live.py` would later implement the same methods behind its own approval gate. The runner and RiskGate stay unchanged.

## 5. One run, step by step

```
start
 ├─ load state.json  (corrupt or missing → abort, alert, do nothing)
 ├─ KILL file present or armed=false? → kill.py (flatten, alert), stop
 ├─ fetch hourly + daily candles from Coinbase; best bid/ask
 ├─ validate: OHLC sane, no gap, last closed bar not stale
 ├─ cross-check last close vs Binance (|gap| ≤ 1%)          ── fail → freeze (no new orders), alert
 ├─ mark to market; update peak equity, daily P&L
 ├─ hourly risk checks: catastrophe stop, daily loss, drawdown ── breach → act per section 6
 ├─ new daily bar closed and not yet processed?
 │    ├─ no  → write heartbeat, commit, stop
 │    └─ yes → target_weights() → order intents (target - current)
 │              → RiskGate.check() → PaperBroker.fill(approved)
 │              → ledger: inputs, signal, every check + reason, fill, costs
 │              → state.last_processed_bar = that bar
 ├─ report.py → daily summary (once per UTC day)
 └─ commit state + ledger to paper-trading branch
```

**Timing.** The backtest fills at the daily open (00:00 UTC). The paper trader fills at the first run after that, around 00:07 UTC. The gap between that fill price and the daily open is measured on every trade (section 9).

## 6. Risk limits

All limits are hard-coded in `config.py`. The RiskGate is a pure function `(state, intents, market) → decisions`, so every rule is unit-testable. Checks run in this order and stop at the first failure:

| # | Check | Limit | On breach | Changed from SPEC §7? |
|---|---|---|---|---|
| 1 | Armed / KILL file | armed=true, no `trading-agent/KILL` file | Flatten, stop, alert | same |
| 2 | Data freshness | Last closed daily bar ≤ 26h old; hourly price ≤ 2h old | Freeze (no new orders), alert | same idea; numbers made concrete |
| 3 | Feed agreement | Coinbase vs Binance close within 1% | Freeze, alert | **new** |
| 4 | API error budget | 3 consecutive or 5 per 24h fetch failures | Freeze, alert; resumes after 1 clean day | same |
| 5 | Daily loss | -3% of equity since 00:00 UTC | Block new entries until next UTC day, alert. **Don't flatten**: the strategy's own exit handles trend breaks | **changed** (was -2% and flatten): -2% would have fired about 5.5 times a year in normal behaviour |
| 6 | Drawdown kill | -25% from peak equity | Flatten, armed=false; Caleb re-arms by hand | **changed** (was -10%): -10% fired in 6 of 8 years; -25% is about 1.3× the worst backtest drawdown at this size |
| 7 | Position caps | ≤ 25% of equity per coin, ≤ 50% total | Clip the order to the cap | same |
| 8 | Order sanity | Price within 2% of last trade; quantity ≥ venue minimum; notional ≤ cap; no more than 1 entry per coin per day | Reject, alert | **new** |
| 9 | Catastrophe stop | Hourly close ≤ entry − 3×ATR(14) | Exit that coin at next run | same |

**Position sizing.** Each coin is a sleeve capped at 25%. The sleeve's weight is `min(1, 0.30 / 30-day realized vol)` × 25%, fixed at entry, exactly as in the backtest. The backtest replay at this size: Sharpe 1.24, CAGR 19.4%, worst drawdown -18.8% (2019 to 2026); held-out 2024+ drawdown -11.7%. These are backtest figures, not a forecast.

**Strategy-broken stops** (from SPEC §8). Any of these triggers a kill:
- 30-day rolling Sharpe < -1 once 60+ days of data exist.
- Drawdown beyond the -25% kill.
- Realized cost per trade more than 2× the modeled cost.
- Fewer than half the expected trades over 60 days, which points to a signal or data bug rather than the market.

## 7. Paper fills (honest, bracketed)

A paper fill can't know whether a real limit order would have filled, so every trade is recorded **two ways**:

| Model | Price | Fee | Meaning |
|---|---|---|---|
| Maker (base) | Best bid (buy) or best ask (sell) at decision time | 0.40% (Kraken entry maker; Coinbase ~0.50%) | Patient limit order that fills |
| Taker (pessimistic) | Best ask (buy) or best bid (sell) + 0.05% | 0.90% (Coinbase entry taker) | Market order |

The book's equity follows the maker model. Both models, and the backtest's next-open price, go in every ledger line, so the tracking report shows the real cost range.

**Order states** are already modeled the way the live adapter will need them: `NEW → SUBMITTED → FILLED | CANCELLED | REJECTED | UNKNOWN → RECONCILED`. In paper mode every order goes `NEW → FILLED` or `REJECTED`. The live adapter must also handle `UNKNOWN`: it reconciles against exchange order history before any retry, using idempotent client order IDs.

## 8. Alerts and the kill switch

- **Kill from a phone:** add a file named `KILL` in `trading-agent/` using the GitHub app, or press the workflow's "kill" button. The next hourly run flattens and stops. To re-arm, delete the file and set `armed: true` in `state.json`, both by commit.
- **Alerts:** each run comments on one pinned issue, "Paper trading log", for trades, freezes, limit hits and kills. The GitHub app notifies the phone. A failed run also emails the repo owner (GitHub default).
- **Heartbeat:** the daily report includes "last successful run". If no run has succeeded in 26h, the next run that does work opens an alert. For the case where nothing runs at all, a weekly Claude routine checks the branch's last commit date and messages Caleb. It only reads, never trades.

## 9. When paper trading passes

After **at least 90 days**:

| Criterion | Pass if |
|---|---|
| Signal match | Replaying the backtest on Coinbase candles over the paper window gives the **same** entry and exit days (100% match) |
| Fill tracking | Median gap between the maker paper price and the backtest's next-open price ≤ 0.30%; worst ≤ 1% |
| Cost tracking | Average modeled round-trip cost within 2× of 0.65% per side |
| Reliability | No gap > 26h between successful runs; zero unhandled exceptions in the last 30 days; every freeze explained |
| Risk engine | Every limit fired in a drill (section 10) and behaved as specified |
| P&L | Reported, compared with the backtest over the same window. **Not** a pass criterion (too few trades) |

Passing unlocks a request to start the live pilot (≤ $100, trade-only API key, no withdrawals), which needs its own approval.

## 10. Failure modes and defences

| Failure | Defence | Test / drill |
|---|---|---|
| Coinbase returns stale or frozen candles | Freshness check, freeze | Feed a fixture with the last bar 30h old |
| Coinbase and Binance disagree (bad print, outage) | 1% agreement check | Fixture with a 5% gap |
| Exchange or API down for hours | Error budget, freeze, catch-up on recovery | Fetch mocked to raise 3 times |
| GitHub cron delayed or skipped | Hourly + idempotent catch-up | Run twice for the same bar → one decision; skip 5 hours → one decision |
| Two runs overlap | `concurrency` group; state version check before commit | Simulated conflicting commit → second run aborts |
| state.json corrupt | Schema + checksum; abort without acting | Truncated-file fixture |
| Strategy code drifts from backtest | Shared function + signal-match replay | Test: paper signal on history == backtest signal |
| Flash crash between daily runs | Hourly catastrophe stop | Fixture with an hourly bar -20% |
| Bug sizes an order 10× too big | Position caps + order sanity | Intent with 10× notional → clipped or rejected |
| Kill switch ignored | Checked first, every run | KILL file present → flatten, no other orders |
| Scheduled workflow disabled after 60 days | Daily commits + weekly heartbeat routine | Manual: disable workflow, confirm the heartbeat alert |
| Someone loosens limits after a loss | Limits only in code; change = reviewed commit | Review checklist item |

## 11. Test plan (written first, before each module)

**`risk.py`**
- One test per row of the section 6 table: each limit at, just inside and just outside its threshold.
- Check order: a KILL file beats every other check.
- Daily loss blocks entries but still allows exits.
- Drawdown kill sets armed=false and flattens.
- Caps clip rather than reject when partial room is left.
- Pure function: the same inputs always give the same output.

**`broker_paper.py`**
- Maker and taker fills use the right side of the book and the right fee.
- Positions and cash reconcile after buy → sell.
- Rejects zero or negative quantities.
- Equity marks match a hand calculation.

**`signal.py`**
- Equals `vol_target_trend` on the full history.
- No look-ahead (reuses the existing future-perturbation test).
- Weights are within [0, 0.25].

**`feeds.py`** (recorded fixtures, no network in tests)
- Parses Coinbase and Binance responses.
- Drops the still-forming bar.
- Detects gaps and staleness.
- Retries with backoff, then raises.

**`state.py` / `ledger.py`**
- Round trip.
- Checksum catches corruption.
- Ledger is append-only (never rewrites).
- Restart mid-run doesn't double-trade.

**`runner.py`** (end to end on fixtures)
- Idempotent per bar.
- Catch-up after missed runs.
- Freeze paths.
- Kill path.
- A full simulated 120-day replay matches the backtest's trade days exactly.

**`kill.py`**
- Flattens everything.
- Leaves armed=false.
- Writes the reason to the ledger and issue.

**Drills before day 1:**
- Run the kill switch from the phone.
- Make the feed go stale.
- Corrupt state.json.
- Disable the workflow and confirm the alert.

## 12. Build order (Gate 4, after approval)

1. `config.py` + `risk.py` (test-first).
2. `state.py` + `ledger.py`.
3. `broker_paper.py`.
4. `feeds.py` with recorded fixtures.
5. `signal.py`.
6. `runner.py` + `kill.py` + `report.py`.
7. The workflow on the `paper-trading` branch.
8. The drills.
9. Day 1 of the 90.

The paper trader starts with a virtual $10,000 book (any size works, since results are reported in %).

## 13. Decisions needed from Caleb

All three approved by Caleb on 2026-11-07: the limit changes, GitHub issue alerts, and the Gate 4 build.

**Build notes (differences from the plan above):**
- The secondary cross-check tries Binance first, then Kraken. If neither answers, it's counted as a data error rather than a disagreement.
- If the trend is still up after a catastrophe stop, the coin isn't re-entered until the signal goes flat once. The backtest has no stop, so tracking reports mark those days "n/a (stop/kill)".
- The weekly summary is posted on Mondays.
- The heartbeat routine for "no runs at all" is set up after merge, because GitHub only schedules workflows that are on `main`.
