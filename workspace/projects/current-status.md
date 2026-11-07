# Current Status

_Last updated: 2026-11-07_

- Money Monday Screener: first version merged (PR #1). No open follow-ups recorded yet.
- Memory system: repo folders merged (PR #2); now linked to Notion Memory as the shared brain.
- Plugins: marketplace plugins enabled (PR #4).
- Skills: marketing/design/writing plugins enabled (PR #7, merged). Bump the pinned tags in `.claude/settings.json` to update them. Repo list + Kronos trial notes live in Notion.
- Cloud environment: "calebkemp310 (Hugging Face access)" adds Hugging Face + PyTorch downloads for this repo's sessions.
- Claude GitHub workflow: added; needs the `CLAUDE_CODE_OAUTH_TOKEN` repo secret before it can run.
- Trading agent: Gate 1 + Round 2 done (`trading-agent/SPEC.md` section 11). Best = `vol_target_trend` (WATCH, fails luck test only). Paper trader built (Gate 4); goes live hourly once merged to main. Next: drills (kill from phone, stale feed), weekly heartbeat routine, then 90+ days of paper tracking.
- Cloud environment now also allows data-api.binance.vision, data.binance.vision, api.exchange.coinbase.com, api.coinbase.com.
