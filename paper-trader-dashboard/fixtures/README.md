# Dashboard fixtures

Load one with `index.html?src=fixtures/<name>/&now=<ISO time>`.

| Fixture | Suggested `now` | Expect |
|---|---|---|
| `flat` | `2026-11-13T02:00:00Z` | ARMED, $10,000.00 in both books, "Flat" message, "No trades yet" |
| `active` | `2026-11-09T00:30:00Z` | Maker $10,432.10 (+4.32%), shadow $10,371.55, BTC position +4.20%, ETH signal match NO, 30h gap flagged, 18 alerts with "Show all" |
| `empty-ledger` | `2026-11-13T02:00:00Z` | "unmarked" equity, "No signal yet", "0 marks", "No alerts yet", report/alerts file errors |
| `malformed` | `2026-11-13T02:00:00Z` | "4 ledger lines could not be read", other panels still render |
| `killed` | `2026-11-13T02:00:00Z` | DISARMED with "drawdown -25.4% from peak" |
| `frozen` | `2026-11-13T04:00:00Z` | FROZEN with the feed-disagreement reason |
| `stale` | `2026-11-15T03:00:00Z` | ARMED · STALE (amber) and the 26h stale banner |
| `bad-state` | any | state.json error (invalid JSON), UNKNOWN pill, alerts still shown |
| `missing` | any | All four files fail, with a Retry button |
| `xss` | any | Alert text containing HTML shown literally, no dialog |
