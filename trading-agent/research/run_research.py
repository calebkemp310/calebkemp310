"""Strategy tournament: sweep every candidate on the training period, pick by a
smoothed neighbourhood score, then judge the pick ONCE on held-out data.

Usage:  python -m research.run_research
Writes: results/research.json, results/research.md

The pass/fail gates below were written before any result was seen. Do not edit
them to rescue a strategy; add a new, separately counted trial instead.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import backtest as bt  # noqa: E402
from agent import data, metrics  # noqa: E402
from agent.strategies import CANDIDATES  # noqa: E402

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TRAIN = ("2019-01-01", "2023-12-31")
TEST = ("2024-01-01", "2026-11-06")
BASE_COSTS = bt.Costs(fee=0.006, slip=0.0005)          # 0.65% per side
COST_LADDER = [0.001, 0.0025, 0.0065, 0.013]            # per-side totals for the sensitivity table

GATES = {
    "test_sharpe_mean_min": 0.5,     # mean held-out Sharpe across assets
    "test_sharpe_each_min": 0.0,     # no asset may lose on a risk-adjusted basis
    "test_dd_beats_hold": True,      # every asset: shallower max drawdown than buy & hold
    "grid_positive_frac_min": 0.7,   # share of train grid points (all assets) with Sharpe > 0
    "double_cost_sharpe_min": 0.0,   # mean held-out Sharpe still > 0 at 1.3% per side
    "test_trades_min": 30,           # total held-out trades across assets
    "dsr_min": 0.90,                 # deflated Sharpe, full period, vs every trial run
}


def period(df, sig, start, end):
    m = (df.index >= start) & (df.index <= f"{end} 23:59:59")
    out = {k: (v[m] if isinstance(v, np.ndarray) else v) for k, v in sig.items()}
    return df[m], out


def evaluate(df, sig, start, end, costs=BASE_COSTS):
    d, s = period(df, sig, start, end)
    res = bt.run(d, s, costs)
    return res, metrics.summarize(res)


def neighbours(grid, i):
    """Indices of grid points that differ from point i by one step on one axis."""
    keys = list(grid[0])
    axes = {k: sorted({g[k] for g in grid}) for k in keys}
    out = [i]
    for j, g in enumerate(grid):
        if j == i:
            continue
        diffs = [k for k in keys if g[k] != grid[i][k]]
        if len(diffs) == 1:
            k = diffs[0]
            if abs(axes[k].index(g[k]) - axes[k].index(grid[i][k])) == 1:
                out.append(j)
    return out


def main():
    frames = {(a, tf): data.load(a, tf, "2019-01-01") for a in ASSETS for tf in {"1d", "4h"}}
    report = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data": {f"{a}_{tf}": {"bars": len(df), "first": str(df.index[0]), "last": str(df.index[-1]),
                               "fingerprint": data.fingerprint(df)} for (a, tf), df in frames.items()},
        "train": TRAIN, "test": TEST, "costs_per_side": BASE_COSTS.per_side, "gates": GATES,
        "benchmark": {}, "candidates": {},
    }

    for a in ASSETS:
        df = frames[(a, "1d")]
        report["benchmark"][a] = {
            "train": metrics.summarize(bt.run_hold(df.loc[TRAIN[0]:TRAIN[1]], BASE_COSTS)),
            "test": metrics.summarize(bt.run_hold(df.loc[TEST[0]:TEST[1]], BASE_COSTS)),
        }

    trial_daily_sharpes = []   # every (strategy, params, asset) train run counts as a trial
    for name, (fn, tf, grid) in CANDIDATES.items():
        train_tbl = []
        for params in grid:
            row = {"params": params, "train": {}}
            for a in ASSETS:
                df = frames[(a, tf)]
                res, summ = evaluate(df, fn(df, **params), *TRAIN)
                r = metrics.daily_returns(res.equity)
                trial_daily_sharpes.append(float(r.mean() / r.std()) if r.std() > 0 else 0.0)
                row["train"][a] = summ
            row["train_sharpe_mean"] = float(np.mean([row["train"][a]["sharpe"] for a in ASSETS]))
            train_tbl.append(row)

        smooth = [np.mean([train_tbl[j]["train_sharpe_mean"] for j in neighbours(grid, i)]) for i in range(len(grid))]
        best = int(np.argmax(smooth))
        params = grid[best]
        pos_frac = float(np.mean([train_tbl[i]["train"][a]["sharpe"] > 0 for i in range(len(grid)) for a in ASSETS]))

        test, full, ladder = {}, {}, {}
        for a in ASSETS:
            df = frames[(a, tf)]
            sig = fn(df, **params)
            _, test[a] = evaluate(df, sig, *TEST)
            res_full, full[a] = evaluate(df, sig, TRAIN[0], TEST[1])
            full[a]["_daily"] = metrics.daily_returns(res_full.equity)
            ladder[a] = {}
            for c in COST_LADDER:
                _, s = evaluate(df, sig, *TEST, costs=bt.Costs(fee=c, slip=0.0))
                ladder[a][str(c)] = s["sharpe"]
        report["candidates"][name] = {
            "timeframe": tf, "grid": train_tbl, "smoothed_train_sharpe": [round(x, 3) for x in smooth],
            "chosen": params, "grid_positive_frac": round(pos_frac, 3), "test": test,
            "cost_ladder_test_sharpe": ladder,
            "_full_daily": {a: full[a].pop("_daily") for a in ASSETS}, "full": full,
        }

    n_trials = len(trial_daily_sharpes)
    report["n_trials"] = n_trials
    for name, c in report["candidates"].items():
        daily = c.pop("_full_daily")
        c["dsr"] = {a: round(metrics.deflated_sharpe(daily[a], trial_daily_sharpes), 3) for a in ASSETS}
        ts = [c["test"][a]["sharpe"] for a in ASSETS]
        checks = {
            "test_sharpe_mean": float(np.mean(ts)) >= GATES["test_sharpe_mean_min"],
            "test_sharpe_each": min(ts) > GATES["test_sharpe_each_min"],
            "test_dd_beats_hold": all(c["test"][a]["max_dd"] > report["benchmark"][a]["test"]["max_dd"] for a in ASSETS),
            "grid_robust": c["grid_positive_frac"] >= GATES["grid_positive_frac_min"],
            "double_cost": float(np.mean([c["cost_ladder_test_sharpe"][a]["0.013"] for a in ASSETS])) > GATES["double_cost_sharpe_min"],
            "enough_trades": sum(c["test"][a]["trades"] for a in ASSETS) >= GATES["test_trades_min"],
            "dsr": min(c["dsr"].values()) >= GATES["dsr_min"],
        }
        c["checks"] = checks
        passed = sum(checks.values())
        c["verdict"] = "PAPER-TRADE" if passed == len(checks) else ("WATCH" if passed >= len(checks) - 2 else "REJECT")

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "research.json").write_text(json.dumps(report, indent=1, default=str))
    (out / "research.md").write_text(render(report))
    print(render(report))


def render(r) -> str:
    L = [f"# Strategy tournament results\n",
         f"Generated {r['generated']} from Binance spot candles. Train {r['train'][0]} to {r['train'][1]}, "
         f"held-out {r['test'][0]} to {r['test'][1]}. Costs {r['costs_per_side']*100:.2f}% per side. "
         f"Trials counted: {r['n_trials']}.\n",
         "## Buy & hold benchmark (held-out)\n", "| Asset | Sharpe | CAGR | Max DD |", "|---|---|---|---|"]
    for a, b in r["benchmark"].items():
        t = b["test"]
        L.append(f"| {a} | {t['sharpe']} | {t['cagr']*100:.1f}% | {t['max_dd']*100:.1f}% |")
    bh = r["benchmark"]
    L += ["", "## Summary (held-out, averaged over BTC/ETH/SOL)\n",
          "| Strategy | TF | Chosen params | Mean Sharpe | Worst Max DD | Trades | Sharpe @0.10%/side | Sharpe @1.30%/side | Verdict |",
          "|---|---|---|---|---|---|---|---|---|",
          f"| buy & hold | 1d | - | {np.mean([b['test']['sharpe'] for b in bh.values()]):.2f} | "
          f"{min(b['test']['max_dd'] for b in bh.values())*100:.1f}% | 1 each | - | - | benchmark |"]
    for name, c in r["candidates"].items():
        t = c["test"]
        lad = c["cost_ladder_test_sharpe"]
        L.append(f"| {name} | {c['timeframe']} | {c['chosen']} | {np.mean([t[a]['sharpe'] for a in t]):.2f} | "
                 f"{min(t[a]['max_dd'] for a in t)*100:.1f}% | {sum(t[a]['trades'] for a in t)} | "
                 f"{np.mean([lad[a]['0.001'] for a in lad]):.2f} | {np.mean([lad[a]['0.013'] for a in lad]):.2f} | {c['verdict']} |")
    L += ["", "## Candidates (chosen on train, scored on held-out)\n",
          "| Strategy | TF | Params | Asset | Test Sharpe | Test CAGR | Test Max DD | Trades | Win % | PF | Sharpe @1.3%/side | DSR (full) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, c in r["candidates"].items():
        for a, t in c["test"].items():
            L.append(f"| {name} | {c['timeframe']} | {c['chosen']} | {a} | {t['sharpe']} | {t['cagr']*100:.1f}% | "
                     f"{t['max_dd']*100:.1f}% | {t['trades']} | {'' if t['win_rate'] is None else round(t['win_rate']*100)} | "
                     f"{t['profit_factor']} | {c['cost_ladder_test_sharpe'][a]['0.013']} | {c['dsr'][a]} |")
    L += ["", "## Verdicts\n", "| Strategy | Grid positive | " + " | ".join(next(iter(r['candidates'].values()))['checks']) + " | Verdict |",
          "|---|---|" + "---|" * (len(next(iter(r['candidates'].values()))['checks']) + 1)]
    for name, c in r["candidates"].items():
        L.append(f"| {name} | {c['grid_positive_frac']*100:.0f}% | " + " | ".join("pass" if v else "FAIL" for v in c["checks"].values())
                 + f" | **{c['verdict']}** |")
    L += ["", "## Cost sensitivity (held-out Sharpe by per-side cost)\n", "| Strategy | Asset | " + " | ".join(f"{float(x)*100:.2f}%" for x in COST_LADDER) + " |",
          "|---|---|" + "---|" * len(COST_LADDER)]
    for name, c in r["candidates"].items():
        for a, lad in c["cost_ladder_test_sharpe"].items():
            L.append(f"| {name} | {a} | " + " | ".join(str(v) for v in lad.values()) + " |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
