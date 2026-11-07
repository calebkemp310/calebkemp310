"""Every number the paper trader acts on. Frozen on purpose: changing a limit
means a reviewed commit, never a runtime setting. Approved by Caleb 2026-11-07
(DESIGN.md section 6)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    sleeve_cap: float = 0.25           # max fraction of equity per coin
    total_cap: float = 0.50            # max fraction of equity across coins
    daily_loss_block: float = -0.03    # since 00:00 UTC: block new entries (exits still allowed)
    drawdown_kill: float = -0.25       # from peak equity: flatten + disarm
    daily_bar_max_age_h: float = 26.0  # hours since the last daily bar CLOSED
    hourly_max_age_h: float = 2.0      # hours since the last hourly bar closed
    feed_max_gap: float = 0.01         # primary vs secondary daily close
    max_consecutive_errors: int = 3
    max_errors_24h: int = 5
    price_band: float = 0.02           # order price vs last trade
    min_notional: float = 10.0         # USD
    max_entries_per_coin_per_day: int = 1
    stop_atr_mult: float = 3.0         # catastrophe stop below entry
    heartbeat_gap_h: float = 26.0      # alert if no successful run for this long


@dataclass(frozen=True)
class Fees:
    maker_fee: float = 0.004    # Kraken Pro entry-tier maker (book of record)
    taker_fee: float = 0.009    # Coinbase Advanced entry-tier taker (pessimistic shadow)
    taker_slip: float = 0.0005


@dataclass(frozen=True)
class StrategyConfig:
    products: tuple = ("BTC-USD", "ETH-USD")
    sma_n: int = 50
    vol_target: float = 0.30
    atr_n: int = 14
    start_equity: float = 10_000.0
    daily_lookback_days: int = 150


SECONDARY = {  # cross-check sources, tried in order
    "BTC-USD": [("binance", "BTCUSDT"), ("kraken", "XBTUSD")],
    "ETH-USD": [("binance", "ETHUSDT"), ("kraken", "ETHUSD")],
}

LIMITS = Limits()
FEES = Fees()
STRATEGY = StrategyConfig()
