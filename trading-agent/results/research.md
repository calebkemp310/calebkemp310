# Strategy tournament results

Generated 2026-11-07T05:38:06+00:00 from Binance spot candles. Train 2019-01-01 to 2023-12-31, held-out 2024-01-01 to 2026-11-06. Costs 0.65% per side. Trials counted: 105.

## Buy & hold benchmark (held-out)

| Asset | Sharpe | CAGR | Max DD |
|---|---|---|---|
| BTCUSDT | 0.63 | 20.6% | -53.0% |
| ETHUSDT | 0.3 | -1.9% | -67.5% |
| SOLUSDT | 0.3 | -7.0% | -76.3% |

## Summary (held-out, averaged over BTC/ETH/SOL)

| Strategy | TF | Chosen params | Mean Sharpe | Worst Max DD | Trades | Sharpe @0.10%/side | Sharpe @1.30%/side | Verdict |
|---|---|---|---|---|---|---|---|---|
| buy & hold | 1d | - | 0.41 | -76.3% | 1 each | - | - | benchmark |
| trend_sma | 1d | {'n': 50} | 0.44 | -69.7% | 88 | 0.71 | 0.11 | REJECT |
| tsmom | 1d | {'lookback': 30} | 0.10 | -71.5% | 132 | 0.52 | -0.38 | REJECT |
| donchian | 1d | {'entry_n': 40, 'exit_n': 10} | 0.03 | -51.6% | 39 | 0.19 | -0.16 | REJECT |
| rsi2_dip | 1d | {'threshold': 10} | -0.15 | -37.4% | 80 | 0.33 | -0.69 | REJECT |
| bollinger_revert_4h | 4h | {'k': 3.0} | -1.17 | -33.6% | 25 | -0.73 | -1.61 | REJECT |

## Candidates (chosen on train, scored on held-out)

| Strategy | TF | Params | Asset | Test Sharpe | Test CAGR | Test Max DD | Trades | Win % | PF | Sharpe @1.3%/side | DSR (full) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| trend_sma | 1d | {'n': 50} | BTCUSDT | 0.52 | 12.5% | -34.8% | 34 | 18 | 1.62 | 0.05 | 0.004 |
| trend_sma | 1d | {'n': 50} | ETHUSDT | 0.84 | 31.9% | -42.3% | 22 | 27 | 2.41 | 0.61 | 0.001 |
| trend_sma | 1d | {'n': 50} | SOLUSDT | -0.04 | -15.1% | -69.7% | 32 | 19 | 0.94 | -0.32 | 0.018 |
| tsmom | 1d | {'lookback': 30} | BTCUSDT | -0.18 | -10.8% | -54.9% | 54 | 18 | 0.96 | -0.91 | 0.001 |
| tsmom | 1d | {'lookback': 30} | ETHUSDT | 0.51 | 14.1% | -49.9% | 40 | 30 | 1.53 | 0.11 | 0.001 |
| tsmom | 1d | {'lookback': 30} | SOLUSDT | -0.02 | -14.1% | -71.5% | 38 | 29 | 0.93 | -0.34 | 0.029 |
| donchian | 1d | {'entry_n': 40, 'exit_n': 10} | BTCUSDT | 0.18 | 1.4% | -38.2% | 13 | 46 | 1.27 | -0.03 | 0.001 |
| donchian | 1d | {'entry_n': 40, 'exit_n': 10} | ETHUSDT | -0.12 | -8.5% | -39.7% | 14 | 43 | 0.79 | -0.32 | 0.0 |
| donchian | 1d | {'entry_n': 40, 'exit_n': 10} | SOLUSDT | 0.02 | -6.1% | -51.6% | 12 | 50 | 0.98 | -0.12 | 0.014 |
| rsi2_dip | 1d | {'threshold': 10} | BTCUSDT | -0.04 | -2.3% | -24.9% | 29 | 45 | 0.84 | -0.75 | 0.0 |
| rsi2_dip | 1d | {'threshold': 10} | ETHUSDT | -0.15 | -5.4% | -28.2% | 22 | 46 | 0.7 | -0.6 | 0.0 |
| rsi2_dip | 1d | {'threshold': 10} | SOLUSDT | -0.25 | -10.3% | -37.4% | 29 | 52 | 0.66 | -0.71 | 0.0 |
| bollinger_revert_4h | 4h | {'k': 3.0} | BTCUSDT | -0.99 | -6.3% | -17.9% | 11 | 36 | 0.21 | -1.68 | 0.0 |
| bollinger_revert_4h | 4h | {'k': 3.0} | ETHUSDT | -1.64 | -12.4% | -33.6% | 9 | 11 | 0.02 | -2.01 | 0.0 |
| bollinger_revert_4h | 4h | {'k': 3.0} | SOLUSDT | -0.87 | -6.5% | -27.4% | 5 | 20 | 0.37 | -1.14 | 0.0 |

## Verdicts

| Strategy | Grid positive | test_sharpe_mean | test_sharpe_each | test_dd_beats_hold | grid_robust | double_cost | enough_trades | dsr | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| trend_sma | 100% | FAIL | FAIL | pass | pass | pass | pass | FAIL | **REJECT** |
| tsmom | 100% | FAIL | FAIL | FAIL | pass | FAIL | pass | FAIL | **REJECT** |
| donchian | 100% | FAIL | FAIL | pass | pass | FAIL | pass | FAIL | **REJECT** |
| rsi2_dip | 67% | FAIL | FAIL | pass | FAIL | FAIL | pass | FAIL | **REJECT** |
| bollinger_revert_4h | 25% | FAIL | FAIL | pass | FAIL | FAIL | FAIL | FAIL | **REJECT** |

## Cost sensitivity (held-out Sharpe by per-side cost)

| Strategy | Asset | 0.10% | 0.25% | 0.65% | 1.30% |
|---|---|---|---|---|---|
| trend_sma | BTCUSDT | 0.92 | 0.81 | 0.52 | 0.05 |
| trend_sma | ETHUSDT | 1.03 | 0.98 | 0.84 | 0.61 |
| trend_sma | SOLUSDT | 0.19 | 0.12 | -0.05 | -0.32 |
| tsmom | BTCUSDT | 0.45 | 0.28 | -0.18 | -0.91 |
| tsmom | ETHUSDT | 0.85 | 0.76 | 0.51 | 0.11 |
| tsmom | SOLUSDT | 0.26 | 0.18 | -0.02 | -0.34 |
| donchian | BTCUSDT | 0.37 | 0.32 | 0.18 | -0.03 |
| donchian | ETHUSDT | 0.05 | 0.01 | -0.12 | -0.32 |
| donchian | SOLUSDT | 0.14 | 0.11 | 0.02 | -0.12 |
| rsi2_dip | BTCUSDT | 0.59 | 0.42 | -0.04 | -0.75 |
| rsi2_dip | ETHUSDT | 0.25 | 0.14 | -0.15 | -0.6 |
| rsi2_dip | SOLUSDT | 0.15 | 0.05 | -0.25 | -0.71 |
| bollinger_revert_4h | BTCUSDT | -0.32 | -0.51 | -0.99 | -1.68 |
| bollinger_revert_4h | ETHUSDT | -1.25 | -1.36 | -1.64 | -2.01 |
| bollinger_revert_4h | SOLUSDT | -0.61 | -0.69 | -0.87 | -1.14 |
