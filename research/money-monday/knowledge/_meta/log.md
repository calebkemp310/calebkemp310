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

## [2026-11-09] task | money-monday-checks Task 6 (analysis)
- `output/data-analysis/analyze.py` -> `output/data-analysis/results/results.json`
- Per-check Mann-Whitney (one-sided, Holm-corrected across 4 checks), n=301:
  - H1 low_float: median 0.0956 (pass) vs 0.0717 (fail), p_holm=0.180 -> REJECTED
  - H2 catalyst: median 0.0893 (yes) vs 0.1169 (no), p_holm=0.860 -> REJECTED (points the wrong direction, not just non-significant)
  - H3 former_runner: median 0.1130 vs 0.0845, p_holm=0.126 -> REJECTED (p_raw=0.042 looked promising but doesn't survive Holm correction)
  - H4 unusual_volume: median 0.1415 vs 0.0656, p_holm=1.5e-5 -> SUPPORTED, the only check that clears the bar
- Leave-one-out (4/4 group vs "3/4 missing X"): only 1 ticker ever graded a true 4/4, so every leave-one-out comparison is "insufficient_n" per the stop rule -- correctly not reported as a finding
- OLS regression did NOT run: it requires catalyst as a covariate, so it can only use the 92 non-excluded rows, below the pre-registered n>=100 threshold. This is a real limitation, not a bug: the catalyst check's 69% exclusion rate (Task 4) starves the regression. H5 is therefore marked "insufficient" rather than forced.
- Sensitivity run excluding stale_float (n=219): same story holds -- unusual_volume p_raw=0.0012 (still clearly significant), former_runner weakens further (p_raw=0.056), catalyst and low_float stay non-significant. Main finding is robust to the stale-float exclusion.
- Verdicts: H1 rejected, H2 rejected, H3 rejected, H4 supported, H5 insufficient (regression underpowered by catalyst exclusions)

## [2026-11-09] task | money-monday-checks Task 7 (cross-checks)
- `output/data-analysis/results/crosschecks.json`
- Cross-check 1 (Notion Trading Journal, `collection://2df10e8a-603c-49bb-aad5-3c7897250ceb`): NULL RESULT. All 8 real logged trades (RCT, INOx2, DBGI, CENNx2, VSA, VIVK) are dated 2026-11-06, a Friday, not a Monday -- none fall inside the study window. Reported as-is rather than papered over; contributes no evidence to H1-H5.
- Cross-check 2 (Tim Sykes newsletter, 2026-10-24 email naming 5 Monday runners): n=5, well below the plan's 10-per-group threshold, so reported only as a cherry-picked table per the plan's own instruction -- no hypothesis test run.
  - 2 of 5 (MNDR 2026-10-12, GRML 2026-09-21) matched exact dates already in the main dataset and were reused from features.csv/graded.csv.
  - 3 of 5 (WORX 2026-10-19, MI 2026-10-05, SOAR 2026-09-28) needed a fresh daily-bar pull (done directly, not via background subagent, since only 3 tickers were needed). MI and SOAR reused existing share snapshots from shares.csv; WORX's snapshot was pulled fresh and appended to shares.csv.
- **Deviation, logged per the plan's Deviations Log requirement:** catalyst was NOT blind-labeled for the 3 freshly-pulled cross-check tickers (WORX/MI/SOAR) -- no separate labeling subagent was dispatched for just 3 items, so their catalyst field is reported as `not_labeled` rather than guessed from the newsletter's own framing. This is a methodological narrowing (less complete than the main sample's labeling), not a result-affecting deviation, since cross-check 2 carries no hypothesis test.
- **Also noted in crosschecks.json:** the newsletter's self-reported % moves (e.g. WORX "+210%") do not match this study's pre-registered outcome metric (max gain from the open) and are shown side-by-side rather than reconciled -- they are likely measured from a different baseline (e.g. multi-day or close-to-close) than daily high/open.
- All premarket-volume checks for the 3 fresh tickers used the `prior_session` fallback (same as the May 11 rule), since these dates are far outside Webull's 180-day rolling minute-bar window.

## [2026-11-09] meta | money-monday-checks coverage deviation (24 of 25 trading Mondays)
- **Deviation, logged per the plan's own Verification requirement** ("graded.csv covers all 25 trading Mondays, or the gap is logged as a deviation"): `graded.csv` covers 24 of the 25 pre-registered trading Mondays (2026-05-11 through 2026-11-02). **2026-11-09 (today) is not included.**
- Reason: this entire research project (Tasks 1-7) was executed ON 2026-11-09, the last Monday of the pre-registered window, before that day's trading session had completed. The outcome metric (max gain from the open = daily high/open - 1) cannot exist for a session still in progress, and the day's Benzinga premarket movers posts were only beginning to publish as data collection started (per `input/notes/data-availability.md`, Task 1). Including a necessarily-incomplete final data point would have required guessing at an unresolved outcome, which the frozen rules do not permit.
- This is a scope-boundary deviation, not a data-quality one: n=301 across 24 Mondays already clears every pre-registered sufficiency threshold (Task 5/6), and dropping the one Monday that cannot yet have a resolved outcome does not bias the comparison between any check's pass/fail groups.

## [2026-11-09] knowledge | money-monday-checks Task 8 (synthesis)
- `knowledge/synthesis/money-monday-check-ranking.md` (status: review) -- Evidence base, results per hypothesis, check ranking, and "What stays open" sections per the plan's Task 8 spec
- Linked from `knowledge/_meta/index.md` to clear the orphan-page lint check
- `python scripts/lint-wiki.py` exits 0

## [2026-11-09] meta | money-monday-checks Caleb reviewed and approved
- Caleb reviewed `knowledge/synthesis/money-monday-check-ranking.md` and the findings artifact (https://claude.ai/artifact/4cbyAJT5CCava2ksfzndpi) and signed off
- Synthesis page frontmatter updated: `status: stable`, `reviewed_by: caleb`
- This clears the plan's final Verification item ("The synthesis page exists with status: stable after Caleb reviews it"). All other Verification items were already satisfied: lint-wiki.py exits 0; graded.csv covers 24/25 trading Mondays with the gap logged as a deviation; analyze.py reproduces results.json end to end; H1-H5 are each marked supported/rejected/insufficient.
- **money-monday-checks project is complete.** The proposed screener diff in the findings artifact (require unusual_volume as one of the 3-of-4 passing checks) remains unapplied, pending a separate decision from Caleb on whether to update `money-monday-screener/index.html`.
