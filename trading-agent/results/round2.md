# Round 2 results (widened search)

Generated 2026-11-07T05:38:08+00:00. Train 2019-01-01 to 2023-12-31, held-out 2024-01-01 to 2026-11-06. Costs 0.65% per side. Trials pooled for deflated Sharpe: 184 (105 from round 1).

## Summary (held-out; per-coin strategies averaged over BTC/ETH/SOL)

| Strategy | TF | Chosen params | Mean Sharpe | Worst Max DD | Trades | Sharpe @0.10% | Sharpe @1.30% | Best DSR | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| buy & hold | 1d | - | 0.41 | -76.3% | - | - | - | - | benchmark |
| trend_band | 1d | {'n': 50, 'band': 0.05} | 0.24 | -66.0% | 37 | 0.35 | 0.11 | 0.072 | WATCH |
| weekly_trend | 1w | {'n': 10} | 0.17 | -75.9% | 44 | 0.31 | 0.01 | 0.003 | REJECT |
| vol_target_trend | 1d | {'n': 50, 'target': 0.3} | 0.54 | -41.9% | 88 | 0.79 | 0.24 | 0.057 | WATCH |
| btc_regime_trend | 1d | {'n': 100} | 0.28 | -72.5% | 65 | 0.48 | 0.04 | 0.035 | REJECT |
| squeeze_breakout | 1d | {'pct': 0.5} | 0.28 | -48.8% | 37 | 0.43 | 0.10 | 0.001 | REJECT |
| dual_momentum (portfolio) | 1d | {'lookback': 30} | -0.45 | -75.3% | 123 | 0.42 | -1.44 | 0.01 | REJECT |
| equal-weight hold (portfolio benchmark) | 1d | - | 0.38 | -62.3% | - | - | - | - | benchmark |

## Gates

| Strategy | Grid positive | test_sharpe_mean | test_sharpe_each | test_dd_beats_hold | grid_robust | double_cost | enough_trades | dsr | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| trend_band | 100% | FAIL | pass | pass | pass | pass | pass | FAIL | **WATCH** |
| weekly_trend | 100% | FAIL | FAIL | pass | pass | pass | pass | FAIL | **REJECT** |
| vol_target_trend | 100% | pass | pass | pass | pass | pass | pass | FAIL | **WATCH** |
| btc_regime_trend | 100% | FAIL | FAIL | pass | pass | pass | pass | FAIL | **REJECT** |
| squeeze_breakout | 78% | FAIL | FAIL | pass | pass | pass | pass | FAIL | **REJECT** |
| dual_momentum | 100% | FAIL | n/a | FAIL | pass | FAIL | pass | FAIL | **REJECT** |

## Per-coin held-out detail

| Strategy | Coin | Sharpe | CAGR | Max DD | Trades | Win % | PF | Exposure |
|---|---|---|---|---|---|---|---|---|
| trend_band | BTCUSDT | 0.3 | 4.7% | -39.6% | 11 | 36 | 1.43 | 60% |
| trend_band | ETHUSDT | 0.38 | 7.3% | -50.1% | 12 | 42 | 1.52 | 49% |
| trend_band | SOLUSDT | 0.05 | -10.7% | -66.0% | 14 | 36 | 0.98 | 52% |
| weekly_trend | BTCUSDT | 0.33 | 5.7% | -39.7% | 15 | 40 | 1.51 | 53% |
| weekly_trend | ETHUSDT | 0.25 | 1.4% | -59.6% | 13 | 38 | 1.36 | 48% |
| weekly_trend | SOLUSDT | -0.06 | -17.4% | -75.9% | 16 | 31 | 0.83 | 48% |
| vol_target_trend | BTCUSDT | 0.6 | 12.7% | -29.9% | 34 | 18 | 1.76 | 56% |
| vol_target_trend | ETHUSDT | 0.8 | 18.2% | -25.5% | 22 | 27 | 2.48 | 49% |
| vol_target_trend | SOLUSDT | 0.22 | 2.4% | -41.9% | 32 | 19 | 1.24 | 51% |
| btc_regime_trend | BTCUSDT | 0.5 | 11.5% | -42.3% | 20 | 20 | 1.84 | 52% |
| btc_regime_trend | ETHUSDT | 0.36 | 6.4% | -52.4% | 18 | 17 | 1.59 | 46% |
| btc_regime_trend | SOLUSDT | -0.01 | -13.8% | -72.5% | 27 | 22 | 0.64 | 47% |
| squeeze_breakout | BTCUSDT | 0.6 | 13.6% | -40.3% | 12 | 42 | 2.06 | 35% |
| squeeze_breakout | ETHUSDT | -0.14 | -8.5% | -48.8% | 12 | 42 | 0.79 | 25% |
| squeeze_breakout | SOLUSDT | 0.38 | 7.4% | -45.5% | 13 | 38 | 1.66 | 31% |
