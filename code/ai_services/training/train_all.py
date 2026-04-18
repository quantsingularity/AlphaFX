"""
AlphaFX AI Services - Model Training Pipeline
Trains and saves all ML models for a given list of currency pairs.

Run:
  python -m ai_services.training.train_all --pairs EURUSD GBPUSD USDJPY
  python -m ai_services.training.train_all --pairs all
"""

import argparse
import json
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_services.config import config
from ai_services.models.anomaly_detector import AnomalyDetector
from ai_services.models.garch_vol import GARCHForecaster
from ai_services.models.lstm_forecaster import LSTMForecaster
from ai_services.models.regime_detector import RegimeDetector
from ai_services.utils.features import build_feature_matrix, build_sequences

MAJOR_PAIRS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "NZDUSD",
    "USDCAD",
    "EURGBP",
    "EURJPY",
    "GBPJPY",
]


def get_ohlcv(pair: str, n: int = 500) -> pd.DataFrame:
    """
    Retrieve OHLCV data.
    In production, replace with database or live API calls.
    """
    try:
        from apps.core.pricing import FALLBACK_RATES

        base = FALLBACK_RATES.get(pair.upper(), 1.0)
    except ImportError:
        base = 1.0

    rng = np.random.default_rng(abs(hash(pair)) % (2**31))
    rets = rng.normal(0.00005, 0.006, n)
    cls = base * np.exp(np.cumsum(rets))
    hi = cls * (1 + rng.uniform(0.001, 0.006, n))
    lo = cls * (1 - rng.uniform(0.001, 0.006, n))
    op = np.roll(cls, 1)
    op[0] = base
    vol = rng.integers(1_000_000, 5_000_000, n).astype(float)
    idx = pd.date_range(end=date.today(), periods=n, freq="B")
    return pd.DataFrame(
        {"open": op, "high": hi, "low": lo, "close": cls, "volume": vol}, index=idx
    )


def train_pair(pair: str, output_dir: str, lookback: int = 60) -> dict:
    """
    Train all models for one currency pair and save to disk.
    Returns a metrics dict.
    """
    print(f"  Training {pair}...")
    pair_dir = os.path.join(output_dir, pair)
    os.makedirs(pair_dir, exist_ok=True)

    df = get_ohlcv(pair, 500)
    feat = build_feature_matrix(df, include_target=True).dropna()
    if feat.empty:
        return {"pair": pair, "status": "skipped - insufficient data"}

    target = feat["target_label"].values
    fmat = feat.drop(
        columns=["target_ret", "target_label"], errors="ignore"
    ).values.astype(np.float32)
    X, y = build_sequences(fmat, target.astype(np.float32), lookback)
    n_feat = X.shape[2] if X.ndim == 3 else fmat.shape[1]

    metrics: dict = {"pair": pair, "status": "ok", "n_train": len(X)}

    # LSTM
    print(f"    LSTM ({n_feat} features, {len(X)} sequences)...")
    lstm = LSTMForecaster(
        n_features=n_feat,
        hidden_size=config.lstm_hidden_size,
        num_layers=config.lstm_num_layers,
        dropout=config.lstm_dropout,
        epochs=config.lstm_epochs,
        batch_size=config.lstm_batch_size,
    )
    lstm.fit(X, y)
    lstm.save(os.path.join(pair_dir, "lstm"))
    if lstm.history_:
        metrics["lstm_val_acc"] = round(lstm.history_[-1].get("val_acc", 0.0), 4)

    # Regime detector
    print(f"    HMM regime detector...")
    regime = RegimeDetector(n_states=config.hmm_n_states, n_iter=config.hmm_n_iter)
    regime.fit(df["close"])
    regime.save(os.path.join(pair_dir, "regime"))
    metrics["regime"] = regime.state_label(regime.current_state(df["close"]))

    # GARCH
    print(f"    GARCH({config.garch_p},{config.garch_q})-{config.garch_dist}...")
    garch = GARCHForecaster(
        pair=pair,
        p=config.garch_p,
        q=config.garch_q,
        model="gjr",
        dist=config.garch_dist,
    )
    garch.fit(df["close"])
    garch.save(os.path.join(pair_dir, "garch"))
    metrics["current_vol_pct"] = garch.current_conditional_vol()

    # Anomaly detector
    print(f"    Isolation Forest anomaly detector...")
    anomaly = AnomalyDetector(
        zscore_window=config.zscore_window,
        zscore_threshold=config.zscore_threshold,
        if_contamination=config.isolation_forest_contamination,
    )
    anomaly.fit(df)
    anomaly.save(os.path.join(pair_dir, "anomaly"))

    print(
        f"  {pair} done. Val acc: {metrics.get('lstm_val_acc', 'N/A')}, "
        f"Regime: {metrics.get('regime', 'N/A')}"
    )
    return metrics


def train_all(pairs: list[str], output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    all_metrics = []

    for pair in pairs:
        try:
            m = train_pair(pair, output_dir)
            all_metrics.append(m)
        except Exception as e:
            print(f"  ERROR training {pair}: {e}")
            all_metrics.append({"pair": pair, "status": f"error: {e}"})

    # Save training manifest
    manifest_path = os.path.join(output_dir, "training_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(
            {
                "trained_at": str(date.today()),
                "pairs": pairs,
                "metrics": all_metrics,
            },
            f,
            indent=2,
        )

    print(f"\nTraining complete. Manifest: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="AlphaFX AI Model Training Pipeline")
    parser.add_argument(
        "--pairs",
        nargs="+",
        default=["EURUSD"],
        help="Pairs to train, or 'all' for all major pairs",
    )
    parser.add_argument(
        "--output-dir",
        default=config.model_dir,
        help="Directory to save trained models",
    )
    parser.add_argument("--lookback", type=int, default=60)
    args = parser.parse_args()

    pairs = MAJOR_PAIRS if "all" in args.pairs else [p.upper() for p in args.pairs]
    print(f"Training {len(pairs)} pairs: {pairs}")
    train_all(pairs, args.output_dir)


if __name__ == "__main__":
    main()
