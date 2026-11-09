---
title: "Data availability probe (Task 1)"
type: note
created: 2026-11-09
updated: 2026-11-09
status: review
author: llm
---

# Data availability probe — Task 1

Probed on 2026-11-09 against the far end (May 11, 2026) and near end (Nov 2, 2026) of the pre-registered window.

## 1. Universe — Benzinga movers posts: AVAILABLE

- `search_news` with keyword `Stocks Moving In Monday's Pre-Market Session` and a single-day date range returns the sector posts for both May 11 and Nov 2: Consumer Discretionary, Health Care, Industrials, Information Technology and Financials. The general "20 Stocks Moving Premarket" post also comes back.
- The API summary only lists 3–6 gainers per post. The **full article** at `news-static.webullfintech.com/us/news-html/<date>/<news_id>.html` is fetchable from this environment and lists every gainer with exchange, ticker, % move and price. Example from May 11, Industrials: CLIK +78.0% to $3.97, BW, HTCO +17.8% to $6.88, MNTS, UGRO, AIRJ. This text can be parsed.
- **Limit:** each sector post names about 6 gainers, so the universe is the biggest movers per sector, not every gapper. This bias was already stated in the design.

## 2. Daily bars: AVAILABLE

- `get_stock_bars` with timespan `D` returns May 2026 daily bars with `end_time` set. Tested on CLIK, HPAI and DCOY for May 7–11.

## 3. Premarket M5 bars: ROLLING 180-DAY LIMIT

- Webull refuses minute bars older than 180 days: `start_time cannot be earlier than 180 days ago for minute-level timespan`. On 2026-11-09 the oldest reachable date is **2026-05-13**.
- Results:
  - **May 11: not reachable.** Its volume check uses the pre-registered fallback (prior-session volume, `volume_basis=prior_session`). This follows the frozen rule and is not a deviation.
  - **May 18: reachable today** (HTCO returned 04:00–09:30 ET bars), but it drops out around Nov 14. One more Monday drops out each week after that.
  - **Nov 2: reachable** (INO and CLRO returned full 04:00–09:25 ET bars).
- **Action:** pull premarket M5 bars for every Monday in the universe first, this week, before more Mondays age out. Any Monday that ages out first falls back to `prior_session`, and that is logged.

## 4. Pre-open news for catalyst labels: AT RISK for older Mondays

- `get_stock_news` (per ticker, no date filter) returns recent items first. CLIK's feed held only 3 items, the oldest from Oct 22, so it does not reach May.
- `search_news` with a ticker or company name and a May date range returned nothing in two tests (`Click Holdings` and `CLIK` for May 8–11; `Helport AI` for May 8–11).
- Partial routes to try in Task 4:
  - The movers article text sometimes gives the reason, e.g. "the company's Q1 earnings came out today"
  - Benzinga "Why <company> shares are trading higher" posts, searched by date
  - Paging `get_stock_news` further back
- **Open decision for Caleb:** when no pre-open news can be found for a ticker, the frozen rule has no "unknown" outcome. Two options:
  - (a) Count it as **no catalyst**. This follows the rule literally, but may wrongly fail stocks that did have news.
  - (b) Exclude the ticker from the catalyst test only, and report how many were excluded.

  Either choice is a deviation and must be logged before Task 4.

## Verdict

The pre-registered window can be covered for the universe, daily bars and premarket volume (with the fallback for May 11). Catalyst coverage for older Mondays needs the decision above. Task 2 can start.
