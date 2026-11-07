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
