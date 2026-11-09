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

## [2026-11-09] task | money-monday-checks Task 3 (market data pull)
- Premarket M5 bars: all 23 Mondays (2026-05-18 to 2026-11-02) returned real data, no dates aged out of Webull's 180-day window
- Daily bars: all 24 Mondays (incl. 2026-05-11) returned 31-bar history per ticker
- Share snapshots: 253 of 270 unique tickers resolved
- 17 tickers found delisted/invalid across the window: ALOT, AMPGR, ANY, BRNS, FTRK, GETY, GNTA, HCWC, JFB, LGLR, MIMI, RITR, SBEV, SNSE, VSME, VTAK, WALD -> `input/data/bars/invalid_symbols.txt`
- `output/data-analysis/features.py` built `input/data/features.csv`: 301 of 320 universe rows survived (19 skipped for tickers with zero daily bars, i.e. the above delisted set intersected with the universe)
- Spot-check: CLIK and HTCO (2026-05-11) both show `volume_basis=prior_session` per the pre-registered fallback; 14 rows total use that basis, exactly the May 11 Monday's universe size
- `stale_float` flagged on 82/301 rows (27%) via two proxies: Monday volume > 50x current share count, or 52-week high > 10x Monday's open (reverse-split signal). This is a conservative proxy for "offering/conversion/reverse split in the prior 30 days" since share snapshots alone don't carry that event history -- noted as a limitation for the synthesis write-up.
- `max_gain` (the outcome) is in its own column; grade.py (Task 5, next) must not read it.

## [2026-11-09] task | money-monday-checks Task 4 (catalyst labeling, blind)
- Background worker labeled all 301 features.csv rows against the frozen catalyst rule, blind to max_gain
- `input/data/news.csv` + `input/data/catalyst_labels.csv`: 301 rows each
- Labels: yes=64, no=28, excluded=209 (no pre-open news found at all)
- Method note: ticker-only news search rarely matched; company name (via get_instruments) was needed for most lookups
- High exclusion rate (69%) reflects thin news coverage for micro/nano-cap gappers generally, not a search failure -- consistent with Task 1's finding that older Mondays' news is hard to find
- "no" labels: exclusion-category items (offerings, financings, Nasdaq compliance notices, buybacks, analyst-rating-only, 13F disclosures, competitor news) correctly kept out of "yes" per the frozen rule

## [2026-11-09] task | money-monday-checks Task 5 (grading)
- `output/data-analysis/grade.py` run against real labels -> `input/data/graded.csv`, 301 rows
- Grade distribution: A=1, B=29, FAIL=271 (271 includes the 209 catalyst_excluded rows, which cannot score A/B under the pre-registered rule)
- Stop-rule check: every check's pass/fail group has >=10 names (smallest: catalyst-no at 28), so no hypothesis is "insufficient data" on sample size alone
  - low_float: True=263, False=38
  - catalyst (n=92 non-excluded): yes=64, no=28
  - former_runner: True=49, False=252
  - unusual_volume: True=102, False=199
  - stale_float flagged: 82/301
- n=301 overall clears the n>=100 threshold for the regression in Task 6
