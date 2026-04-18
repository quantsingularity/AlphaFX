# AlphaFX Quantitative Models

This document describes the mathematical models underlying AlphaFX analytics.

---

## Spot Rate Retrieval

Spot rates are sourced from a 25-pair fallback matrix covering majors,
minors, and selected EM pairs. The lookup chain is:

```
1. Direct lookup:   EURUSD -> FALLBACK_RATES["EURUSD"]
2. Inverse lookup:  USDEUR -> 1 / FALLBACK_RATES["EURUSD"]
3. Triangulation:   EURGBP -> EURUSD / GBPUSD
4. Default:         1.0
```

When ExchangeRate-API is configured, live rates are fetched and cached for 60 seconds.

### Pair coverage

| Category | Pairs                                                          |
| -------- | -------------------------------------------------------------- |
| Major    | EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD         |
| Crosses  | EURGBP, EURJPY, GBPJPY, EURCHF, AUDJPY, GBPCHF, CADJPY, AUDNZD |
| Minor    | USDSGD, USDHKD, EURNOK, EURSEK, GBPNOK, GBPSEK, AUDCAD         |
| EM       | USDMXN, USDZAR, USDTRY                                         |

---

## Forward Rates (Covered Interest Parity)

The no-arbitrage forward rate formula under continuous compounding:

```
F = S * exp((r_q - r_b) * T)
```

Where S is the spot rate, r_q is the domestic (quote) rate, r_b is the
foreign (base) rate, and T = tenor_days / 365.

Forward points are expressed in pips:

```
forward_points = (F - S) * 10000
```

Annualised swap cost in basis points:

```
swap_cost_bps = (r_q - r_b) * 10000
```

### Interest rate matrix

| Currency | Rate   | Central Bank              |
| -------- | ------ | ------------------------- |
| USD      | 5.33%  | Federal Reserve           |
| EUR      | 4.25%  | ECB                       |
| GBP      | 5.25%  | Bank of England           |
| JPY      | 0.10%  | Bank of Japan             |
| CHF      | 1.50%  | SNB                       |
| AUD      | 4.35%  | Reserve Bank of Australia |
| NZD      | 5.50%  | RBNZ                      |
| CAD      | 5.00%  | Bank of Canada            |
| TRY      | 50.00% | CBRT                      |
| ZAR      | 8.20%  | SARB                      |

---

## Garman-Kohlhagen Options Pricing

Extension of Black-Scholes for FX options. The base interest rate
plays the role of the continuous dividend yield.

### Option price formulas

Call: C = S _ exp(-r_f _ T) _ N(d1) - K _ exp(-r*d * T) _ N(d2)
Put: P = K _ exp(-r*d * T) _ N(-d2) - S _ exp(-r*f * T) \_ N(-d1)

Where:

```
d1 = [ln(S/K) + (r_d - r_f + sigma^2 / 2) * T] / (sigma * sqrt(T))
d2 = d1 - sigma * sqrt(T)
```

### Greeks

| Greek | Call Formula                                    | Units             |
| ----- | ----------------------------------------------- | ----------------- |
| Delta | exp(-r*f * T) \_ N(d1)                          | Price per price   |
| Gamma | exp(-r*f * T) _ N'(d1) / (S _ sigma \_ sqrt(T)) | Delta per price   |
| Vega  | S _ exp(-r_f _ T) _ N'(d1) _ sqrt(T) / 100      | Price per 1% vol  |
| Theta | Complex (per day, see source)                   | Price per day     |
| Rho   | K _ T _ exp(-r*d * T) \_ N(d2) / 100            | Price per 1% rate |

### Put-call parity (FX)

```
C - P = S * exp(-r_f * T) - K * exp(-r_d * T)
```

Verified in the test suite to within 5e-5 tolerance.

---

## Implied Volatility Surface

The surface is parameterised across 7 tenors and 5 delta strikes.

### Tenors

| Label | Calendar days |
| ----- | ------------- |
| 1D    | 1             |
| 7D    | 7             |
| 1M    | 30            |
| 2M    | 60            |
| 3M    | 90            |
| 6M    | 180           |
| 1Y    | 365           |

### Term structure adjustment

```
term_vol = base_vol * (1 + 0.015 * (T/365)^0.4)
```

### Smile adjustment (symmetric)

```
smile_adj = 1 + 0.002 * ((delta - 50) / 10)^2
```

---

## SABR Smile Calibration

AlphaFX implements the Hagan et al. SABR beta=1 (log-normal backbone)
approximation for FX volatility smile calibration.

### Parameter mapping from market quotes

| Market observable | SABR parameter           |
| ----------------- | ------------------------ |
| ATM volatility    | alpha (vol-of-vol scale) |
| 25d Risk Reversal | rho (skew/correlation)   |
| 25d Butterfly     | nu (vol of vol)          |

### SABR implied volatility approximation

For F != K:

```
vol = alpha / (FK)^((1-beta)/2) * (z / chi(z))
```

where z = (nu/alpha) _ (FK)^((1-beta)/2) _ ln(F/K)

---

## Carry Trade Screening

Net carry in basis points per pair:

```
carry_bps = |r_base - r_quote| * 10000
```

Long the higher-yielding currency, short the lower-yielding currency.

Carry-to-volatility ratio (Sharpe proxy):

```
carry_to_vol = |r_base - r_quote| / sigma_annualised
```

---

## Purchasing Power Parity

Deviation from PPP fair value:

```
deviation_pct = (spot - ppp_rate) / ppp_rate * 100
```

Z-score (number of annualised volatilities from fair value):

```
z_score = deviation_pct / (annualised_vol * 100)
```

Mean reversion signal thresholds:

| Threshold       | Signal      |
| --------------- | ----------- |
| z > +2.0        | STRONG_SELL |
| +1.0 < z < +2.0 | SELL        |
| -1.0 < z < +1.0 | NEUTRAL     |
| -2.0 < z < -1.0 | BUY         |
| z < -2.0        | STRONG_BUY  |

---

## Risk Analytics

### Value at Risk

AlphaFX uses a Monte Carlo simulation of 252-day GBM paths per position.
Pair-specific daily volatility is used rather than a global assumption.

```
sigma_daily = pair_specific_vol  (e.g. 0.006 for EURUSD)
log_ret_i ~ N(0.00005, sigma_daily)
rates_path = spot * exp(cumsum(log_ret_i))
```

VaR at confidence level c over holding period h:

```
VaR_h = percentile(portfolio_pnl * sqrt(h), (1-c)*100)
```

VaR_10d uses sqrt(10) scaling of the 1d series.

### Expected Shortfall

```
ES = mean(portfolio_pnl[portfolio_pnl <= VaR])
```

### Herfindahl-Hirschman Index

```
HHI = sum(w_i^2)   where  w_i = notional_i / total_notional
```

Range: 0 (fully diversified) to 1 (single-position concentration).

---

## Technical Indicators

| Indicator       | Formula summary                                                |
| --------------- | -------------------------------------------------------------- | ---- | --- | ---- | -------------- |
| RSI (period p)  | 100 - 100/(1 + AvgGain_EWMA / AvgLoss_EWMA), Wilder EWMA       |
| MACD            | EMA(12) - EMA(26); signal = EMA(9) of MACD line                |
| Bollinger Bands | SMA(20) +/- 2 \* RollingStd(20)                                |
| ATR             | max(H-L,                                                       | H-Cp | ,   | L-Cp | ); Wilder EWMA |
| Stochastic %K   | 100 \* (C - LowestLow(14)) / (HighestHigh(14) - LowestLow(14)) |
| Stochastic %D   | SMA(3) of %K                                                   |
| Williams %R     | -100 \* (HighestHigh - C) / (HighestHigh - LowestLow)          |
| Ichimoku Tenkan | (Max(9) + Min(9)) / 2                                          |
| Ichimoku Kijun  | (Max(26) + Min(26)) / 2                                        |
| Span A          | (Tenkan + Kijun) / 2                                           |
| Span B          | (Max(52) + Min(52)) / 2                                        |
| VWAP            | Cumsum(C \* V) / Cumsum(V)                                     |
| Pivot (P)       | (H + L + C) / 3                                                |
| R1              | 2P - L                                                         |
| S1              | 2P - H                                                         |
