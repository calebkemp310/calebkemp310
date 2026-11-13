# Paper trader dashboard

One self-contained page that shows how the paper trader (`trading-agent/`) is doing. It reads the four files the hourly GitHub Actions job saves to the `paper-trading` branch, live from raw.githubusercontent.com:

- `state.json`
- `ledger.jsonl`
- `report.md`
- `alerts.md`

It's read-only: it never places or suggests orders, and it needs no keys.

## What it shows
- **Health:**
  - armed / frozen / disarmed
  - last successful run, with a warning if it's more than 26h old
  - data errors
  - Coinbase-vs-secondary price agreement
  - day N of the 90-day paper phase
- **Equity:** the maker book and the taker shadow book, each with % change vs $10,000, drawdown from peak, today's change, cash and exposure.
- **Positions:** held coins with mark price, P&L and stop distance, or a "flat" message.
- **Current signal:** per coin, the close vs the 50-day average, volatility, and the would-be size if long. These are informational only.
- **Equity curve:**
  - maker line, plus the taker shadow line dashed
  - $10k baseline
  - trade markers
  - 7D / 30D / All ranges
  - tap to read values
- **Trade history:** every simulated fill, round-trip P&L, and rejected or skipped orders.
- **Tracking vs backtest:** signal match (taken from report.md) and fill gaps vs the daily open (computed here), checked against the paper-phase pass limits.
- **Alerts:** from alerts.md, newest first, each tagged by severity.

## Open it
Open `index.html` from a local server. Fetching the data files doesn't work from `file://`.

```
cd paper-trader-dashboard
python3 -m http.server 8765
# then visit http://localhost:8765/
```

It refreshes every 5 minutes while the tab is visible. Press **Refresh** to load right away.

## Test parameters
- `?src=fixtures/<name>/` loads a test fixture instead of live data. Anything else is ignored, with a notice.
- `?now=<ISO time>` freezes the clock for age and stale checks, for example `?now=2026-11-15T03:00:00Z`.

| Fixture | State |
|---|---|
| `flat` | Snapshot of the live account (cash only) |
| `active` | 35 days of history, an open BTC position, a closed ETH round trip, a rejected order, a 30h outage, 18 alerts |
| `empty-ledger` | Day zero: no marks, no report, no alerts |
| `malformed` | 4 broken ledger lines, which are skipped and counted |
| `killed` | Disarmed by the drawdown kill |
| `frozen` | Frozen by a feed disagreement |
| `missing` | No files at all |
| `xss` | An alert containing HTML, which must show as plain text |

The `flat` snapshot's BTC close (75,731.04) differs from the 74,754.08 in the spec, because the spec quoted an older live value.
