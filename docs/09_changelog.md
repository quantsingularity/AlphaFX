# AlphaFX Changelog

---

## v2.1.0 - Current Release

### Added

| Feature                   | Description                                                     |
| ------------------------- | --------------------------------------------------------------- |
| AI Services microservice  | Separate FastAPI service on port 8001                           |
| LSTM Forecaster           | BiLSTM with temporal attention, PyTorch + sklearn fallback      |
| Regime Detector           | Gaussian HMM, 3-state market classification                     |
| GARCH Volatility          | GJR-GARCH with skewed-t, news impact curve, multi-step forecast |
| Anomaly Detector          | Isolation Forest + Z-score two-layer detection                  |
| Sentiment Analysis        | FinBERT + lexicon fallback, currency-level aggregation          |
| Signal Aggregator         | Weighted ensemble of all ML model outputs                       |
| Feature Engineering       | 40+ ML features from OHLCV with rolling Z-score normalisation   |
| Training Pipeline         | Batch training script for all major pairs                       |
| docs/ directory           | 9 documentation files with tables and examples                  |
| code/ directory structure | Separated backend, ai_services, and frontend                    |

---

## v2.0.0 - Django Edition

### Framework migration

| Before (FastAPI)     | After (Django)                       |
| -------------------- | ------------------------------------ |
| FastAPI + Uvicorn    | Django 5.0 + DRF + Daphne (ASGI)     |
| In-memory dict store | PostgreSQL via Django ORM            |
| No WebSockets        | Django Channels, live tick streaming |
| No admin             | Django Admin panel                   |
| No caching           | Redis via django-redis               |

### New features in v2.0.0

| Feature                      | Description                                       |
| ---------------------------- | ------------------------------------------------- |
| Trade history                | Closed position recording with TradeHistory model |
| Portfolio performance        | Win rate, profit factor, avg win/loss             |
| Price alerts                 | CRUD, above/below conditions, auto-trigger        |
| Risk reversals and butterfly | 25-delta RR and fly endpoints                     |
| SABR smile calibration       | Hagan beta=1 from ATM vol, RR, butterfly          |
| Multi-leg strategy builder   | Up to 6 legs, net Greeks, payoff table            |
| WM/R fixing rates            | Daily fixing rate simulation                      |
| Support and resistance       | Swing-based clustering, top 5 levels              |
| Fibonacci levels             | Retracement and extension levels                  |
| HV term structure            | 5 to 252 day windows with percentile rank         |
| Williams %R indicator        | Added to technical engine and scan                |
| Ichimoku Cloud               | Tenkan, Kijun, Span A/B, Chikou                   |
| VWAP                         | Cumulative volume-weighted average price          |
| Pivot points                 | Classic floor pivots P, R1-R3, S1-S3              |
| 5-level signal strength      | STRONG_BULLISH / STRONG_BEARISH added             |
| 10 macro scenarios           | Added EM Crisis and Commodity Boom                |
| Carry-to-vol ratio           | Sharpe proxy in all carry screener results        |
| PPP Z-score and signal       | Mean-reversion signal based on Z-score            |

### Test improvements

| Version | Tests |
| ------- | ----- |
| v1.0.0  | 30    |
| v2.0.0  | 88    |
| v2.1.0  | 108   |

---

## v1.0.0 - Original FastAPI Edition

### Initial features

| Category  | Features                                                                 |
| --------- | ------------------------------------------------------------------------ |
| Rates     | 20-pair spot rates, forward, cross-rate                                  |
| Options   | Garman-Kohlhagen pricer, Greeks, vol surface                             |
| Technical | RSI, MACD, Bollinger, ATR, Stochastic, EMA, 13 total                     |
| Portfolio | In-memory CRUD, VaR, 8 scenarios                                         |
| Analytics | Position sizing, R:R, swap rates, PPP                                    |
| Frontend  | 7 pages: Dashboard, Rates, Charts, Portfolio, Options, Carry, Calculator |
| Tests     | 30 unit tests                                                            |
