---
title: "Which Money Monday check best predicts a bigger Monday move in small-cap gappers?"
type: plan
created: 2026-11-09
updated: 2026-11-09
status: draft
author: mixed
design: "[[money-monday-checks-design]]"
---

# Money Monday checks — Research Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `research-superpowers:executing-research-plan` to run this plan task by task. Tasks use checkbox (`- [ ]`) syntax for TodoWrite integration.

**Research Question:** Over the 27 Mondays from May 11 to Nov 9, 2026, among US stocks under $20 that gapped up ≥10% premarket or at the open, does passing each Money Monday check go with a larger max gain from the open? Which check adds the most once the other three are known? The checks are low float, catalyst, former runner and unusual volume.

**Hypotheses (pre-registered, immutable once confirmed).** No check is favoured; all four are tested on equal terms.
- **H1 (low float):** gappers that pass have a higher median max gain from the open than those that fail.
- **H2 (catalyst):** same, for the catalyst check.
- **H3 (former runner):** same, for the former-runner check.
- **H4 (unusual volume):** same, for the unusual-volume check.
- **H5:** the four checks differ in effect size, so the ranking reflects real differences, not noise.

**Falsification Criteria:**
- H1–H4: a check's hypothesis is rejected when its pass-group median is at or below its fail-group median, or when the one-sided Mann-Whitney U test gives p ≥ 0.05 after Holm correction across the four checks.
- If the regression runs (n ≥ 100), a check is also rejected when its coefficient's 95% CI includes 0.
- H5 is rejected if all four regression coefficients' 95% CIs overlap. Without the regression, H5 is rejected if the four Hodges-Lehmann shift estimates' 95% CIs all overlap.

**Stop Criterion:**
- Data covers exactly the 27 Mondays from May 11 to Nov 9, 2026. No Mondays are added or dropped to change a result. Holidays: May 25 (Memorial Day) and Sep 7 (Labor Day) are market closures and are logged as such, leaving 25 trading Mondays.
- A check with fewer than 10 names in its pass or fail group is reported as **insufficient data** for that hypothesis, not as a finding.

**Outcome:** max gain from the open = (daily high ÷ daily open) − 1, from Webull daily bars on the Monday itself.

**Method:**
- Grade every gapper in the universe on four frozen, mechanical rules that use only pre-open information.
- Compare the outcome between pass and fail groups for each check (medians, one-sided Mann-Whitney, Holm correction).
- Compare the 4/4 group with each "3/4 missing check X" group (leave-one-out).
- With n ≥ 100, fit OLS of log(1 + max gain) on the four flags with Monday fixed effects and HC3 robust errors.
- Sensitivity run: exclude names whose float is flagged stale.

**Output target:** other (findings artifact + proposed screener rule edits)
**Language:** en

---

## Frozen grading rules (copied from the design)

- **Low float:** Webull outstanding shares < 90M. The count is flagged *stale* if one day's volume exceeds 50× it, or an offering, conversion or reverse split happened in the prior 30 days.
- **Catalyst:** company-specific positive news published in the 24 hours before 9:30 ET: a launch, partnership, contract, earnings, deal or FDA event. Offerings, related-party deals, compliance or listing notices, and lawsuits don't count. Each item is labelled from its headline and summary with outcome columns hidden.
- **Former runner:** at least one day of +50% or more in the prior 30 sessions, measured close to close or as intraday high vs prior close. The latest pre-Monday close must be no more than 50% below that spike's high.
- **Unusual volume:** premarket volume (04:00–09:30 ET) ≥ 5× the 30-session average daily volume. If premarket bars are unavailable, the prior session's volume is used against the same average, and the row is marked `volume_basis=prior_session`.
- **Grade:** A = 4/4. B = 3/4 including the catalyst. FAIL otherwise.

## Data Sources

- **Universe:** Benzinga "Stocks Moving In Monday's Pre-Market Session" and "…Intraday Session" posts, via Webull `search_news`. *Availability unverified; Task 1 checks it.*
- **Per-ticker data:** Webull `get_stock_bars` (daily, plus M5 with `trading_sessions=PRE`), `get_stock_snapshot` (share counts) and `get_stock_news` (catalysts). *Available live; history depth to be checked in Task 1.*
- **Cross-check 1:** Notion Trading Journal, Trades database `collection://2df10e8a-603c-49bb-aad5-3c7897250ceb`. *Accessible.*
- **Cross-check 2:** Gmail newsletter emails from Tim Sykes and Tim Bohen that name Monday runners. *Accessible.*

## Tasks

### Task 1: Feasibility probe (one Monday, Nov 2, 2026)
**Files:** `input/notes/data-availability.md`

- [ ] Run `search_news` for the Nov 2 Benzinga movers posts and record whether they're found and how many tickers they list
- [ ] Repeat the search for May 11, 2026 to test the far end of the window
- [ ] For 3 tickers from each date, record whether daily bars, premarket M5 bars and pre-open news come back
- [ ] Write the findings to `input/notes/data-availability.md`. If the window can't be covered, stop and log a deviation before Task 2

### Task 2: Build the universe
**Files:** `output/data-analysis/build_universe.py`, `input/data/universe.csv`

- [ ] For each of the 25 trading Mondays, collect tickers from the movers posts with gap ≥10% and price < $20
- [ ] Write `universe.csv` (columns: `date, ticker, gap_pct, prev_close, source_post_id`) and de-duplicate on `(date, ticker)`
- [ ] Log the row count per Monday in `input/notes/data-availability.md`

### Task 3: Pull market data and features
**Files:** `output/data-analysis/pull_bars.py`, `input/data/bars/`, `input/data/features.csv`

- [ ] Save each ticker's 31 daily bars ending on the Monday to `input/data/bars/<date>_<ticker>.json`
- [ ] Save premarket M5 bars where available
- [ ] Write `features.csv` (columns: `date, ticker, shares_out, stale_float, pm_volume, avg_vol_30, volume_basis, max_runup_30, drawdown_from_spike, open, high`)
- [ ] Compute `max_gain = high / open - 1` in a separate column, outside any grading code

### Task 4: Label catalysts blind
**Files:** `input/data/news.csv`, `input/data/catalyst_labels.csv`

- [ ] Write each ticker's news from the 24 hours before the open to `news.csv` (columns: `date, ticker, publish_time, title, summary`)
- [ ] Label each row `catalyst=yes|no` with a one-line reason in `catalyst_labels.csv`, with no outcome columns loaded during labelling

### Task 5: Grade
**Files:** `output/data-analysis/grade.py`, `input/data/graded.csv`

- [ ] Apply the frozen rules to `features.csv` and `catalyst_labels.csv`
- [ ] Write `graded.csv` (columns: the four pass/fail flags, `stale_float`, `grade`, `max_gain`)
- [ ] Spot-check 10 random rows by hand against the rules

### Task 6: Analyze
**Files:** `output/data-analysis/analyze.py`, `output/data-analysis/results/results.json`

- [ ] For each check: pass/fail medians, the one-sided Mann-Whitney test, Holm-adjusted p-values, Hodges-Lehmann shift and its 95% CI
- [ ] Leave-one-out: the 4/4 group against each "3/4 missing X" group, with group sizes
- [ ] If n ≥ 100: OLS of log(1+max_gain) on the four flags with Monday fixed effects and HC3 errors
- [ ] Sensitivity run excluding `stale_float=true`
- [ ] Mark each of H1–H5 as `supported | rejected | insufficient` in `results.json`

### Task 7: Cross-checks
**Files:** `output/data-analysis/results/crosschecks.json`

- [ ] Grade Caleb's journal trades on Mondays in the window with the same rules, and summarize their outcomes
- [ ] Grade the newsletter-named Monday runners the same way and report them separately as a cherry-picked set

### Task 8: Synthesis page
**Files:** `knowledge/synthesis/money-monday-check-ranking.md`

- [ ] Sections: Evidence base (sample size per Monday, data gaps), results per hypothesis, the check ranking, and What stays open
- [ ] Run `python scripts/lint-wiki.py` and fix it to green

### Task 9: Findings page and screener proposal
**Files:** an Artifact page, plus the proposed diff to `money-monday-screener/index.html` (not applied)

- [ ] Publish a findings artifact that ranks the checks, with group sizes and the caveats
- [ ] Propose rule edits to the screener for Caleb's approval

## Verification

The project is complete when:
- [ ] `python scripts/lint-wiki.py` exits 0
- [ ] `graded.csv` covers all 25 trading Mondays, or the gap is logged as a deviation
- [ ] `analyze.py` reproduces `results.json` end to end from the CSVs
- [ ] Each of H1–H5 is marked supported, rejected or insufficient
- [ ] The synthesis page exists with `status: stable` after Caleb reviews it

## Deviations Log

Append to `knowledge/_meta/log.md`, referencing `money-monday-checks`, whenever scope, method or data sources change after pre-registration. A result reached after a deviation is labelled exploratory.
