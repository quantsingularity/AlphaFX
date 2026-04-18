"""
AlphaFX Technical Analysis Engine
RSI, MACD, Bollinger Bands, ATR, Stochastic, EMA/SMA, Ichimoku, Williams %R
"""

from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from apps.core.pricing import FALLBACK_RATES

# ─── OHLCV generation ─────────────────────────────────────────────────────────


def synthetic_ohlcv(
    pair: str, n: int = 252, seed: Optional[int] = None
) -> pd.DataFrame:
    """
    Generate synthetic OHLCV data via geometric Brownian motion.
    Seeded by pair name hash for deterministic reproducibility.
    """
    base_price = FALLBACK_RATES.get(pair.upper(), 1.0)
    rng = np.random.default_rng(seed or abs(hash(pair)) % (2**31))

    log_returns = rng.normal(0.00005, 0.006, n)
    closes = base_price * np.exp(np.cumsum(log_returns))

    highs = closes * (1 + rng.uniform(0.001, 0.006, n))
    lows = closes * (1 - rng.uniform(0.001, 0.006, n))
    opens = np.roll(closes, 1)
    opens[0] = base_price
    volumes = rng.integers(1_000_000, 5_000_000, n).astype(float)

    idx = pd.date_range(end=date.today(), periods=n, freq="B")
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=idx,
    )


# ─── Indicators ───────────────────────────────────────────────────────────────


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI using Wilder smoothing (EWMA)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD: EMA(fast) − EMA(slow), signal EMA(signal)."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_bollinger(
    close: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands: SMA ± num_std * rolling std."""
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Average True Range using Wilder smoothing."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def compute_ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def compute_sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period).mean()


def stochastic_oscillator(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """Stochastic %K and %D."""
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(d_period).mean()
    return k, d


def williams_r(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Williams %R — oscillator between -100 and 0."""
    highest_high = high.rolling(period).max()
    lowest_low = low.rolling(period).min()
    return (
        -100 * (highest_high - close) / (highest_high - lowest_low).replace(0, np.nan)
    )


def compute_ichimoku(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> dict[str, pd.Series]:
    """
    Ichimoku Cloud components:
    - Tenkan-sen (Conversion, 9-period)
    - Kijun-sen (Base, 26-period)
    - Senkou Span A (Leading Span A)
    - Senkou Span B (Leading Span B, 52-period)
    - Chikou Span (Lagging Span)
    """

    def midpoint(h, l, p):
        return (h.rolling(p).max() + l.rolling(p).min()) / 2

    tenkan = midpoint(high, low, 9)
    kijun = midpoint(high, low, 26)
    span_a = (tenkan + kijun) / 2
    span_b = midpoint(high, low, 52)
    chikou = close.shift(-26)

    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "span_a": span_a,
        "span_b": span_b,
        "chikou": chikou,
    }


def compute_vwap(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Volume-Weighted Average Price."""
    return (close * volume).cumsum() / volume.cumsum()


def pivot_points(high: float, low: float, close: float) -> dict[str, float]:
    """Classic floor pivot points: P, R1-R3, S1-S3."""
    P = (high + low + close) / 3
    R1 = 2 * P - low
    S1 = 2 * P - high
    R2 = P + (high - low)
    S2 = P - (high - low)
    R3 = high + 2 * (P - low)
    S3 = low - 2 * (high - P)
    return {
        "pivot": round(P, 5),
        "R1": round(R1, 5),
        "R2": round(R2, 5),
        "R3": round(R3, 5),
        "S1": round(S1, 5),
        "S2": round(S2, 5),
        "S3": round(S3, 5),
    }


# ─── Signal generation ────────────────────────────────────────────────────────


def trend_signal(
    close: pd.Series,
    rsi: pd.Series,
    macd: pd.Series,
    macd_sig: pd.Series,
    stoch_k: pd.Series,
) -> dict:
    """
    Multi-factor trend signal using majority vote across 5 conditions.
    Returns signal label plus score breakdown.
    """
    last_close = close.iloc[-1]
    ema50 = compute_ema(close, 50).iloc[-1]
    ema200 = compute_ema(close, 200).iloc[-1]

    bullish = 0
    bearish = 0
    signals = {}

    # Price vs EMA50
    if last_close > ema50:
        bullish += 1
        signals["price_vs_ema50"] = "bullish"
    else:
        bearish += 1
        signals["price_vs_ema50"] = "bearish"

    # Golden/Death cross
    if ema50 > ema200:
        bullish += 1
        signals["ema50_vs_ema200"] = "bullish"
    else:
        bearish += 1
        signals["ema50_vs_ema200"] = "bearish"

    # RSI
    rsi_val = float(rsi.iloc[-1])
    if rsi_val > 55:
        bullish += 1
        signals["rsi"] = "bullish"
    elif rsi_val < 45:
        bearish += 1
        signals["rsi"] = "bearish"
    else:
        signals["rsi"] = "neutral"

    # MACD
    if macd.iloc[-1] > macd_sig.iloc[-1]:
        bullish += 1
        signals["macd"] = "bullish"
    else:
        bearish += 1
        signals["macd"] = "bearish"

    # Stochastic %K
    stoch_val = float(stoch_k.iloc[-1])
    if stoch_val > 60:
        bullish += 1
        signals["stochastic"] = "bullish"
    elif stoch_val < 40:
        bearish += 1
        signals["stochastic"] = "bearish"
    else:
        signals["stochastic"] = "neutral"

    if bullish >= 4:
        overall = "STRONG_BULLISH"
    elif bullish == 3:
        overall = "BULLISH"
    elif bearish >= 4:
        overall = "STRONG_BEARISH"
    elif bearish == 3:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"

    return {
        "signal": overall,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "component_signals": signals,
    }


# ─── Full analysis ────────────────────────────────────────────────────────────


def full_analysis(pair: str, n: int = 252) -> dict:
    """
    Run complete technical analysis suite on a pair.
    Returns indicators, signal, volatility, OHLCV history, pivot points.
    """
    df = synthetic_ohlcv(pair, n)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    rsi = compute_rsi(close)
    macd_line, macd_signal, macd_hist = compute_macd(close)
    bb_upper, bb_mid, bb_lower = compute_bollinger(close)
    atr = compute_atr(high, low, close)
    ema20 = compute_ema(close, 20)
    ema50 = compute_ema(close, 50)
    ema200 = compute_ema(close, 200)
    k, d = stochastic_oscillator(high, low, close)
    wr = williams_r(high, low, close)
    vwap = compute_vwap(close, volume)
    ichimoku = compute_ichimoku(high, low, close)

    signal_data = trend_signal(close, rsi, macd_line, macd_signal, k)

    returns = close.pct_change().dropna()
    daily_vol = float(returns.std())
    annual_vol = daily_vol * np.sqrt(252) * 100

    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    change = (last - prev) / prev * 100

    pivots = pivot_points(
        float(high.iloc[-1]),
        float(low.iloc[-1]),
        float(close.iloc[-1]),
    )

    hist_data = []
    for i in range(min(100, len(df))):
        row = df.iloc[-(100 - i)]
        hist_data.append(
            {
                "date": str(row.name.date()),
                "open": round(float(row["open"]), 5),
                "high": round(float(row["high"]), 5),
                "low": round(float(row["low"]), 5),
                "close": round(float(row["close"]), 5),
                "volume": int(row["volume"]),
            }
        )

    return {
        "pair": pair.upper(),
        "current_price": round(last, 5),
        "change_pct": round(change, 4),
        "annualized_volatility_pct": round(annual_vol, 2),
        "signal": signal_data["signal"],
        "bullish_count": signal_data["bullish_count"],
        "bearish_count": signal_data["bearish_count"],
        "component_signals": signal_data["component_signals"],
        "pivot_points": pivots,
        "indicators": {
            "rsi_14": round(float(rsi.iloc[-1]), 2),
            "macd": round(float(macd_line.iloc[-1]), 6),
            "macd_signal": round(float(macd_signal.iloc[-1]), 6),
            "macd_hist": round(float(macd_hist.iloc[-1]), 6),
            "bb_upper": round(float(bb_upper.iloc[-1]), 5),
            "bb_mid": round(float(bb_mid.iloc[-1]), 5),
            "bb_lower": round(float(bb_lower.iloc[-1]), 5),
            "atr_14": round(float(atr.iloc[-1]), 6),
            "ema_20": round(float(ema20.iloc[-1]), 5),
            "ema_50": round(float(ema50.iloc[-1]), 5),
            "ema_200": round(float(ema200.iloc[-1]), 5),
            "stoch_k": round(float(k.iloc[-1]), 2),
            "stoch_d": round(float(d.iloc[-1]), 2),
            "williams_r": round(float(wr.iloc[-1]), 2),
            "vwap": round(float(vwap.iloc[-1]), 5),
            "ichimoku_tenkan": round(float(ichimoku["tenkan"].iloc[-1]), 5),
            "ichimoku_kijun": round(float(ichimoku["kijun"].iloc[-1]), 5),
            "ichimoku_span_a": round(float(ichimoku["span_a"].iloc[-1]), 5),
            "ichimoku_span_b": round(float(ichimoku["span_b"].iloc[-1]), 5),
        },
        "ohlcv": hist_data,
    }


def correlation_matrix(pairs: list[str], n: int = 60) -> dict:
    """Rolling correlation matrix across pairs (returns-based)."""
    series = {}
    for pair in pairs:
        df = synthetic_ohlcv(pair, n)
        series[pair] = df["close"].pct_change().dropna()

    combined = pd.DataFrame(series).dropna()
    corr = combined.corr()

    return {
        "pairs": list(corr.columns),
        "matrix": [
            [round(float(corr.iloc[i, j]), 4) for j in range(len(corr.columns))]
            for i in range(len(corr.index))
        ],
        "lookback_days": n,
    }
