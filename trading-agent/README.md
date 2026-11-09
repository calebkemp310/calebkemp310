# Trading agent

Research, and a **paper** trader for one strategy that passed most validation gates.
No code here holds an API key or can place a real order.

- [SPEC.md](SPEC.md): research, strategy tournament results, risk spec.
- [DESIGN.md](DESIGN.md): how the paper trader works and how it's judged.

## Paper trader

Scheduled hourly on GitHub Actions (`.github/workflows/paper-trader.yml`); GitHub actually runs it about every 4 hours. It trades
`vol_target_trend` (50-day trend filter, 30% vol target) on BTC-USD and ETH-USD
with a virtual $10,000, using Coinbase public prices checked against Binance/Kraken.

| You want to | Do this |
|---|---|
| See how it's doing | Open `report.md` on the `paper-trading` branch |
| See alerts | Open `alerts.md` on the `paper-trading` branch (trades, freezes, limit hits, kills, weekly summary). The Sunday heartbeat check also pushes a summary to your phone. Phone alerts per event are off (repo Issues are disabled by choice) |
| Stop everything now | Add a file named `KILL` in `trading-agent/` on `main` (GitHub app: Add file), or Actions → Paper trader → Run workflow → `kill` |
| Start again after a kill | Delete the `KILL` file, then Actions → Paper trader → Run workflow → `rearm` |
| Run a cycle now | Actions → Paper trader → Run workflow → `run` |

Every decision, risk check and fill is appended to `ledger.jsonl` on the
`paper-trading` branch. Limits live in `agent/config.py`, and changing one takes a reviewed commit.

## Development

```
pip install -r requirements.txt
python -m pytest -q
python -m research.run_research && python -m research.run_round2   # research
python -m agent.runner --state-dir /tmp/paper --outbox /tmp/outbox.md   # one paper cycle, live public data
```
