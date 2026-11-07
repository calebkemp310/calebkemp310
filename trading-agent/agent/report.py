"""report.md on the paper-trading branch: equity, positions, fills and the
tracking checks from DESIGN.md section 9."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np

from . import broker_paper as bk
from .config import STRATEGY
from .state import read_ledger
from .strategies import vol_target_trend


def expected_trade_days(daily, first_bar: str, cfg=STRATEGY) -> list[tuple[str, str]]:
    """Backtest-rule replay on the same candles, starting at the first bar the paper
    trader acted on: a decision at bar t's close fills on day t+1.
    Returns (side, fill_day) pairs, including a fill due today."""
    from datetime import timedelta
    sig = vol_target_trend(daily, n=cfg.sma_n, target=cfg.vol_target)
    out, holding = [], False
    for i, t in enumerate(daily.index):
        if t.date().isoformat() < first_bar:
            continue
        day = (t + timedelta(days=1)).date().isoformat()
        if not holding and sig["entry"][i]:
            out.append(("buy", day))
            holding = True
        elif holding and sig["exit"][i]:
            out.append(("sell", day))
            holding = False
    return out


def tracking(state_dir: Path, data: dict) -> dict:
    led = read_ledger(state_dir / "ledger.jsonl")
    out = {}
    for p, d in data.items():
        decisions = [r for r in led if r.get("type") == "decision" and r["product"] == p]
        fills = [r for r in led if r.get("type") == "fill" and r["product"] == p and r["kind"] in ("entry", "exit")]
        stops = [r for r in led if r.get("type") == "fill" and r["product"] == p and r["kind"] in ("stop", "kill")]
        if not decisions:
            continue
        expected = expected_trade_days(d["daily"], decisions[0]["bar"])
        actual = [(r["side"], r["ts"][:10]) for r in fills]
        gaps = [abs(r["maker_gap_vs_open"]) for r in fills if r.get("maker_gap_vs_open") is not None]
        out[p] = {"expected": expected, "actual": actual, "match": expected == actual if not stops else None,
                  "stops_or_kills": len(stops), "median_gap": float(np.median(gaps)) if gaps else None,
                  "worst_gap": float(max(gaps)) if gaps else None}
    return out


def write_report(state_dir: Path, state: dict, prices: dict, data: dict) -> None:
    eq, sh = bk.equity(state, prices), bk.shadow_equity(state, prices)
    dd = eq / state["peak_equity"] - 1
    L = [f"# Paper trading report\n", f"_Updated {state['last_run']}. Started {state['started'][:10]}._\n",
         "| | Value |", "|---|---|",
         f"| Armed | {'yes' if state['armed'] else 'NO: ' + state.get('kill_reason', '')} |",
         f"| Frozen | {'YES' if state['frozen'] else 'no'} |",
         f"| Equity (maker fills) | ${eq:,.2f} ({eq / state['start_equity'] - 1:+.2%}) |",
         f"| Equity (taker shadow) | ${sh:,.2f} ({sh / state['start_equity'] - 1:+.2%}) |",
         f"| Drawdown from peak | {dd:.2%} |",
         f"| Last successful run | {state['last_success'] or state['last_run']} |",
         "", "## Positions\n"]
    if state["positions"]:
        L += ["| Coin | Qty | Entry | Mark | P&L | Stop |", "|---|---|---|---|---|---|"]
        for p, v in state["positions"].items():
            L.append(f"| {p} | {v['qty']:.6f} | {v['entry_px']:,.2f} | {prices[p]:,.2f} | "
                     f"{prices[p] / v['entry_px'] - 1:+.2%} | {v['stop']:,.2f} |")
    else:
        L.append("None: holding cash.")
    L += ["", "## Tracking vs backtest (DESIGN.md section 9)\n",
          "| Coin | Signal match | Expected trades | Actual trades | Median fill gap vs open | Worst gap | Stops/kills |",
          "|---|---|---|---|---|---|---|"]
    for p, t in tracking(state_dir, data).items():
        match = "n/a (stop/kill)" if t["match"] is None else ("yes" if t["match"] else "**NO**")
        fmt = lambda x: "-" if x is None else f"{x:.3%}"
        L.append(f"| {p} | {match} | {len(t['expected'])} | {len(t['actual'])} | {fmt(t['median_gap'])} | "
                 f"{fmt(t['worst_gap'])} | {t['stops_or_kills']} |")
    (state_dir / "report.md").write_text("\n".join(L) + "\n")
