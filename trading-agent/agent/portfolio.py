"""Multi-asset rotation backtest (round 2).

dual_momentum: at each daily close, rank coins by trailing `lookback`-day return.
Hold the leader if its return is positive, else hold cash. Switches fill at the
next open and pay costs on both legs. Edge: capital rotates into the strongest
coin, and absolute momentum keeps the book in cash during broad drawdowns.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest import Costs, Result


def dual_momentum_targets(closes: pd.DataFrame, lookback: int) -> np.ndarray:
    """Index of the coin to hold after each close (-1 = cash). Uses closes up to t only."""
    mom = closes.pct_change(lookback, fill_method=None).fillna(-np.inf).to_numpy()
    best = mom.argmax(axis=1)
    return np.where(mom.max(axis=1) > 0, best, -1)


def run_rotation(opens: pd.DataFrame, closes: pd.DataFrame, targets: np.ndarray, costs: Costs = Costs()) -> Result:
    o, c = opens.to_numpy(), closes.to_numpy()
    n = len(closes)
    cash, qty, held = 1.0, 0.0, -1
    entry_eq = entry_t = None
    eq = np.empty(n)
    trades, in_mkt, pending = [], 0, -1
    for t in range(n):
        if t > 0 and pending != held:
            if held >= 0:  # sell current
                cash = qty * o[t, held] * (1 - costs.slip) * (1 - costs.fee)
                trades.append((closes.index[entry_t], closes.index[t], cash / entry_eq - 1))
                qty, held = 0.0, -1
            if pending >= 0 and np.isfinite(o[t, pending]):  # buy new leader
                entry_eq, entry_t = cash, t
                qty = cash * (1 - costs.fee) / (o[t, pending] * (1 + costs.slip))
                cash, held = 0.0, pending
        eq[t] = cash + (qty * c[t, held] if held >= 0 else 0.0)
        in_mkt += held >= 0
        pending = targets[t] if t < n - 1 else held
    return Result(equity=pd.Series(eq, index=closes.index), trades=trades, exposure=in_mkt / n)


GRID = [{"lookback": L} for L in [30, 60, 90, 120]]
