from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from agent.config import Limits
from agent.risk import Order, RiskContext, assess, vet

L = Limits()
NOW = datetime(2026, 11, 8, 0, 7, tzinfo=timezone.utc)


def ctx(**kw):
    base = dict(
        now=NOW, armed=True, kill_file=False, equity=10_000.0, peak_equity=10_000.0,
        day_start_equity=10_000.0, daily_bar_close=NOW - timedelta(minutes=7),
        hourly_bar_close=NOW - timedelta(minutes=7), feed_gaps={"BTC-USD": 0.001, "ETH-USD": 0.001},
        consecutive_errors=0, errors_24h=0, positions={}, entries_today={},
        last_price={"BTC-USD": 75_000.0, "ETH-USD": 2_200.0},
    )
    base.update(kw)
    return RiskContext(**base)


def buy(product="BTC-USD", notional=1_000.0, price=75_000.0):
    return Order(product=product, side="buy", kind="entry", notional=notional, qty=None, price=price)


def sell(product="BTC-USD", qty=0.01, price=75_000.0, kind="exit"):
    return Order(product=product, side="sell", kind=kind, notional=None, qty=qty, price=price)


# ---- assess: one test per limit, at / inside / outside -------------------------

def test_all_clear():
    v = assess(ctx(), L)
    assert v.mode == "ok" and not v.block_entries and v.reasons == []


def test_disarmed_is_kill():
    assert assess(ctx(armed=False), L).mode == "kill"


def test_kill_file_is_kill():
    assert assess(ctx(kill_file=True), L).mode == "kill"


def test_kill_file_beats_everything_else():
    v = assess(ctx(kill_file=True, daily_bar_close=NOW - timedelta(hours=99), consecutive_errors=9), L)
    assert v.mode == "kill"


@pytest.mark.parametrize("age_h,mode", [(25.9, "ok"), (26.0, "ok"), (26.1, "freeze")])
def test_daily_bar_freshness(age_h, mode):
    assert assess(ctx(daily_bar_close=NOW - timedelta(hours=age_h)), L).mode == mode


@pytest.mark.parametrize("age_h,mode", [(1.9, "ok"), (2.0, "ok"), (2.1, "freeze")])
def test_hourly_freshness(age_h, mode):
    assert assess(ctx(hourly_bar_close=NOW - timedelta(hours=age_h)), L).mode == mode


@pytest.mark.parametrize("gap,mode", [(0.0099, "ok"), (0.01, "ok"), (0.0101, "freeze"), (-0.02, "freeze")])
def test_feed_agreement(gap, mode):
    assert assess(ctx(feed_gaps={"BTC-USD": gap, "ETH-USD": 0.0}), L).mode == mode


def test_missing_secondary_is_not_a_disagreement():
    assert assess(ctx(feed_gaps={"BTC-USD": None, "ETH-USD": 0.0}), L).mode == "ok"


@pytest.mark.parametrize("cons,day,mode", [(2, 4, "ok"), (3, 3, "freeze"), (0, 5, "freeze")])
def test_error_budget(cons, day, mode):
    assert assess(ctx(consecutive_errors=cons, errors_24h=day), L).mode == mode


@pytest.mark.parametrize("eq,blocked", [(9_701.0, False), (9_700.0, True), (9_500.0, True)])
def test_daily_loss_blocks_entries(eq, blocked):
    v = assess(ctx(equity=eq, peak_equity=10_000.0), L)
    assert v.mode == "ok" and v.block_entries is blocked


@pytest.mark.parametrize("eq,mode", [(7_501.0, "ok"), (7_500.0, "kill"), (7_000.0, "kill")])
def test_drawdown_kill(eq, mode):
    assert assess(ctx(equity=eq, day_start_equity=eq), L).mode == mode


def test_stale_data_freezes_before_drawdown_kill():
    """With stale prices the equity mark can't be trusted, so freeze rather than kill."""
    v = assess(ctx(equity=5_000.0, day_start_equity=5_000.0, daily_bar_close=NOW - timedelta(hours=30)), L)
    assert v.mode == "freeze"


def test_assess_is_pure():
    c = ctx(equity=9_600.0)
    assert assess(c, L) == assess(c, L)


# ---- vet: orders ---------------------------------------------------------------

def test_entry_passes():
    o, why = vet(buy(), ctx(), L, assess(ctx(), L))
    assert o is not None and o.notional == 1_000.0 and why == "ok"


def test_entry_clipped_to_sleeve_cap():
    c = ctx(positions={"BTC-USD": 2_000.0})
    o, why = vet(buy(notional=1_500.0), c, L, assess(c, L))
    assert o.notional == pytest.approx(500.0) and "clipped" in why


def test_entry_clipped_to_total_cap():
    c = ctx(positions={"ETH-USD": 2_500.0, "SOL-USD": 2_300.0})
    o, _ = vet(buy(notional=2_500.0), c, L, assess(c, L))
    assert o.notional == pytest.approx(200.0)


def test_entry_rejected_when_no_room():
    c = ctx(positions={"BTC-USD": 2_495.0})
    o, why = vet(buy(notional=500.0), c, L, assess(c, L))
    assert o is None and "min notional" in why


def test_entry_blocked_by_daily_loss_but_exit_allowed():
    c = ctx(equity=9_600.0, peak_equity=10_000.0)
    v = assess(c, L)
    assert vet(buy(), c, L, v)[0] is None
    assert vet(sell(), c, L, v)[0] is not None


def test_one_entry_per_coin_per_day():
    c = ctx(entries_today={"BTC-USD": 1})
    o, why = vet(buy(), c, L, assess(c, L))
    assert o is None and "per day" in why


@pytest.mark.parametrize("px,ok", [(76_499.0, True), (76_501.0, False), (73_501.0, True), (73_499.0, False)])
def test_price_band(px, ok):
    o, _ = vet(buy(price=px), ctx(), L, assess(ctx(), L))
    assert (o is not None) is ok


def test_bad_quantities_rejected():
    assert vet(buy(notional=0.0), ctx(), L, assess(ctx(), L))[0] is None
    assert vet(sell(qty=0.0), ctx(), L, assess(ctx(), L))[0] is None
    assert vet(sell(qty=-1.0), ctx(), L, assess(ctx(), L))[0] is None


def test_freeze_rejects_everything():
    c = ctx(consecutive_errors=5)
    v = assess(c, L)
    assert vet(buy(), c, L, v)[0] is None and vet(sell(), c, L, v)[0] is None


def test_kill_mode_allows_only_kill_orders():
    c = ctx(kill_file=True)
    v = assess(c, L)
    assert vet(buy(), c, L, v)[0] is None
    assert vet(sell(), c, L, v)[0] is None
    assert vet(sell(kind="kill"), c, L, v)[0] is not None


def test_kill_orders_skip_price_band():
    """Flattening must not be blocked by a fast market."""
    c = ctx(kill_file=True)
    assert vet(sell(kind="kill", price=50_000.0), c, L, assess(c, L))[0] is not None


def test_limits_are_frozen():
    with pytest.raises(Exception):
        L.drawdown_kill = -0.9  # type: ignore[misc]
    assert replace(L, drawdown_kill=-0.3).drawdown_kill == -0.3  # changes need a new object (a commit)
