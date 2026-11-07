import numpy as np
import pandas as pd
import pytest

from agent import backtest as bt
from agent.strategies import CANDIDATES


def make_df(n=600, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    open_ = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.002, n))
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.02, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.02, n))
    idx = pd.date_range("2020-01-01", periods=n, freq="1D", tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": 1.0}, index=idx)


@pytest.mark.parametrize("name", list(CANDIDATES))
def test_no_lookahead(name):
    """Changing the future must not change any signal or equity value up to the cut."""
    fn, _, grid = CANDIDATES[name]
    df = make_df()
    for cut, mult in [(300, 3.0), (300, 0.3), (450, 3.0), (450, 0.3)]:
        future = df.copy()
        future.iloc[cut + 1:, :4] *= mult  # wild future, up and down
        for params in grid:
            a, b = fn(df, **params), fn(future, **params)
            for key in ("entry", "exit"):
                assert np.array_equal(a[key][: cut + 1], b[key][: cut + 1]), (name, params, key, cut)
            ea = bt.run(df, a).equity.iloc[: cut + 1]
            eb = bt.run(future, b).equity.iloc[: cut + 1]
            # Equity at the cut close depends only on bars <= cut.
            assert np.allclose(ea.to_numpy(), eb.to_numpy()), (name, params, cut)


def test_lookahead_check_catches_a_leak():
    """Guard the guard: a strategy peeking one bar ahead must be caught."""
    df = make_df()
    caught = False
    for cut, mult in [(300, 3.0), (300, 0.3), (450, 3.0), (450, 0.3)]:
        future = df.copy()
        future.iloc[cut + 1:, :4] *= mult
        leak = lambda d: (d["close"].shift(-1) > d["close"]).to_numpy()
        caught |= not np.array_equal(leak(df)[: cut + 1], leak(future)[: cut + 1])
    assert caught


def test_fill_at_next_open_with_costs():
    df = make_df(10)
    entry = np.zeros(10, bool)
    entry[2] = True
    exit_ = np.zeros(10, bool)
    exit_[5] = True
    costs = bt.Costs(fee=0.01, slip=0.0)
    res = bt.run(df, {"entry": entry, "exit": exit_}, costs)
    buy_px, sell_px = df["open"].iloc[3], df["open"].iloc[6]
    expected = (1 - 0.01) * sell_px / buy_px * (1 - 0.01)
    assert res.equity.iloc[6] == pytest.approx(expected)
    assert res.equity.iloc[2] == pytest.approx(1.0)  # not filled on the signal bar
    assert len(res.trades) == 1


def test_signal_on_last_bar_is_never_filled():
    df = make_df(5)
    entry = np.zeros(5, bool)
    entry[-1] = True
    res = bt.run(df, {"entry": entry, "exit": np.zeros(5, bool)})
    assert res.equity.iloc[-1] == 1.0 and not res.trades


def test_costs_only_reduce_returns():
    df = make_df()
    fn, _, grid = CANDIDATES["trend_sma"]
    sig = fn(df, **grid[0])
    free = bt.run(df, sig, bt.Costs(0, 0)).equity.iloc[-1]
    paid = bt.run(df, sig, bt.Costs(0.006, 0.0005)).equity.iloc[-1]
    assert paid < free


def test_time_stop():
    df = make_df(40)
    entry = np.zeros(40, bool)
    entry[0] = True
    res = bt.run(df, {"entry": entry, "exit": np.zeros(40, bool), "max_hold": 3})
    (t_in, t_out, _), = res.trades
    assert (t_out - t_in).days == 3
