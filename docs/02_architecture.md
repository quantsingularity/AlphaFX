# AlphaFX Architecture

This document describes the system architecture, service topology, data flow,
and design decisions behind the AlphaFX platform.

---

## High-Level Architecture

```
Browser / API Client
        |
        v
   Nginx (port 80)
   +-----------------------------------------+
   | /             -> frontend:80 (React SPA)|
   | /api/v1/      -> backend:8000 (Django)  |
   | /ws/          -> backend:8000 (Daphne)  |
   | /static/      -> local filesystem       |
   | /ai/          -> ai_services:8001       |
   +-----------------------------------------+
        |                        |
        v                        v
  Django Backend          AI Services
  (port 8000)             (port 8001)
  Daphne ASGI             FastAPI + Uvicorn
        |                        |
        v                        v
  PostgreSQL              Redis (db 1)
  Redis (db 0)            Saved model files
  Channel Layers
```

---

## Service Responsibilities

| Service     | Technology        | Responsibilities                                              |
| ----------- | ----------------- | ------------------------------------------------------------- |
| backend     | Django 5 + DRF    | REST API, WebSocket ticks, portfolio persistence, admin panel |
| ai_services | FastAPI + PyTorch | LSTM inference, HMM regime, GARCH vol, sentiment, anomaly     |
| frontend    | React 18 + Vite   | Interactive SPA, charts, forms, WebSocket consumption         |
| nginx       | Nginx alpine      | Reverse proxy, WebSocket upgrade headers, static files        |
| db          | PostgreSQL 16     | Portfolios, positions, trade history, price alerts            |
| redis       | Redis 7           | Rate cache (TTL), Django channel layers, AI service cache     |

---

## Backend Django Application Layout

```
code/backend/
  alphafx/
    settings/base.py     All configuration via django-environ
    urls.py              Root URL dispatcher
    asgi.py              ASGI app: HTTP + WebSocket via Channels
    wsgi.py              WSGI fallback
  apps/
    core/                Shared engines (no URL routing)
      pricing.py         Spot, forward, GK options, carry, vol surface
      technical.py       17 technical indicators, signal engine
      risk.py            VaR, ES, net exposure, HHI, scenarios
      data_feed.py       Live rate fetch, OHLCV, economic calendar
      exceptions.py      Uniform error envelope {error, status_code, detail}
    rates/               Rate endpoints + WebSocket producer
    portfolio/           Portfolio CRUD + persistent models
    analytics/           Quantitative calculators
    technical/           Technical analysis endpoints
```

---

## AI Services Layout

```
code/ai_services/
  models/
    lstm_forecaster.py   BiLSTM + temporal attention, PyTorch or sklearn fallback
    regime_detector.py   Gaussian HMM, 3-state market regime
    garch_vol.py         GJR-GARCH, skewed-t, multi-step vol forecast
    anomaly_detector.py  Isolation Forest + Z-score two-layer detection
  services/
    sentiment.py         FinBERT + lexicon fallback, currency aggregation
    signal_aggregator.py Weighted combination of all model outputs
  utils/
    features.py          Feature engineering: 40+ features from OHLCV
  training/
    train_all.py         Batch training pipeline, saves models to disk
  api/
    main.py              FastAPI application, 8 inference endpoints
  config.py              All AI hyperparameters in one dataclass
  tests/                 20 unit tests for all model components
```

---

## Database Schema

| Table        | Key Fields                                                        |
| ------------ | ----------------------------------------------------------------- |
| portfolio    | id (UUID), name, base_currency, initial_balance, created_at       |
| position     | id (UUID), portfolio_id, pair, side, notional, entry_rate, status |
| pricealert   | id (UUID), pair, target_price, condition, triggered, triggered_at |
| tradehistory | id (UUID), portfolio_id, entry_rate, close_rate, realized_pnl     |

All primary keys are UUID to avoid sequential ID enumeration. Positions carry
stop_loss, take_profit, leverage, notes, and close_rate for full lifecycle tracking.

---

## Caching Strategy

| Endpoint                    | Cache TTL | Key Pattern                    |
| --------------------------- | --------- | ------------------------------ |
| GET /rates/ (major pairs)   | 10 s      | major_pairs_quotes             |
| GET /technical/{pair}       | 30 s      | technical:{pair}:{n}           |
| GET /technical/ (scan)      | 30 s      | technical_scan:{n}             |
| GET /technical/correlation/ | 60 s      | correlation:{sorted_pairs}:{n} |
| Live rates via data_feed    | 30 s      | live_rates:{base}              |

Cache backend is Redis via django-redis. Cache degrades gracefully to no-cache
when Redis is unavailable (IGNORE_EXCEPTIONS=True).

---

## WebSocket Protocol

Connection URL: ws://host:8000/ws/rates/{PAIR}/

Use PAIR="all" to receive ticks for all major pairs simultaneously.

### Server messages

| Type       | Payload fields                                        |
| ---------- | ----------------------------------------------------- |
| tick       | type, timestamp, ticks[]{pair, bid, ask, mid, change} |
| subscribed | type, pair                                            |

### Client messages

| Action    | Payload fields | Effect                            |
| --------- | -------------- | --------------------------------- |
| subscribe | pair           | Switch to a different pair stream |

Ticks are broadcast every 2 seconds. Price movement is simulated as
Gaussian noise around the fallback mid with pair-specific pip size scaling.

---

## Authentication and Security

| Control           | Implementation                                 |
| ----------------- | ---------------------------------------------- |
| Authentication    | JWT via djangorestframework-simplejwt          |
| Session auth      | Django sessions (for Admin panel)              |
| Throttling (anon) | 100 requests per minute                        |
| Throttling (user) | 1000 requests per minute                       |
| CORS              | django-cors-headers, origins from env var      |
| CSRF              | Enabled for session-authenticated routes       |
| Secret key        | Loaded from environment, never hardcoded       |
| Debug mode        | Controlled by DEBUG env var, defaults to False |

---

## Error Response Envelope

All API errors return a consistent JSON envelope:

```json
{
  "error": true,
  "status_code": 404,
  "detail": "Portfolio not found."
}
```

This is enforced via the custom exception handler in apps/core/exceptions.py.
Handles both dict-shaped and list-shaped DRF error payloads.

---

## Deployment Variants

| Variant        | How to run                                   | Notes                     |
| -------------- | -------------------------------------------- | ------------------------- |
| Local dev      | python manage.py runserver                   | SQLite, no Redis required |
| Docker Compose | docker compose up --build                    | Full stack, PostgreSQL    |
| Production     | daphne alphafx.asgi:application behind nginx | Set DEBUG=False           |
| AI standalone  | uvicorn ai_services.api.main:app --port 8001 | Separate process          |
