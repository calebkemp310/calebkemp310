"""Simulated fills. Every order fills twice:

- book of record (maker): buy at best bid, sell at best ask, maker fee.
- shadow (taker): buy at ask + slip, sell at bid - slip, taker fee.

Both, plus the backtest's reference price (the daily open), go in the fill
record so tracking reports can show the real cost range. Sells always close
the whole position (the strategy never scales out).
"""
from __future__ import annotations

from datetime import datetime

from .config import Fees
from .risk import Order


class BrokerError(Exception):
    pass


def _buy(book_state: dict, product: str, notional: float, px: float, fee: float) -> float:
    if notional <= 0 or notional > book_state["cash"] + 1e-9:
        raise BrokerError(f"bad buy notional {notional} vs cash {book_state['cash']}")
    qty = notional * (1 - fee) / px
    book_state["cash"] -= notional
    book_state["positions"][product] = {"qty": qty, "entry_px": px}
    return qty


def _sell(book_state: dict, product: str, px: float, fee: float) -> tuple[float, float]:
    pos = book_state["positions"].pop(product, None)
    if not pos or pos["qty"] <= 0:
        raise BrokerError(f"no position in {product}")
    proceeds = pos["qty"] * px * (1 - fee)
    book_state["cash"] += proceeds
    return pos["qty"], proceeds


def execute(order: Order, quote: dict, state: dict, fees: Fees, now: datetime,
            ref_open: float | None, prices: dict, extra: dict | None = None) -> dict:
    """quote: {'bid','ask'}; prices: product -> mark, for sizing the shadow book.
    Mutates state (main + shadow books). Returns the fill record."""
    bid, ask = float(quote["bid"]), float(quote["ask"])
    if not (0 < bid <= ask):
        raise BrokerError(f"bad quote {quote}")
    main = {"cash": state["cash"], "positions": state["positions"]}
    shadow = state["shadow"]
    rec = {"type": "fill", "ts": now.isoformat(), "product": order.product, "side": order.side,
           "kind": order.kind, "bid": bid, "ask": ask, "ref_open": ref_open}
    if order.side == "buy":
        m_px, t_px = bid, ask * (1 + fees.taker_slip)
        qty = _buy(main, order.product, order.notional, m_px, fees.maker_fee)
        main["positions"][order.product].update(extra or {})
        main["positions"][order.product]["entry_time"] = now.isoformat()
        # Shadow commits the same fraction of ITS equity that the main book commits of its own.
        main_eq_before = main["cash"] + order.notional + sum(
            p["qty"] * prices[k] for k, p in main["positions"].items() if k != order.product)
        s_notional = min(order.notional * _equity(shadow, prices) / main_eq_before, shadow["cash"])
        s_qty = _buy(shadow, order.product, s_notional, t_px, fees.taker_fee) if s_notional > 0 else 0.0
        rec.update(notional=order.notional, qty=qty, maker_px=m_px, maker_fee=order.notional * fees.maker_fee,
                   taker_px=t_px, shadow_qty=s_qty)
    else:
        m_px, t_px = ask, bid * (1 - fees.taker_slip)
        qty, proceeds = _sell(main, order.product, m_px, fees.maker_fee)
        rec.update(qty=qty, proceeds=proceeds, maker_px=m_px, maker_fee=qty * m_px * fees.maker_fee, taker_px=t_px)
        if order.product in shadow["positions"]:
            s_qty, s_proceeds = _sell(shadow, order.product, t_px, fees.taker_fee)
            rec.update(shadow_qty=s_qty, shadow_proceeds=s_proceeds)
    state["cash"] = main["cash"]
    if ref_open:
        rec["maker_gap_vs_open"] = rec["maker_px"] / ref_open - 1
        rec["taker_gap_vs_open"] = rec["taker_px"] / ref_open - 1
    return rec


def _equity(book_state: dict, prices: dict) -> float:
    return book_state["cash"] + sum(p["qty"] * prices[k] for k, p in book_state["positions"].items())


def equity(state: dict, prices: dict) -> float:
    return _equity({"cash": state["cash"], "positions": state["positions"]}, prices)


def shadow_equity(state: dict, prices: dict) -> float:
    return _equity(state["shadow"], prices)
