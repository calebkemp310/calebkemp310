# Decisions

Format: `- YYYY-MM-DD: decision — reasoning`

- 2026-10-29: Built the screener as a single self-contained `index.html` — no build step, opens anywhere.
- 2026-11-01: Adopted structured memory folders (`memory/`, `workspace/`) + `CLAUDE.md` instructions — transparent, portable.
- 2026-11-01: Notion Memory is the shared brain across all Claude apps; repo folders hold repo-specific notes only — one memory, no duplicated work.
- 2026-11-06: Enabled the claude-code-plugins marketplace plugins in `.claude/settings.json` — `/plugin` doesn't work in cloud sessions.
- 2026-11-06: Added `.github/workflows/claude.yml` (@claude in issues/PRs) with `CVector-Energy/claude-code-memory` pinned to a commit SHA — CI runs keep Claude's auto-memory between runs; that cache is CI-only and doesn't replace Notion or the repo memory files.
- 2026-11-06: Enabled marketing-skills, ui-ux-pro-max, taste-skill and humanizer plugins, each pinned to a release tag, plus stop-slop copied into `.claude/skills/` (it has no plugin manifest) — for Momentum store copy, SEO and page design. Reviewed hooks/MCP/install scripts first. Skipped claude-seo: Claude Code rejects its reserved "claude-" plugin name; marketing-skills covers SEO.
- 2026-11-07: Trading agent research uses Binance spot candles (data-api.binance.vision) as a proxy; live venue must be US (Kraken Pro / Coinbase Advanced). Binance doesn't serve US residents.
- 2026-11-07: Seven pass/fail gates (held-out Sharpe, per-coin Sharpe, drawdown vs hold, grid robustness, 2x cost, trade count, deflated Sharpe) fixed in `research/run_research.py` before results; never edit them to rescue a strategy, and count every new trial.
- 2026-11-07: Gate 1 rejected all 5 candidates; the main killer is US entry-tier fees (0.4-0.9% per side). No LLM in the order path, ever.
- 2026-11-07: Round 2 candidates pre-registered in commit 6e0a950 before running; deflated Sharpe pools all trials across rounds. Fixed weekly-bar scoring bug (daily clock now forward-filled) after the first round-2 run, disclosed in SPEC section 11.
- 2026-11-07: Paper trader design: GitHub Actions hourly + idempotent per daily bar, no secrets, state on a `paper-trading` branch, Coinbase primary feed (99.9% SMA50 signal agreement with Binance since 2024), Binance cross-check. Paper is judged on tracking (signal match, fill gap, reliability), not P&L.
- 2026-11-07: Caleb approved limits (daily -3% block-only, DD kill -25%), GitHub issue alerts, and the Gate 4 build. Paper trader secondary cross-check: Binance then Kraken; a missing secondary counts as a data error, not a disagreement. No re-entry after a catastrophe stop until the trend signal resets.
