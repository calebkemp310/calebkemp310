"""RiskGate: pure functions, no I/O. Every order passes through here.

assess() looks at the whole account and returns a mode:
  kill   -> flatten everything, disarm (only 'kill' orders pass)
  freeze -> no orders at all (data or connectivity can't be trusted)
  ok     -> orders allowed; block_entries=True still allows exits
vet() checks one order against caps and sanity rules, clipping where it can.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from .config import Limits


@dataclass(frozen=True)
class Order:
    product: str
    side: str                 # "buy" | "sell"
    kind: str                 # "entry" | "exit" | "stop" | "kill"
    notional: float | None    # USD, buys
    qty: float | None         # coins, sells
    price: float              # reference price at decision time


@dataclass(frozen=True)
class RiskContext:
    now: datetime
    armed: bool
    kill_file: bool
    equity: float
    peak_equity: float
    day_start_equity: float
    daily_bar_close: datetime
    hourly_bar_close: datetime
    feed_gaps: dict           # product -> fractional gap, or None if no secondary answered
    consecutive_errors: int
    errors_24h: int
    positions: dict           # product -> current notional (USD)
    entries_today: dict       # product -> count
    last_price: dict          # product -> last trade


@dataclass(frozen=True)
class Verdict:
    mode: str
    reasons: list = field(default_factory=list)
    block_entries: bool = False


def _hours(a: datetime, b: datetime) -> float:
    return (a - b).total_seconds() / 3600


def assess(c: RiskContext, L: Limits) -> Verdict:
    # 1. Armed / KILL file: checked first, beats everything.
    if c.kill_file:
        return Verdict("kill", ["KILL file present"])
    if not c.armed:
        return Verdict("kill", ["disarmed"])

    # 2-4. Can the data be trusted?
    freeze = []
    age_d = _hours(c.now, c.daily_bar_close)
    if age_d > L.daily_bar_max_age_h:
        freeze.append(f"daily bar stale ({age_d:.1f}h)")
    age_h = _hours(c.now, c.hourly_bar_close)
    if age_h > L.hourly_max_age_h:
        freeze.append(f"hourly price stale ({age_h:.1f}h)")
    for p, gap in sorted(c.feed_gaps.items()):
        if gap is not None and abs(gap) > L.feed_max_gap:
            freeze.append(f"{p} feeds disagree by {gap:+.2%}")
    if c.consecutive_errors >= L.max_consecutive_errors:
        freeze.append(f"{c.consecutive_errors} consecutive data errors")
    if c.errors_24h >= L.max_errors_24h:
        freeze.append(f"{c.errors_24h} data errors in 24h")
    if freeze:
        return Verdict("freeze", freeze)

    # 6. Drawdown kill (only on trusted marks).
    dd = c.equity / c.peak_equity - 1
    if dd <= L.drawdown_kill:
        return Verdict("kill", [f"drawdown {dd:.1%} hit the {L.drawdown_kill:.0%} kill"])

    # 5. Daily loss: block entries, keep exits.
    day = c.equity / c.day_start_equity - 1
    if day <= L.daily_loss_block:
        return Verdict("ok", [f"daily loss {day:.1%}: entries blocked until 00:00 UTC"], block_entries=True)
    return Verdict("ok")


def vet(o: Order, c: RiskContext, L: Limits, v: Verdict) -> tuple[Order | None, str]:
    if v.mode == "kill":
        if o.kind != "kill" or o.side != "sell" or not o.qty or o.qty <= 0:
            return None, "kill mode: only flatten orders"
        return o, "ok"
    if v.mode == "freeze":
        return None, "frozen: " + "; ".join(v.reasons)
    if o.kind == "kill":
        return None, "kill order outside kill mode"

    last = c.last_price.get(o.product)
    if not last or abs(o.price / last - 1) > L.price_band + 1e-12:
        return None, f"price {o.price} outside {L.price_band:.0%} of last {last}"

    if o.side == "sell":
        if o.qty is None or o.qty <= 0:
            return None, "non-positive quantity"
        return o, "ok"

    # Buys
    if v.block_entries:
        return None, "entries blocked: " + "; ".join(v.reasons)
    if c.entries_today.get(o.product, 0) >= L.max_entries_per_coin_per_day:
        return None, "already entered this coin today (max 1 per day)"
    if o.notional is None or o.notional <= 0:
        return None, "non-positive notional"
    held = c.positions.get(o.product, 0.0)
    room_coin = L.sleeve_cap * c.equity - held
    room_total = L.total_cap * c.equity - sum(c.positions.values())
    allowed = min(o.notional, room_coin, room_total)
    if allowed < L.min_notional:
        return None, f"below min notional after caps (room ${max(allowed, 0):.2f})"
    if allowed < o.notional - 1e-9:
        return replace(o, notional=allowed), f"clipped to cap (${allowed:.2f})"
    return o, "ok"
