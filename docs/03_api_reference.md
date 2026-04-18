# AlphaFX API Reference

Base URL: http://localhost:8000/api/v1
AI Services Base URL: http://localhost:8001

Interactive documentation is available at /docs/ (Swagger UI) and /redoc/ (ReDoc).

---

## Authentication

All endpoints are publicly accessible by default (AllowAny permission class).
To enable authenticated-only access, change DEFAULT_PERMISSION_CLASSES in settings.

JWT tokens are available via the djangorestframework-simplejwt endpoints
at /api/token/ and /api/token/refresh/.

---

## Rates Endpoints

| Method | Path                                | Description                              |
| ------ | ----------------------------------- | ---------------------------------------- |
| GET    | /rates/                             | All major pair live quotes               |
| GET    | /rates/all-pairs/                   | Full pair list (major + minor + EM)      |
| GET    | /rates/spot/{pair}/                 | Single pair bid/ask/mid/spread           |
| POST   | /rates/spot/                        | Batch spot quotes (up to 20 pairs)       |
| POST   | /rates/forward/                     | Forward rate via Covered Interest Parity |
| POST   | /rates/cross/                       | Cross-rate via USD triangulation         |
| POST   | /rates/option/                      | Garman-Kohlhagen FX option pricer        |
| GET    | /rates/option/vol-surface/{pair}/   | Implied volatility surface               |
| GET    | /rates/option/risk-reversal/{pair}/ | 25-delta risk reversal and butterfly     |
| GET    | /rates/carry/                       | Carry trade opportunity screener         |
| GET    | /rates/interest-rates/              | Central bank policy rates                |
| GET    | /rates/calendar/                    | Economic event calendar                  |
| GET    | /rates/pip-value/{pair}/            | Pip value in USD for a given notional    |

### POST /rates/forward/ - Request fields

| Field      | Type    | Required | Description                           |
| ---------- | ------- | -------- | ------------------------------------- |
| base       | string  | yes      | Base currency code (e.g. EUR)         |
| quote      | string  | yes      | Quote currency code (e.g. USD)        |
| tenor_days | integer | yes      | Tenor in calendar days (1-3650)       |
| base_rate  | float   | no       | Override base currency interest rate  |
| quote_rate | float   | no       | Override quote currency interest rate |

### POST /rates/option/ - Request fields

| Field       | Type   | Required | Description                               |
| ----------- | ------ | -------- | ----------------------------------------- |
| base        | string | yes      | Base currency (e.g. EUR)                  |
| quote       | string | yes      | Quote currency (e.g. USD)                 |
| spot        | float  | yes      | Spot rate (> 0)                           |
| strike      | float  | yes      | Strike price (> 0)                        |
| tenor_days  | int    | yes      | Expiry in calendar days (1-3650)          |
| volatility  | float  | yes      | Implied volatility as decimal (e.g. 0.08) |
| base_rate   | float  | yes      | Foreign (base) interest rate              |
| quote_rate  | float  | yes      | Domestic (quote) interest rate            |
| option_type | string | no       | "call" (default) or "put"                 |
| notional    | float  | no       | Contract notional (default 1,000,000)     |

### GET /rates/carry/ - Query parameters

| Parameter     | Type  | Default | Description                             |
| ------------- | ----- | ------- | --------------------------------------- |
| min_carry_bps | float | 0.0     | Minimum carry threshold in basis points |

---

## Technical Analysis Endpoints

| Method | Path                                  | Description                          |
| ------ | ------------------------------------- | ------------------------------------ |
| GET    | /technical/{pair}/                    | Full indicator suite for a pair      |
| GET    | /technical/                           | Signal scan across all major pairs   |
| GET    | /technical/correlation/               | Rolling correlation matrix           |
| GET    | /technical/{pair}/support-resistance/ | Swing-based support and resistance   |
| GET    | /technical/{pair}/fibonacci/          | Fibonacci retracement/extensions     |
| GET    | /technical/{pair}/volatility/         | Historical volatility term structure |

### Common query parameters

| Parameter | Type | Default | Range  | Description   |
| --------- | ---- | ------- | ------ | ------------- |
| n         | int  | 252     | 50-500 | Lookback bars |

### Indicator reference

| Indicator       | Key in response            | Normalisation   |
| --------------- | -------------------------- | --------------- |
| RSI (14)        | indicators.rsi_14          | 0 to 100        |
| MACD line       | indicators.macd            | Raw price units |
| MACD signal     | indicators.macd_signal     | Raw price units |
| MACD histogram  | indicators.macd_hist       | Raw price units |
| Bollinger upper | indicators.bb_upper        | Price level     |
| Bollinger mid   | indicators.bb_mid          | Price level     |
| Bollinger lower | indicators.bb_lower        | Price level     |
| ATR (14)        | indicators.atr_14          | Price units     |
| EMA 20          | indicators.ema_20          | Price level     |
| EMA 50          | indicators.ema_50          | Price level     |
| EMA 200         | indicators.ema_200         | Price level     |
| Stochastic %K   | indicators.stoch_k         | 0 to 100        |
| Stochastic %D   | indicators.stoch_d         | 0 to 100        |
| Williams %R     | indicators.williams_r      | -100 to 0       |
| VWAP            | indicators.vwap            | Price level     |
| Ichimoku Tenkan | indicators.ichimoku_tenkan | Price level     |
| Ichimoku Kijun  | indicators.ichimoku_kijun  | Price level     |

### Signal values

| Signal         | Bullish signals | Bearish signals |
| -------------- | --------------- | --------------- |
| STRONG_BULLISH | 5               | 0-1             |
| BULLISH        | 4               | 0-2             |
| NEUTRAL        | 2-3             | 2-3             |
| BEARISH        | 0-2             | 4               |
| STRONG_BEARISH | 0-1             | 5               |

---

## Portfolio Endpoints

| Method | Path                                 | Description                    |
| ------ | ------------------------------------ | ------------------------------ |
| GET    | /portfolios/                         | List all portfolios            |
| POST   | /portfolios/                         | Create portfolio               |
| GET    | /portfolios/{id}/                    | Portfolio detail with live P&L |
| PATCH  | /portfolios/{id}/                    | Update name or description     |
| DELETE | /portfolios/{id}/                    | Delete portfolio + positions   |
| GET    | /portfolios/{id}/positions/          | List open positions with P&L   |
| POST   | /portfolios/{id}/positions/          | Open a new FX position         |
| GET    | /portfolios/{id}/positions/{pos_id}/ | Single position detail         |
| DELETE | /portfolios/{id}/positions/{pos_id}/ | Close position, record history |
| GET    | /portfolios/{id}/risk/               | VaR, ES, exposure, HHI         |
| POST   | /portfolios/{id}/scenarios/          | Run 10 macro scenarios         |
| GET    | /portfolios/{id}/history/            | Closed trade history           |
| GET    | /portfolios/{id}/performance/        | Win rate and performance stats |
| GET    | /portfolios/alerts/                  | List price alerts              |
| POST   | /portfolios/alerts/                  | Create price alert             |
| GET    | /portfolios/alerts/{id}/             | Check alert, auto-trigger      |
| DELETE | /portfolios/alerts/{id}/             | Delete alert                   |

### POST /portfolios/{id}/positions/ - Request fields

| Field       | Type   | Required | Description                            |
| ----------- | ------ | -------- | -------------------------------------- |
| pair        | string | yes      | Currency pair (e.g. EURUSD)            |
| side        | string | yes      | "buy" or "sell"                        |
| notional    | float  | yes      | Position size in base currency units   |
| entry_rate  | float  | yes      | Entry price                            |
| stop_loss   | float  | no       | Stop loss level                        |
| take_profit | float  | no       | Take profit level                      |
| leverage    | float  | no       | Leverage multiplier (1-500, default 1) |
| notes       | string | no       | Optional trade notes                   |

### GET /portfolios/{id}/risk/ - Query parameters

| Parameter  | Type  | Default | Description                |
| ---------- | ----- | ------- | -------------------------- |
| confidence | float | 0.99    | VaR confidence level (0-1) |

### Scenario list

| Scenario Name                     | Currency shocks             |
| --------------------------------- | --------------------------- |
| USD Strength +5%                  | USD +5%                     |
| USD Weakness -5%                  | USD -5%                     |
| EUR Rally +3%                     | EUR +3%                     |
| EUR Selloff -3%                   | EUR -3%                     |
| JPY Safe Haven +10%               | JPY +10%                    |
| JPY Carry Unwind -10%             | JPY -10%                    |
| Risk-Off (USD+5, JPY+3, CHF+2)    | USD +5%, JPY +3%, CHF +2%   |
| Risk-On (USD-3, AUD+2, NZD+2)     | USD -3%, AUD +2%, NZD +2%   |
| EM Crisis (USD+8, TRY-20, ZAR-10) | USD +8%, TRY -20%, ZAR -10% |
| Commodity Boom (AUD+5, CAD+4)     | AUD +5%, CAD +4%, USD -2%   |

---

## Analytics Endpoints

| Method | Path                                | Description                          |
| ------ | ----------------------------------- | ------------------------------------ |
| POST   | /analytics/position-size/           | Fixed-risk and Kelly position sizing |
| POST   | /analytics/risk-reward/             | Risk/reward ratio and break-even WR  |
| POST   | /analytics/pip-value/               | Pip value for any notional           |
| GET    | /analytics/swap-rates/              | Forward swap rates for all pairs     |
| GET    | /analytics/purchasing-power-parity/ | PPP deviation, Z-score, signal       |
| POST   | /analytics/sabr-smile/              | SABR smile calibration               |
| POST   | /analytics/strategy-builder/        | Multi-leg FX options strategy        |
| GET    | /analytics/fixing-rates/            | WM/R-style FX fixing rates           |

### POST /analytics/position-size/ - Request fields

| Field           | Type   | Required | Description                              |
| --------------- | ------ | -------- | ---------------------------------------- |
| account_balance | float  | yes      | Total account balance in USD             |
| risk_pct        | float  | no       | Percent of balance to risk (default 1.0) |
| stop_loss_pips  | float  | yes      | Stop loss distance in pips               |
| pair            | string | yes      | Currency pair                            |
| leverage        | float  | no       | Position leverage (default 1.0)          |

### POST /analytics/strategy-builder/ - Leg fields

| Field       | Type   | Required | Description               |
| ----------- | ------ | -------- | ------------------------- |
| option_type | string | yes      | "call" or "put"           |
| strike      | float  | yes      | Strike price              |
| tenor_days  | int    | yes      | Days to expiry            |
| notional    | float  | no       | Leg notional (default 1M) |
| direction   | string | no       | "long" or "short"         |

---

## AI Services Endpoints

Base URL: http://localhost:8001

| Method | Path                  | Description                                   |
| ------ | --------------------- | --------------------------------------------- |
| GET    | /ai/health            | Service health check                          |
| POST   | /ai/forecast/{pair}   | LSTM price direction probability              |
| GET    | /ai/regime/{pair}     | HMM market regime and state probabilities     |
| GET    | /ai/volatility/{pair} | GARCH conditional vol forecast + NIC          |
| POST   | /ai/sentiment         | Batch headline sentiment analysis             |
| GET    | /ai/sentiment/macro   | Macro risk-on/off index from sample headlines |
| GET    | /ai/anomaly/{pair}    | Anomaly detection on recent price history     |
| POST   | /ai/signal/{pair}     | Aggregated ML trading signal                  |

### POST /ai/signal/{pair} - Response fields

| Field                     | Type   | Description                                     |
| ------------------------- | ------ | ----------------------------------------------- |
| signal                    | string | BUY, SELL, or NEUTRAL                           |
| direction_score           | float  | Weighted score in [-1, +1]                      |
| confidence                | float  | Absolute confidence in [0, 1]                   |
| regime                    | string | BULL, BEAR, or RANGING                          |
| vol_regime                | string | LOW_VOL, NORMAL, HIGH_VOL, or EXTREME_VOL       |
| components.lstm.prob      | float  | LSTM up-probability [0, 1]                      |
| components.regime.probs   | dict   | HMM state posterior probabilities               |
| components.garch_vol      | dict   | GARCH daily vol and regime                      |
| components.sentiment      | dict   | Net sentiment score and signal                  |
| components.technical      | dict   | Technical signal and indicator snapshot         |
| risk_adjustment.size_pct  | float  | Suggested position size as pct of normal        |
| risk_adjustment.stop_mult | float  | ATR multiplier for stop loss in high-vol regime |

---

## WebSocket API

Connection: ws://host:8000/ws/rates/{PAIR}/

| PAIR value | Behavior                                   |
| ---------- | ------------------------------------------ |
| EURUSD     | Stream ticks for EURUSD only               |
| all        | Stream ticks for all major pairs every 2 s |
| GBPUSD     | Stream ticks for GBPUSD only               |

### Tick message shape

```json
{
  "type": "tick",
  "timestamp": "2025-01-01T12:00:00+00:00",
  "ticks": [
    {
      "pair": "EURUSD",
      "bid": 1.08415,
      "ask": 1.08427,
      "mid": 1.08421,
      "change": 0.3,
      "timestamp": "2025-01-01T12:00:00+00:00"
    }
  ]
}
```

---

## HTTP Status Codes

| Code | Meaning                                           |
| ---- | ------------------------------------------------- |
| 200  | Success                                           |
| 201  | Created (portfolio, position, alert)              |
| 204  | Deleted (no response body)                        |
| 400  | Bad request / validation error                    |
| 404  | Resource not found                                |
| 422  | Unprocessable entity (cannot compute pip value)   |
| 429  | Rate limit exceeded (100/min anon, 1000/min auth) |
| 500  | Internal server error                             |
