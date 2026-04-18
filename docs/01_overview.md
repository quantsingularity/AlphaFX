# AlphaFX Platform Overview

AlphaFX is an institutional-grade foreign exchange analytics and trading intelligence platform.
It covers the full FX analytics stack: live rate feeds, technical analysis, options pricing,
carry trade screening, portfolio risk management, and machine learning signal generation.

---

## Platform Summary

| Property          | Value                                         |
| ----------------- | --------------------------------------------- |
| Backend Framework | Django 5.0 + Django REST Framework            |
| Database          | PostgreSQL 16 (SQLite for local development)  |
| Cache             | Redis 7                                       |
| Real-time         | Django Channels + Daphne (WebSocket)          |
| AI Services       | FastAPI 0.111 + PyTorch + scikit-learn + arch |
| Frontend          | React 18 + TypeScript + Vite + Tailwind CSS   |
| Containerisation  | Docker Compose (5 services)                   |
| Test Coverage     | 88 backend tests + 20 AI service tests        |
| License           | MIT                                           |

---

## Service Architecture

| Service     | Port | Role                                                   |
| ----------- | ---- | ------------------------------------------------------ |
| backend     | 8000 | Django REST API, WebSocket ticks, Admin panel          |
| ai_services | 8001 | FastAPI ML inference (LSTM, HMM, GARCH, sentiment)     |
| frontend    | 3000 | React SPA (served via Nginx in production)             |
| nginx       | 80   | Reverse proxy, WebSocket upgrade, static file serving  |
| db          | 5432 | PostgreSQL persistent storage                          |
| redis       | 6379 | Rate cache (db 0) and channel layers (db 0), AI (db 1) |

---

## Feature Matrix

| Feature Category     | Capability                                                     |
| -------------------- | -------------------------------------------------------------- |
| Spot Rates           | 25 pairs, inverse lookup, bid/ask/mid, spread modelling        |
| Forward Rates        | Covered Interest Parity, forward points, swap cost in bps      |
| Cross Rates          | USD triangulation, direct and inverse chain                    |
| FX Options           | Garman-Kohlhagen, full Greeks, put-call parity verified        |
| Vol Surface          | 7 tenors x 5 delta strikes, smile and term structure           |
| Risk Reversals       | 25-delta RR and butterfly                                      |
| SABR Calibration     | Hagan beta=1, alpha/rho/nu from market quotes                  |
| Strategy Builder     | Multi-leg (up to 6 legs), net Greeks, payoff table             |
| Carry Trade          | All 25 pairs, carry-to-vol ratio, annualised carry             |
| PPP Analysis         | IMF fair values, deviation pct, Z-score, mean-reversion signal |
| Fixing Rates         | WM/Reuters-style daily fixing simulation                       |
| Technical Analysis   | 17 indicators, 5-level signal, pivot points, S/R, Fibonacci    |
| Correlation Matrix   | Rolling N-day correlation across arbitrary pair set            |
| HV Term Structure    | 5-252 day windows, percentile rank                             |
| Portfolio Management | Full CRUD, persistent DB, live P&L enrichment                  |
| Position Sizing      | Fixed-risk and Kelly fraction sizing                           |
| Risk Analytics       | VaR (1d/10d), Expected Shortfall, net exposure, HHI            |
| Scenario Analysis    | 10 macro scenarios including EM Crisis and Commodity Boom      |
| Trade History        | Closed position recording, duration, realised P&L              |
| Performance Stats    | Win rate, profit factor, avg win/loss, best/worst trade        |
| Price Alerts         | above/below conditions, triggered timestamp, live distance     |
| AI Forecasting       | Bidirectional LSTM with temporal attention                     |
| Regime Detection     | Gaussian HMM, 3-state Bull/Bear/Ranging                        |
| GARCH Volatility     | GJR-GARCH, skewed-t, news impact curve, multi-step forecast    |
| Sentiment Analysis   | FinBERT + lexicon fallback, per-currency aggregation           |
| Anomaly Detection    | Isolation Forest + Z-score two-layer detection                 |
| Unified AI Signal    | Weighted aggregation of all ML model outputs                   |
| WebSocket Streaming  | Live tick per-pair, 2s interval, re-subscription               |
| Admin Panel          | Django Admin for all models                                    |
| API Documentation    | OpenAPI 3.0 at /docs/ and /redoc/                              |

---

## Directory Layout

```
AlphaFX/
  code/
    backend/          Django project (API, models, WebSocket)
    ai_services/      ML inference service (FastAPI)
    frontend/         React SPA
  docs/               All platform documentation (this directory)
  infrastructure/     Nginx configuration
  docker-compose.yml  Full stack orchestration
  .env.example        Environment variable reference
```

---

## Quick Start

```bash
# Clone and configure
cp .env.example .env
# Edit .env: set SECRET_KEY, DB_PASSWORD

# Start full stack
docker compose up --build

# Access points
# Platform:    http://localhost
# API docs:    http://localhost:8000/docs/
# AI service:  http://localhost:8001/docs
# Admin:       http://localhost:8000/admin/
# WebSocket:   ws://localhost:8000/ws/rates/EURUSD/
```

---

## Data Sources

| Source           | Usage                                           | Key Required |
| ---------------- | ----------------------------------------------- | ------------ |
| ExchangeRate-API | Live spot rates (all 25 pairs from USD base)    | Optional     |
| yfinance         | Historical OHLCV for technical analysis         | No           |
| Alpha Vantage    | Intraday tick data                              | Optional     |
| Synthetic GBM    | Fallback OHLCV when live data unavailable       | No           |
| Static matrix    | Fallback spot rates when API key not configured | No           |

All analytics remain fully functional without any API keys using the synthetic fallback.
