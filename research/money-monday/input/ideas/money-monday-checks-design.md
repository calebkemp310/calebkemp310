---
title: "Which Money Monday check best predicts a bigger Monday move in small-cap gappers?"
type: design
created: 2026-11-09
updated: 2026-11-09
tags: [trading, us-small-caps, money-monday, quantitative]
status: draft
author: mixed
---

# Which Money Monday check best predicts a bigger Monday move?

## Research Question
Over the last 26 Mondays (May 11 – Nov 9, 2026), among US stocks under $20 that gapped up 10% or more premarket or at the open, does passing each Money Monday check go with a larger **max gain from the open** (day high ÷ open − 1)? Which check adds the most once the other three are known?

The checks are low float, bullish news catalyst, former runner and unusual volume.

This can come out negative. A check may add nothing, or point the wrong way: passing it could go with a *smaller* move.

## Relevance (brief)
The four checks come from a newsletter pitch, Tim Bohen's "Money Monday" via StocksToTrade and Tim Sykes. Its examples are hand-picked winners: WORX, MNDR, MI, SOAR, GRML. Caleb grades setups A (4/4), B (3/4 with a clear catalyst) or no trade. Testing each check against every gapper, losers included, shows which rules earn their place in the screener and which are noise.

## Method
Quantitative. Grade every gapper, then compare outcomes.

1. **Universe.** For each Monday, collect every US-listed stock up ≥10% premarket or at the open, priced under $20.
2. **Grading.** Score each name on the four checks with fixed, mechanical rules. The rules are set before any outcome is looked at, and they use only information available before the 9:30 ET open.
   - *Low float:* Webull outstanding shares under 90M. Flag a share count as possibly stale when one day's volume is more than 50× that count, or an offering, conversion or reverse split happened in the prior 30 days.
   - *Catalyst:* company-specific positive news published in the 24 hours before the open: a launch, partnership, contract, earnings, deal or FDA event. Offerings, related-party deals, compliance and listing notices, and lawsuits don't count. Each item is classified from its headline and summary *without seeing the price outcome*, and the label is logged.
   - *Former runner:* at least one day of +50% or more (close to close, or intraday high vs prior close) in the prior 30 sessions, with the latest close no more than 50% below that spike's high.
   - *Unusual volume:* premarket volume at least 5× the stock's 30-day average daily volume. Where premarket volume isn't available, use the prior session's volume against the same average, and mark that substitution.
3. **Outcome.** Max gain from the open, taken from the daily bar.
4. **Analysis.**
   - (a) For each check, the median outcome for pass vs fail, with a rank-sum test
   - (b) Leave-one-out: the 4/4 group compared with each "3/4, missing check X" group
   - (c) If there are at least 100 names: a regression of log(1 + max gain) on the four pass/fail flags, with Monday fixed effects
   - Rank the checks by the size of their effect in (c), or in (a) and (b) when the sample is too small for (c).

**Alternatives not chosen.**
- Caleb's own trades only: too few to rank four checks.
- The TextToQuant backtester: this account's plan covers crypto only.

## Data Sources / Material Basis
- **Main sample:** past Monday gappers rebuilt from Benzinga's "Stocks Moving In Monday's Pre-Market Session" and "…Intraday Session" posts, found with Webull `search_news`. Webull's gainers ranking is live only and has no history. Per-ticker data comes from Webull:
  - daily bars (`get_stock_bars`)
  - premarket M5 bars where available
  - snapshots (share counts)
  - `get_stock_news` (catalysts)
- **Cross-check 1:** Caleb's logged trades in the Notion Trading Journal (Trades database).
- **Cross-check 2:** Monday runners named in the Sykes and Bohen emails in Gmail. Reported separately, because they are a cherry-picked set.

## Output Target
☐ Book chapter  ☐ Journal article  ☐ Grant proposal  ☐ Talk  ☑ Other: a findings page (artifact) that ranks the four checks, plus proposed edits to the Money Monday screener rules if a check proves useless.

## Expected Results
- **Positive:** one or two checks clearly separate big movers from small ones, e.g. catalyst names show a median max gain well above non-catalyst names. The screener then weights those checks more.
- **Null:** no check separates outcomes once the others are controlled. The A/B grade then adds little beyond "it gapped", and the screener should be simplified.

## Ethical / Methodological Risks
- **Survivorship and adjusted prices:** delisted and reverse-split tickers may be missing, or show split-adjusted prices. These are flagged and kept in the sample where data exists.
- **Incomplete universe:** the Benzinga movers posts list only some gappers, so the universe is biased toward the largest movers. This is stated with every result.
- **Catalyst judgment:** labels are assigned blind to outcomes and logged, so they can be audited.
- **Small groups:** about 26 Mondays may yield few 4/4 names. Group sizes are reported, and no effect is claimed from a group under 10 names.
- **Stale share counts:** seen already with SPRC and BURU. These are flagged, and a sensitivity check is run without them.
- **Not advice:** results describe past data only and are educational, not a trading recommendation.

## Feasibility
- About 26 Mondays × ~10–20 names each means roughly 260–520 ticker look-ups, plus manual catalyst labels.
- The tools are already connected: Webull, Notion and Gmail. Analysis runs in Python in `output/data-analysis/`.
- No collaborators, paid plans or credits are needed.
- Main constraint: how far back Webull's news and premarket bars reach. This is checked on the first Monday before scaling up.

## Scope Boundaries (what is NOT investigated)
- Entry timing, stops, hold time or position sizing
- Short selling
- Days other than Monday
- Stocks priced $20 or more
- Options, and the trading-agent crypto work in `trading-agent/`

## Next Step
Hand off to writing-research-plan to produce `input/ideas/money-monday-checks-plan.md`, with full pre-registration, since the project is quantitative.
