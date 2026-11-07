"""Bar-by-bar long-only backtester.

Timing rule: a signal computed from bar t's CLOSE is filled at bar t+1's OPEN.
Costs: every fill pays `fee` (fraction of notional) and moves `slip` against us.
A signal on the final bar is never filled.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Costs:
    fee: float = 0.006    # per side, fraction of notional (Coinbase Advanced lowest taker tier, assumption)
    slip: float = 0.0005  # per side, adverse price move vs the bar open

    @property
    def per_side(self) -> float:
        return self.fee + self.slip


@dataclass
class Result:
    equity: pd.Series                 # marked at each bar close
    trades: list = field(default_factory=list)  # (entry_time, exit_time, pnl_frac)
    exposure: float = 0.0


def run(df: pd.DataFrame, signals: dict, costs: Costs = Costs(), weight: float = 1.0) -> Result:
    """signals: 'entry' and 'exit' boolean arrays aligned to df (known at bar close),
    optional 'max_hold' (int bars, time stop)."""
    o = df["open"].to_numpy()
    c = df["close"].to_numpy()
    entry = np.asarray(signals["entry"], dtype=bool)
    exit_ = np.asarray(signals["exit"], dtype=bool)
    max_hold = signals.get("max_hold")
    n = len(df)

    cash, qty = 1.0, 0.0
    pending = 0          # +1 buy at next open, -1 sell at next open
    entry_px = entry_i = None
    entry_equity = None
    eq = np.empty(n)
    trades = []
    in_mkt = 0

    for t in range(n):
        # 1) Fill whatever was decided at the previous close, at this bar's open.
        if pending == 1 and qty == 0:
            px = o[t] * (1 + costs.slip)
            notional = cash * weight
            qty = notional * (1 - costs.fee) / px
            cash -= notional
            entry_px, entry_i, entry_equity = px, t, cash + notional
        elif pending == -1 and qty > 0:
            px = o[t] * (1 - costs.slip)
            cash += qty * px * (1 - costs.fee)
            trades.append((df.index[entry_i], df.index[t], cash / entry_equity - 1))
            qty = 0.0
            entry_px = entry_i = entry_equity = None
        pending = 0

        # 2) Mark to market at the close.
        eq[t] = cash + qty * c[t]
        if qty > 0:
            in_mkt += 1

        # 3) Decide using information up to and including this close.
        if t == n - 1:
            break
        if qty == 0 and entry[t]:
            pending = 1
        elif qty > 0:
            held = t - entry_i + 1
            if exit_[t] or (max_hold is not None and held >= max_hold):
                pending = -1

    return Result(equity=pd.Series(eq, index=df.index), trades=trades, exposure=in_mkt / n)


def run_hold(df: pd.DataFrame, costs: Costs = Costs()) -> Result:
    """Buy at the first open, hold to the end. Benchmark."""
    entry = np.zeros(len(df), dtype=bool)
    entry[0] = True
    return run(df, {"entry": entry, "exit": np.zeros(len(df), dtype=bool)}, costs)
