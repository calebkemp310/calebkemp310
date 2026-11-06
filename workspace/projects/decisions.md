# Decisions

Format: `- YYYY-MM-DD: decision — reasoning`

- 2026-10-29: Built the screener as a single self-contained `index.html` — no build step, opens anywhere.
- 2026-11-01: Adopted structured memory folders (`memory/`, `workspace/`) + `CLAUDE.md` instructions — transparent, portable.
- 2026-11-01: Notion Memory is the shared brain across all Claude apps; repo folders hold repo-specific notes only — one memory, no duplicated work.
- 2026-11-06: Enabled the claude-code-plugins marketplace plugins in `.claude/settings.json` — `/plugin` doesn't work in cloud sessions.
- 2026-11-06: Added `.github/workflows/claude.yml` (@claude in issues/PRs) with `CVector-Energy/claude-code-memory` pinned to a commit SHA — CI runs keep Claude's auto-memory between runs; that cache is CI-only and doesn't replace Notion or the repo memory files.
