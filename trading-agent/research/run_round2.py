"""Round 2: widened search. Same split, same costs, same seven gates as round 1.

Usage:  python -m research.run_round2
Writes: results/round2.json, results/round2.md

Pre-registered: candidates, grids and this script were committed before the
first run. The deflated Sharpe pools EVERY trial from rounds 1 and 2.
The rotation strategy is one portfolio, so per-coin gates become
portfolio gates (marked in the table).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import backtest as bt  # noqa: E402
from agent import data, metrics, portfolio  # noqa: E402
from agent.strategies import CANDIDATES, CANDIDATES_R2  # noqa: E402
from research.run_research import (ASSETS, BASE_COSTS, COST_LADDER, GATES, TEST, TRAIN,  # noqa: E402
                                   evaluate, neighbours)


def daily_sr(res) -> float:
    r = metrics.daily_returns(res.equity)
    return float(r.mean() / r.std()) if r.std() > 0 else 0.0


def call(fn, df, params, frames):
    if getattr(fn, "needs_btc", False):
        return fn(df, btc_close=frames[("BTCUSDT", "1d")]["close"], **params)
    return fn(df, **params)


def verdict(checks: dict) -> str:
    passed = sum(v for v in checks.values() if v is not None)
    total = sum(v is not None for v in checks.values())
    return "PAPER-TRADE" if passed == total else ("WATCH" if passed >= total - 2 else "REJECT")


def main():
    tfs = {"1d", "4h", "1w"}
    frames = {(a, tf): data.load(a, tf, "2019-01-01") for a in ASSETS for tf in tfs}
    trials: list[float] = []

    # Round-1 trials, recomputed so the pool is complete.
    for name, (fn, tf, grid) in CANDIDATES.items():
        for p in grid:
            for a in ASSETS:
                df = frames[(a, tf)]
                res, _ = evaluate(df, fn(df, **p), *TRAIN)
                trials.append(daily_sr(res))
    n_round1 = len(trials)

    bench = {a: {"test": metrics.summarize(bt.run_hold(frames[(a, "1d")].loc[TEST[0]:TEST[1]], BASE_COSTS))} for a in ASSETS}
    out = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "train": TRAIN, "test": TEST,
           "costs_per_side": BASE_COSTS.per_side, "gates": GATES, "benchmark": bench, "candidates": {}}

    full_daily = {}
    for name, (fn, tf, grid) in CANDIDATES_R2.items():
        rows = []
        for p in grid:
            row = {"params": p, "train": {}}
            for a in ASSETS:
                df = frames[(a, tf)]
                res, s = evaluate(df, call(fn, df, p, frames), *TRAIN)
                trials.append(daily_sr(res))
                row["train"][a] = s
            row["train_sharpe_mean"] = float(np.mean([row["train"][a]["sharpe"] for a in ASSETS]))
            rows.append(row)
        smooth = [float(np.mean([rows[j]["train_sharpe_mean"] for j in neighbours(grid, i)])) for i in range(len(grid))]
        p = grid[int(np.argmax(smooth))]
        test, ladder, fd = {}, {}, {}
        for a in ASSETS:
            df = frames[(a, tf)]
            sig = call(fn, df, p, frames)
            _, test[a] = evaluate(df, sig, *TEST)
            res_full, _ = evaluate(df, sig, TRAIN[0], TEST[1])
            fd[a] = metrics.daily_returns(res_full.equity)
            ladder[a] = {str(c): evaluate(df, sig, *TEST, costs=bt.Costs(fee=c, slip=0.0))[1]["sharpe"] for c in COST_LADDER}
        full_daily[name] = fd
        out["candidates"][name] = {
            "timeframe": tf, "grid": rows, "smoothed_train_sharpe": [round(x, 3) for x in smooth], "chosen": p,
            "grid_positive_frac": round(float(np.mean([r["train"][a]["sharpe"] > 0 for r in rows for a in ASSETS])), 3),
            "test": test, "cost_ladder_test_sharpe": ladder,
        }

    # Rotation (one portfolio across the three coins).
    d1 = {a: frames[(a, "1d")] for a in ASSETS}
    closes = pd.concat([d1[a]["close"] for a in ASSETS], axis=1, keys=ASSETS)
    opens = pd.concat([d1[a]["open"] for a in ASSETS], axis=1, keys=ASSETS)

    def rot(p, start, end, costs=BASE_COSTS):
        tg = portfolio.dual_momentum_targets(closes, **p)
        m = (closes.index >= start) & (closes.index <= f"{end} 23:59:59")
        return portfolio.run_rotation(opens[m], closes[m], tg[m], costs)

    rrows = []
    for p in portfolio.GRID:
        res = rot(p, *TRAIN)
        trials.append(daily_sr(res))
        rrows.append({"params": p, "train": metrics.summarize(res)})
    smooth = [float(np.mean([rrows[j]["train"]["sharpe"] for j in neighbours(portfolio.GRID, i)])) for i in range(len(rrows))]
    rp = portfolio.GRID[int(np.argmax(smooth))]
    ew_hold = closes.loc[TEST[0]:TEST[1]].div(closes.loc[TEST[0]:TEST[1]].iloc[0]).mean(axis=1)
    out["rotation"] = {
        "grid": rrows, "chosen": rp, "test": metrics.summarize(rot(rp, *TEST)),
        "grid_positive_frac": round(float(np.mean([r["train"]["sharpe"] > 0 for r in rrows])), 3),
        "cost_ladder_test_sharpe": {str(c): metrics.summarize(rot(rp, *TEST, bt.Costs(fee=c, slip=0.0)))["sharpe"] for c in COST_LADDER},
        "equal_weight_hold_test": {"sharpe": round(metrics.sharpe(metrics.daily_returns(ew_hold)), 2),
                                   "max_dd": round(metrics.max_drawdown(ew_hold), 4)},
    }
    rot_full_daily = metrics.daily_returns(rot(rp, TRAIN[0], TEST[1]).equity)

    out["n_trials"] = {"round1": n_round1, "total": len(trials)}
    for name, c in out["candidates"].items():
        c["dsr"] = {a: round(metrics.deflated_sharpe(full_daily[name][a], trials), 3) for a in ASSETS}
        ts = [c["test"][a]["sharpe"] for a in ASSETS]
        c["checks"] = {
            "test_sharpe_mean": float(np.mean(ts)) >= GATES["test_sharpe_mean_min"],
            "test_sharpe_each": min(ts) > GATES["test_sharpe_each_min"],
            "test_dd_beats_hold": all(c["test"][a]["max_dd"] > bench[a]["test"]["max_dd"] for a in ASSETS),
            "grid_robust": c["grid_positive_frac"] >= GATES["grid_positive_frac_min"],
            "double_cost": float(np.mean([c["cost_ladder_test_sharpe"][a]["0.013"] for a in ASSETS])) > GATES["double_cost_sharpe_min"],
            "enough_trades": sum(c["test"][a]["trades"] for a in ASSETS) >= GATES["test_trades_min"],
            "dsr": min(c["dsr"].values()) >= GATES["dsr_min"],
        }
        c["verdict"] = verdict(c["checks"])
    r = out["rotation"]
    r["dsr"] = round(metrics.deflated_sharpe(rot_full_daily, trials), 3)
    r["checks"] = {
        "test_sharpe_mean": r["test"]["sharpe"] >= GATES["test_sharpe_mean_min"],
        "test_sharpe_each": None,  # n/a: one portfolio
        "test_dd_beats_hold": r["test"]["max_dd"] > r["equal_weight_hold_test"]["max_dd"],
        "grid_robust": r["grid_positive_frac"] >= GATES["grid_positive_frac_min"],
        "double_cost": r["cost_ladder_test_sharpe"]["0.013"] > GATES["double_cost_sharpe_min"],
        "enough_trades": r["test"]["trades"] >= GATES["test_trades_min"],
        "dsr": r["dsr"] >= GATES["dsr_min"],
    }
    r["verdict"] = verdict(r["checks"])

    res_dir = ROOT / "results"
    res_dir.mkdir(exist_ok=True)
    (res_dir / "round2.json").write_text(json.dumps(out, indent=1, default=str))
    (res_dir / "round2.md").write_text(render(out))
    print(render(out))


def render(o) -> str:
    def f(x):
        return "pass" if x else ("n/a" if x is None else "FAIL")
    L = ["# Round 2 results (widened search)\n",
         f"Generated {o['generated']}. Train {o['train'][0]} to {o['train'][1]}, held-out {o['test'][0]} to {o['test'][1]}. "
         f"Costs {o['costs_per_side']*100:.2f}% per side. Trials pooled for deflated Sharpe: {o['n_trials']['total']} "
         f"({o['n_trials']['round1']} from round 1).\n",
         "## Summary (held-out; per-coin strategies averaged over BTC/ETH/SOL)\n",
         "| Strategy | TF | Chosen params | Mean Sharpe | Worst Max DD | Trades | Sharpe @0.10% | Sharpe @1.30% | Best DSR | Verdict |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    b = o["benchmark"]
    L.append(f"| buy & hold | 1d | - | {np.mean([b[a]['test']['sharpe'] for a in b]):.2f} | {min(b[a]['test']['max_dd'] for a in b)*100:.1f}% | - | - | - | - | benchmark |")
    for name, c in o["candidates"].items():
        t, lad = c["test"], c["cost_ladder_test_sharpe"]
        L.append(f"| {name} | {c['timeframe']} | {c['chosen']} | {np.mean([t[a]['sharpe'] for a in t]):.2f} | "
                 f"{min(t[a]['max_dd'] for a in t)*100:.1f}% | {sum(t[a]['trades'] for a in t)} | "
                 f"{np.mean([lad[a]['0.001'] for a in lad]):.2f} | {np.mean([lad[a]['0.013'] for a in lad]):.2f} | "
                 f"{max(c['dsr'].values())} | {c['verdict']} |")
    r = o["rotation"]
    L.append(f"| dual_momentum (portfolio) | 1d | {r['chosen']} | {r['test']['sharpe']} | {r['test']['max_dd']*100:.1f}% | "
             f"{r['test']['trades']} | {r['cost_ladder_test_sharpe']['0.001']} | {r['cost_ladder_test_sharpe']['0.013']} | {r['dsr']} | {r['verdict']} |")
    L.append(f"| equal-weight hold (portfolio benchmark) | 1d | - | {r['equal_weight_hold_test']['sharpe']} | {r['equal_weight_hold_test']['max_dd']*100:.1f}% | - | - | - | - | benchmark |")
    keys = list(next(iter(o["candidates"].values()))["checks"])
    L += ["", "## Gates\n", "| Strategy | Grid positive | " + " | ".join(keys) + " | Verdict |", "|---|---|" + "---|" * (len(keys) + 1)]
    for name, c in list(o["candidates"].items()) + [("dual_momentum", r)]:
        L.append(f"| {name} | {c['grid_positive_frac']*100:.0f}% | " + " | ".join(f(c['checks'][k]) for k in keys) + f" | **{c['verdict']}** |")
    L += ["", "## Per-coin held-out detail\n", "| Strategy | Coin | Sharpe | CAGR | Max DD | Trades | Win % | PF | Exposure |", "|---|---|---|---|---|---|---|---|---|"]
    for name, c in o["candidates"].items():
        for a, t in c["test"].items():
            L.append(f"| {name} | {a} | {t['sharpe']} | {t['cagr']*100:.1f}% | {t['max_dd']*100:.1f}% | {t['trades']} | "
                     f"{'' if t['win_rate'] is None else round(t['win_rate']*100)} | {t['profit_factor']} | {t['exposure']*100:.0f}% |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
