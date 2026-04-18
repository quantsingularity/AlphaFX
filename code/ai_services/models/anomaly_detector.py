"""
AlphaFX AI Services - Anomaly Detector
Combines Isolation Forest and statistical Z-score methods to flag
anomalous price movements in FX tick data.

Use cases:
  - Flash crash detection
  - Data quality / feed error alerting
  - Risk circuit-breaker triggers
  - Unusual volume detection

Usage:
  from ai_services.models.anomaly_detector import AnomalyDetector
  det = AnomalyDetector()
  det.fit(feature_df)
  flags = det.detect(new_df)
"""

import json
import os
from typing import Optional

import numpy as np
import pandas as pd


class AnomalyDetector:
    """
    Two-layer anomaly detection:
      Layer 1: Rolling Z-score on returns and volatility
      Layer 2: Isolation Forest on multi-dimensional feature space

    A bar is flagged if either layer triggers above the respective threshold.
    """

    def __init__(
        self,
        zscore_window: int = 20,
        zscore_threshold: float = 3.5,
        if_contamination: float = 0.05,
        if_n_estimators: int = 100,
        random_state: int = 42,
    ):
        self.zscore_window = zscore_window
        self.zscore_threshold = zscore_threshold
        self.if_contamination = if_contamination
        self.if_n_estimators = if_n_estimators
        self.random_state = random_state
        self._iso_forest = None
        self._feature_cols: Optional[list[str]] = None
        self._fitted = False

    # ---- Feature extraction ------------------------------------------------

    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build anomaly-detection feature set from OHLCV.
        Returns DataFrame with numeric features only.
        """
        c = df["close"]
        h = df["high"]
        l = df["low"]
        v = df.get("volume", pd.Series(np.ones(len(df)), index=df.index))

        feat = pd.DataFrame(index=df.index)
        feat["ret_1"] = c.pct_change()
        feat["ret_1_abs"] = feat["ret_1"].abs()
        feat["hl_range"] = (h - l) / c
        feat["gap"] = (df["open"] - c.shift(1)).abs() / c.shift(1)
        feat["vol_z"] = (v - v.rolling(20).mean()) / (v.rolling(20).std() + 1e-9)
        feat["ret_z"] = (
            feat["ret_1"] - feat["ret_1"].rolling(self.zscore_window).mean()
        ) / (feat["ret_1"].rolling(self.zscore_window).std() + 1e-9)
        feat["range_z"] = (
            feat["hl_range"] - feat["hl_range"].rolling(self.zscore_window).mean()
        ) / (feat["hl_range"].rolling(self.zscore_window).std() + 1e-9)

        return feat.dropna()

    # ---- Training ----------------------------------------------------------

    def fit(self, df: pd.DataFrame) -> "AnomalyDetector":
        """
        Fit the Isolation Forest on historical OHLCV data.
        Requires scikit-learn.
        """
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            self._fitted = False
            return self

        feat = self._extract_features(df)
        self._feature_cols = list(feat.columns)
        iso = IsolationForest(
            n_estimators=self.if_n_estimators,
            contamination=self.if_contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        iso.fit(feat.values)
        self._iso_forest = iso
        self._fitted = True
        return self

    # ---- Detection ---------------------------------------------------------

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect anomalies in new data.

        Returns a DataFrame with columns:
          ret_z         - return Z-score
          range_z       - range Z-score
          zscore_flag   - True if Z-score exceeds threshold
          if_score      - Isolation Forest anomaly score (lower = more anomalous)
          if_flag       - True if Isolation Forest labels -1
          anomaly       - True if either layer flags the bar
          severity      - "HIGH" / "MEDIUM" / "LOW" / "NORMAL"
        """
        feat = self._extract_features(df)

        result = pd.DataFrame(index=feat.index)
        result["ret_z"] = feat["ret_z"]
        result["range_z"] = feat["range_z"]
        result["zscore_flag"] = feat["ret_z"].abs() > self.zscore_threshold

        if self._fitted and self._iso_forest is not None:
            # Align feature columns
            X = feat[self._feature_cols].values if self._feature_cols else feat.values
            result["if_score"] = self._iso_forest.score_samples(X)
            result["if_flag"] = self._iso_forest.predict(X) == -1
        else:
            result["if_score"] = 0.0
            result["if_flag"] = False

        result["anomaly"] = result["zscore_flag"] | result["if_flag"]

        def severity(row):
            if not row["anomaly"]:
                return "NORMAL"
            if abs(row["ret_z"]) > 5 or row["if_score"] < -0.3:
                return "HIGH"
            if abs(row["ret_z"]) > 4 or row["if_score"] < -0.2:
                return "MEDIUM"
            return "LOW"

        result["severity"] = result.apply(severity, axis=1)
        return result

    def detect_latest(self, df: pd.DataFrame) -> dict:
        """Return anomaly assessment for the most recent bar only."""
        detected = self.detect(df)
        if detected.empty:
            return {"anomaly": False, "severity": "NORMAL"}

        last = detected.iloc[-1]
        return {
            "date": str(detected.index[-1].date()),
            "anomaly": bool(last["anomaly"]),
            "severity": last["severity"],
            "ret_z": round(float(last["ret_z"]), 3),
            "range_z": round(float(last["range_z"]), 3),
            "if_score": round(float(last["if_score"]), 4),
            "zscore_flag": bool(last["zscore_flag"]),
            "if_flag": bool(last["if_flag"]),
        }

    # ---- Persistence -------------------------------------------------------

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        meta = {
            "zscore_window": self.zscore_window,
            "zscore_threshold": self.zscore_threshold,
            "if_contamination": self.if_contamination,
            "feature_cols": self._feature_cols,
            "fitted": self._fitted,
        }
        with open(os.path.join(path, "anomaly_meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        if self._fitted and self._iso_forest is not None:
            import joblib

            joblib.dump(self._iso_forest, os.path.join(path, "iso_forest.joblib"))

    @classmethod
    def load(cls, path: str) -> "AnomalyDetector":
        with open(os.path.join(path, "anomaly_meta.json")) as f:
            meta = json.load(f)
        det = cls(
            zscore_window=meta["zscore_window"],
            zscore_threshold=meta["zscore_threshold"],
            if_contamination=meta["if_contamination"],
        )
        det._feature_cols = meta.get("feature_cols")
        det._fitted = meta.get("fitted", False)
        iso_path = os.path.join(path, "iso_forest.joblib")
        if os.path.exists(iso_path):
            import joblib

            det._iso_forest = joblib.load(iso_path)
        return det
