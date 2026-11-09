---
title: "Which Money Monday check best predicts a bigger Monday move?"
type: synthesis
created: 2026-11-09
updated: 2026-11-09
status: stable
reviewed_by: caleb
author: llm
---

# Which Money Monday check best predicts a bigger Monday move?

## Research question

Over the Mondays from May 11 to Nov 9, 2026, among US stocks under $20 that
gapped up ≥10% premarket or at the open, does passing each of the four Money
Monday checks (low float, catalyst, former runner, unusual volume) go with a
larger max gain from the open? Which check adds the most once the other
three are known?

## Evidence base

- **n = 301** gapper rows across **24 of the 25 pre-registered trading
  Mondays** (2026-05-11 to 2026-11-02). 2026-11-09 is not included because
  that day's session was still in progress while this project ran; see the
  coverage-deviation log entry in `knowledge/_meta/log.md`.
- **Universe:** built from 92 cached Benzinga "Stocks Moving In Monday's
  Pre-Market Session" article pages (`input/data/universe.csv`), gap ≥10%,
  price <$20, de-duped on (date, ticker). Coverage is partial by design: each
  Monday surfaces 3-5 of roughly 6-8 possible sector posts (Benzinga's search
  has no pagination), so the universe is biased toward the largest movers per
  sector, not every gapper that day. This bias was stated in the design doc
  before data collection, not discovered afterward.
- **17 tickers** were found delisted/invalid (`invalid_symbols.txt`) and
  dropped rather than silently excluded.
- **Catalyst coverage gap:** of 301 rows, **209 (69%) have no pre-open news
  findable at all** and are `catalyst_excluded` — excluded from the catalyst
  comparison only (H2), per Caleb's pre-registered choice (logged as a
  deviation before Task 4 labeling began). Of the 92 remaining, 64 were
  labeled `yes` and 28 `no`.
- **stale_float** (a conservative proxy for "an offering/conversion/reverse
  split happened recently," since point-in-time share snapshots carry no
  event history) is flagged on 82/301 rows (27%).
- **Premarket volume** mostly comes from real 04:00-09:30 ET minute bars;
  only 2026-05-11 uses the pre-registered `prior_session` fallback, because
  Webull's 180-day rolling window had already aged that date's minute bars
  out by the time Task 3 ran.
- **Group sizes clear the pre-registered ≥10-per-group floor on every check**
  (smallest: catalyst-no at 28), so none of H1-H4 is "insufficient data" for
  sample-size reasons alone. The regression behind H5 is the exception — see
  below.
- **Cross-checks (Task 7, `output/data-analysis/results/crosschecks.json`)
  are descriptive only, not evidence for or against any hypothesis:**
  - Caleb's Notion Trading Journal has **zero** trades dated on a Monday in
    the window — all 8 real logged trades fall on 2026-11-06, a Friday. Null
    result, reported as-is.
  - 5 newsletter-named Monday runners (Tim Sykes, 2026-10-24 email) were
    graded as a cherry-picked n=5 table. Far below the 10-per-group
    threshold; no test was run. The newsletter's self-reported % moves don't
    match this study's max-gain-from-open metric and aren't directly
    comparable to the figures here.

## Results per hypothesis

Mann-Whitney one-sided test, Holm-corrected across the four checks
(`output/data-analysis/results/results.json`):

| Hypothesis | Check | n pass / fail | Median max gain (pass vs fail) | p (Holm) | Verdict |
|---|---|---|---|---|---|
| H1 | low_float | 263 / 38 | 9.6% vs 7.2% | 0.180 | **Rejected** |
| H2 | catalyst | 64 / 28 | 8.9% vs 11.7% | 0.860 | **Rejected** — wrong direction, not just non-significant |
| H3 | former_runner | 49 / 252 | 11.3% vs 8.5% | 0.126 | **Rejected** — p_raw=0.042 looked promising but doesn't survive Holm correction |
| H4 | unusual_volume | 102 / 199 | 14.2% vs 6.6% | 1.5×10⁻⁵ | **Supported** |
| H5 | (ranking is real, not noise) | — | — | — | **Insufficient** — see below |

**H4 is the one finding that survives correction, by a wide margin.**
Unusual premarket volume (≥5× the 30-session average) is associated with
roughly double the median max gain from the open (14.2% vs 6.6%), and the
effect holds under Holm correction with several orders of magnitude to
spare.

**Leave-one-out comparison** (4/4 graders vs. each "3/4 missing check X"
group) could not be run meaningfully: only **1 ticker in the entire sample
ever graded a true 4/4**, so every leave-one-out group is "insufficient_n"
per the stop rule. This is reported honestly as a limitation of the data,
not glossed over.

**The regression behind H5 did not run.** It requires catalyst as a
covariate, which restricts it to the 92 non-excluded rows — below the
pre-registered n≥100 threshold. The catalyst check's 69% exclusion rate is
what starves it, not a flaw in the regression code. **H5 is marked
insufficient**, not forced through on an underpowered sample.

**Sensitivity run excluding stale_float** (n=219) reproduces the same
pattern: unusual_volume stays clearly significant (p_raw=0.0012),
former_runner weakens further (p_raw=0.056), catalyst and low_float remain
non-significant. The main finding is robust to the stale-float exclusion.

## The check ranking

1. **Unusual volume** — the only check with real, correction-surviving
   predictive power in this sample. Roughly double the median max gain on a
   pass.
2. **Former runner** — a real-looking raw signal (p_raw=0.042) that does not
   survive multiple-comparison correction. Treat as suggestive, not
   confirmed, until a larger or independent sample re-tests it specifically
   (not as part of a four-way comparison, which is a harder bar to clear).
3. **Low float** — no measurable edge in this sample; points the expected
   direction but far from significant.
4. **Catalyst** — no measurable edge, and the point estimate runs *against*
   the hypothesis (catalyst-yes names had a slightly *lower* median max gain
   than catalyst-no). This is read alongside the 69% exclusion rate: Webull's
   thin pre-open news archive for micro/nano-cap gappers means the catalyst
   check could not be tested on anything close to the full sample, which
   likely weakens its apparent signal independent of whether a real catalyst
   effect exists.

**This ranking answers "which check adds the most, given this sample," not
"which check matters in principle."** The catalyst result in particular
should not be read as "catalysts don't matter" — it should be read as "this
study's news-search coverage could not test catalysts on 69% of the
sample," which is a data-availability finding as much as a statistical one.

## What stays open

- **H5 (do the four checks really differ, not just by noise) was never
  properly tested.** The regression that would answer it needs catalyst as a
  covariate and is underpowered by the same news-coverage gap that weakens
  H2. A larger catalyst-labeled sample, or a catalyst data source with
  better pre-open news depth than Webull's `get_stock_news`/`search_news`,
  would let this be re-run properly.
- **Leave-one-out (the 4/4 vs. 3/4-missing-X comparison) is essentially
  untested** — only one ticker in 301 ever graded a clean 4/4. Whether the
  four checks combine additively, or whether one check's signal subsumes
  another's, is an open question this sample cannot answer.
- **The universe itself is a biased sample of "Monday gappers,"** limited to
  whichever 3-5 sector posts Benzinga's search surfaced per Monday (of
  roughly 6-8 possible), skewed toward the largest movers per sector. A
  gapper that didn't make a sector's top names is invisible to this entire
  study, by design stated before data collection.
- **Former runner's p_raw=0.042 is a real candidate for follow-up.** It is
  reported here as rejected under the pre-registered correction, but a study
  designed around this single check (rather than four at once) would face a
  less conservative bar and could settle whether this is signal or noise.
- **The catalyst check needs a better news source before it can be fairly
  tested at all.** 69% of the sample has no confirmed catalyst label either
  way; the current result cannot distinguish "catalysts don't predict bigger
  moves" from "this study couldn't find most of the catalysts."
- **Cross-check 1 (the trading journal) answered nothing** — it had no
  Monday trades to grade. If Caleb starts logging Monday trades going
  forward, this cross-check becomes testable in a future replication.
