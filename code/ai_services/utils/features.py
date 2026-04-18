"""
AlphaFX AI Services - Feature Engineering
Transforms raw OHLCV data into supervised learning feature matrices.
Covers price-derived, momentum, volatility, microstructure, and
inter-market features used across all ML models.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Core feature builder
# ---------------------------------------------------------------------------


def build_feature_matrix(
    df: pd.DataFrame,
    target_horizon: int = 5,
    include_target: bool = True,
) -> pd.DataFrame:
    """
    Build a complete ML feature matrix from OHLCV data.

    Parameters
    ----------
    df              DataFrame with columns: open, high, low, close, volume
    target_horizon  Forward bars for the return label
    include_target  Whether to append the target column

    Returns
    -------
    DataFrame with all features (and optionally target), NaN rows dropped.
    """
    feat = pd.DataFrame(index=df.index)
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]

    # --- Price momentum features ---
    for w in [1, 2, 3, 5, 10, 21]:
        feat[f"ret_{w}"] = c.pct_change(w)

    # --- Trend indicators ---
    for w in [10, 20, 50, 100, 200]:
        feat[f"sma_{w}"] = c / c.rolling(w).mean() - 1

    feat["ema20_50_cross"] = _ema(c, 20) / _ema(c, 50) - 1
    feat["ema50_200_cross"] = _ema(c, 50) / _ema(c, 200) - 1

    # --- RSI ---
    for w in [7, 14, 21]:
        feat[f"rsi_{w}"] = _rsi(c, w) / 100.0  # normalise to [0, 1]

    # --- MACD ---
    macd = _ema(c, 12) - _ema(c, 26)
    sig = _ema(macd, 9)
    feat["macd_norm"] = macd / c
    feat["macd_signal_norm"] = sig / c
    feat["macd_hist_norm"] = (macd - sig) / c

    # --- Bollinger Band position ---
    for w in [20]:
        mid = c.rolling(w).mean()
        std = c.rolling(w).std()
        feat[f"bb_pos_{w}"] = (c - mid) / (2 * std)  # -1 = lower, +1 = upper

    # --- ATR ---
    for w in [7, 14]:
        feat[f"atr_{w}_norm"] = _atr(h, l, c, w) / c

    # --- Stochastic ---
    k, d = _stochastic(h, l, c, 14, 3)
    feat["stoch_k"] = k / 100.0
    feat["stoch_d"] = d / 100.0
    feat["stoch_cross"] = (k - d) / 100.0

    # --- Williams %R ---
    feat["williams_r"] = _williams_r(h, l, c, 14) / -100.0  # normalise to [0,1]

    # --- Volatility features ---
    for w in [5, 10, 21, 63]:
        feat[f"hv_{w}"] = c.pct_change().rolling(w).std() * np.sqrt(252)

    feat["vol_ratio_5_21"] = feat["hv_5"] / (feat["hv_21"] + 1e-9)

    # --- Volume features ---
    feat["vol_ratio"] = v / v.rolling(20).mean()
    feat["vol_trend"] = v.pct_change(5)

    # --- Candle patterns ---
    feat["body_size"] = abs(c - df["open"]) / (h - l + 1e-9)
    feat["upper_wick"] = (h - c.clip(lower=df["open"])) / (h - l + 1e-9)
    feat["lower_wick"] = (c.clip(upper=df["open"]) - l) / (h - l + 1e-9)
    feat["bullish_candle"] = (c > df["open"]).astype(float)

    # --- Price level features ---
    feat["dist_from_52w_high"] = c / h.rolling(252).max() - 1
    feat["dist_from_52w_low"] = c / l.rolling(252).min() - 1

    # --- Lag features (autoregression) ---
    for lag in [1, 2, 3, 5]:
        feat[f"close_lag_{lag}"] = c.pct_change().shift(lag)

    # --- Target: forward log return ---
    if include_target:
        fwd_ret = np.log(c.shift(-target_horizon) / c)
        feat["target_ret"] = fwd_ret
        feat["target_label"] = (fwd_ret > 0).astype(int)  # binary direction

    return feat.dropna()


# ---------------------------------------------------------------------------
# Correlation / inter-market features
# ---------------------------------------------------------------------------


def build_inter_market_features(
    pair_dfs: dict[str, pd.DataFrame],
    base_pair: str,
    lookback: int = 10,
) -> pd.DataFrame:
    """
    Add rolling correlation and relative-strength features versus other pairs.
    Useful for modelling cross-asset spillover effects.
    """
    rets = {}
    for pair, df in pair_dfs.items():
        rets[pair] = df["close"].pct_change()

    combined = pd.DataFrame(rets).dropna()
    base_ret = combined[base_pair]

    features = pd.DataFrame(index=combined.index)
    for pair in combined.columns:
        if pair == base_pair:
            continue
        roll_corr = base_ret.rolling(lookback).corr(combined[pair])
        features[f"corr_{pair}_{lookback}d"] = roll_corr
        features[f"beta_{pair}_{lookback}d"] = base_ret.rolling(lookback).cov(
            combined[pair]
        ) / (combined[pair].rolling(lookback).var() + 1e-9)

    return features.dropna()


# ---------------------------------------------------------------------------
# Sequence builder for LSTM / Transformer
# ---------------------------------------------------------------------------


def build_sequences(
    features: np.ndarray,
    targets: np.ndarray,
    lookback: int = 60,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert flat feature array into (N, lookback, n_features) tensor
    suitable for LSTM or Transformer input.
    """
    X, y = [], []
    for i in range(lookback, len(features)):
        X.append(features[i - lookback : i])
        y.append(targets[i])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ---------------------------------------------------------------------------
# Feature scaling helpers
# ---------------------------------------------------------------------------


def rolling_zscore(series: pd.Series, window: int = 60) -> pd.Series:
    """Rolling Z-score normalisation -- avoids look-ahead bias."""
    mu = series.rolling(window).mean()
    std = series.rolling(window).std()
    return (series - mu) / (std + 1e-9)


def scale_features_rolling(df: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """Apply rolling Z-score to every column."""
    return df.apply(lambda col: rolling_zscore(col, window))


# ---------------------------------------------------------------------------
# Private indicator helpers (avoid importing from Django apps)
# ---------------------------------------------------------------------------


def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=period - 1, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period - 1, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def _stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k: int = 14,
    d: int = 3,
) -> tuple[pd.Series, pd.Series]:
    lowest = low.rolling(k).min()
    highest = high.rolling(k).max()
    pct_k = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    pct_d = pct_k.rolling(d).mean()
    return pct_k, pct_d


def _williams_r(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    return -100 * (hh - close) / (hh - ll).replace(0, np.nan)
