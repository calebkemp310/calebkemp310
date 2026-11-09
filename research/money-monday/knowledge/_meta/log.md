---
title: "Wiki Log"
type: synthesis
created: 2026-04-15
updated: 2026-04-15
status: review
author: llm
---

# Wiki-Log

## [2026-04-15] meta | Projekt initialisiert
- Ordnerstruktur angelegt
- Schema-Dokument (CLAUDE.md) erstellt
- Index und Log initialisiert

## [2026-11-09] plan | money-monday-checks
- Design approved by Caleb: `input/ideas/money-monday-checks-design.md`
- Plan written: `input/ideas/money-monday-checks-plan.md` (status: draft, awaiting pre-registration sign-off)
- Correction: May 11 to Nov 9, 2026 holds 27 Mondays (the design said 26); 25 are trading days after Memorial Day and Labor Day. Window unchanged.

## [2026-11-09] meta | money-monday-checks pre-registered
- Caleb confirmed H1-H5, falsification criteria and stop rule. Plan status: pre-registered. Any later change is logged here as a deviation.

## [2026-11-09] task | money-monday-checks Task 1 (feasibility probe)
- Notes: `input/notes/data-availability.md`
- Universe posts + daily bars available across the window; full article HTML parseable
- Premarket M5 limited to the last 180 days (rolling): May 11 uses the pre-registered prior-session fallback; remaining Mondays must be pulled this week
- Catalyst news for older Mondays not reliably reachable: handling of "no news found" needs a decision before Task 4
- 2026-11-09 · deviation · plan=money-monday-checks · Catalyst check: a ticker with no pre-open news found in Webull is EXCLUDED from the catalyst comparison (H2) only, not counted as "no catalyst". The excluded count is reported. Chosen by Caleb before any catalyst labelling; H2 results are reported with this caveat.
