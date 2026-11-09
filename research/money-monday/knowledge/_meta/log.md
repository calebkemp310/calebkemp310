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

## [2026-11-09] task | money-monday-checks Task 2 (universe build)
- `input/data/posts.csv`: 92 unique Benzinga movers posts across 24 Mondays (2026-05-11 to 2026-11-02)
- `output/data-analysis/build_universe.py`: fetches/caches article HTML, parses Gainers mentions, filters gap>=10% and price<$20, de-dupes on (date,ticker)
- `input/data/universe.csv`: 320 rows, 6-19 names per Monday (median ~14)
- Spot-check passed: CLIK (78.0%, $3.97) and HTCO (17.8%, $6.88) from the May 11 Industrials post
- Coverage gap: each Monday has 3-5 of ~6-8 possible sector posts (search_news returns no pagination key); not exhaustively gap-filled given the Task 3 time pressure (180-day minute-bar window). The universe is biased toward the largest movers per sector, as already stated in the design doc.
- 1 post (the May 11 general "20 Stocks Moving Premarket" roundup) has a different, unparsed format; that Monday is already covered by 4 sector posts, so not fixed.
- Task 3 (premarket bars, daily bars, share counts) dispatched to a background worker; results to follow.
