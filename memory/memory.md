# Agent Memory — calebkemp310/calebkemp310

> Personal context, preferences and cross-project memory live in **Notion Memory**
> (fetch id `"memory"`). This file covers this repo only.

## Current Project
- Name: Money Monday Screener
- Description: Single-page HTML premarket stock screener / worksheet for Webull (`money-monday-screener/index.html`)
- Status: active

## Trading Agent (`trading-agent/`)
- 24/7 crypto agent built gate by gate with Caleb's approval. Gate 1 (spec + strategy tournament) is done; see `trading-agent/SPEC.md`
- Gate 1 result: all 5 candidates REJECTED on held-out 2024 to 2026 data, so nothing is deployed and no order code exists
- Round 2 (widened search, 184 pooled trials): `vol_target_trend` (SMA50, 30% vol target) passes 6 of 7 gates, failing only deflated Sharpe, so it's WATCH, a risk overlay rather than proven alpha. Paper trader built (Gate 4): `agent/runner.py` + `.github/workflows/paper-trader.yml`, hourly, state/ledger/report on the `paper-trading` branch, alerts in the "Paper trading log" issue, KILL file or workflow kill/rearm. Limits: -3% daily (block only), -25% DD kill
- Dashboard: `paper-trader-dashboard/index.html` shows health, equity, positions, signals, curve, trades, tracking, alerts (read-only)

## Key Decisions
- See `workspace/projects/decisions.md`

## User Preferences
- Code: `workspace/preferences/coding-style.md`
- Communication: Notion Memory → "Communication and Notion preferences"

## Important Context
- This is Caleb's GitHub profile repo — `README.md` renders on his profile.
