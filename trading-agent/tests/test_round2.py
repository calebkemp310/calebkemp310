import numpy as np
import pandas as pd
import pytest

from agent import backtest as bt
from agent import portfolio
from agent.strategies import CANDIDATES_R2
from tests.test_backtest import make_df

CUTS = [(500, 3.0), (500, 0.3), (650, 3.0), (650, 0.3)]


def call(fn, df, params):
    if getattr(fn, "needs_btc", False):
        return fn(df, btc_close=df["close"], **params)
    return fn(df, **params)


@pytest.mark.parametrize("name", list(CANDIDATES_R2))
def test_no_lookahead_round2(name):
    fn, _, grid = CANDIDATES_R2[name]
    df = make_df(800)
    for cut, mult in CUTS:
        future = df.copy()
        future.iloc[cut + 1:, :4] *= mult
        for params in grid:
            a, b = call(fn, df, params), call(fn, future, params)
            for key in ("entry", "exit", "weight"):
                if key in a:
                    assert np.array_equal(a[key][: cut + 1], b[key][: cut + 1]), (name, params, key, cut)
            ea = bt.run(df, a).equity.iloc[: cut + 1].to_numpy()
            eb = bt.run(future, b).equity.iloc[: cut + 1].to_numpy()
            assert np.allclose(ea, eb), (name, params, cut)


def test_weight_scales_exposure():
    df = make_df(10)
    entry = np.zeros(10, bool)
    entry[2] = True
    sig = {"entry": entry, "exit": np.zeros(10, bool), "weight": np.full(10, 0.25)}
    full = bt.run(df, {"entry": entry, "exit": np.zeros(10, bool)}, bt.Costs(0, 0)).equity
    quarter = bt.run(df, sig, bt.Costs(0, 0)).equity
    assert quarter.iloc[-1] - 1 == pytest.approx((full.iloc[-1] - 1) * 0.25)


def three_coins(n=400):
    dfs = [make_df(n, seed=s) for s in (1, 2, 3)]
    closes = pd.concat([d["close"] for d in dfs], axis=1, keys=["A", "B", "C"])
    opens = pd.concat([d["open"] for d in dfs], axis=1, keys=["A", "B", "C"])
    return opens, closes


def test_rotation_no_lookahead():
    opens, closes = three_coins()
    for cut, mult in [(250, 3.0), (250, 0.3)]:
        fo, fc = opens.copy(), closes.copy()
        fo.iloc[cut + 1:] *= mult
        fc.iloc[cut + 1:] *= mult
        for p in portfolio.GRID:
            ta = portfolio.dual_momentum_targets(closes, **p)
            tb = portfolio.dual_momentum_targets(fc, **p)
            assert np.array_equal(ta[: cut + 1], tb[: cut + 1])
            ea = portfolio.run_rotation(opens, closes, ta).equity.iloc[: cut + 1].to_numpy()
            eb = portfolio.run_rotation(fo, fc, tb).equity.iloc[: cut + 1].to_numpy()
            assert np.allclose(ea, eb)


def test_rotation_switch_costs_both_legs():
    opens, closes = three_coins(6)
    targets = np.array([0, 1, 1, 1, 1, 1])  # hold A after bar 0, switch to B after bar 1
    res = portfolio.run_rotation(opens, closes, targets, bt.Costs(fee=0.01, slip=0.0))
    a_qty = 0.99 / opens["A"].iloc[1]
    cash = a_qty * opens["A"].iloc[2] * 0.99
    b_qty = cash * 0.99 / opens["B"].iloc[2]
    assert res.equity.iloc[2] == pytest.approx(b_qty * closes["B"].iloc[2])
    assert len(res.trades) == 1


def test_weekly_and_daily_sharpe_agree():
    """Scoring a weekly equity curve must not inflate Sharpe vs the same path sampled daily."""
    from agent import metrics
    rng = np.random.default_rng(7)
    idx = pd.date_range("2020-01-06", periods=7 * 300, freq="1D", tz="UTC")
    eq = pd.Series(np.exp(np.cumsum(rng.normal(0.001, 0.03, len(idx)))), index=idx)
    weekly = eq.iloc[::7]
    s_d = metrics.sharpe(metrics.daily_returns(eq))
    s_w = metrics.sharpe(metrics.daily_returns(weekly))
    assert abs(s_w - s_d) < 0.5, (s_d, s_w)
