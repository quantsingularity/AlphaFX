"""
AlphaFX AI Services - Market Regime Detector
Gaussian Hidden Markov Model that classifies the market into latent
regimes (typically Bull / Bear / Ranging) from returns and volatility.

The regime label is surfaced as a feature for other models and as a
standalone API endpoint so the dashboard can display current regime.

Usage:
  from ai_services.models.regime_detector import RegimeDetector
  detector = RegimeDetector(n_states=3)
  detector.fit(returns_series)
  state = detector.current_state(returns_series)
  label = detector.state_label(state)  # "BULL" / "BEAR" / "RANGING"
"""

import json
import os
from typing import Optional

import numpy as np
import pandas as pd


class RegimeDetector:
    """
    Gaussian HMM-based market regime classifier.

    States are labelled post-fit by sorting on the mean return of each
    state: highest mean -> BULL, lowest mean -> BEAR, middle -> RANGING.
    With n_states=2 labels are BULL and BEAR only.
    """

    LABEL_MAP_3 = {0: "BEAR", 1: "RANGING", 2: "BULL"}
    LABEL_MAP_2 = {0: "BEAR", 1: "BULL"}

    def __init__(
        self,
        n_states: int = 3,
        n_iter: int = 100,
        covariance_type: str = "full",
        random_state: int = 42,
    ):
        self.n_states = n_states
        self.n_iter = n_iter
        self.covariance_type = covariance_type
        self.random_state = random_state
        self._model = None
        self._state_order: Optional[list[int]] = None  # sorted low->high mean
        self._fitted = False

    # ---- Feature preparation -----------------------------------------------

    def _build_obs(self, close: pd.Series) -> np.ndarray:
        """
        Build 2-column observation matrix: [return, log_vol].
        Log-vol is the rolling 5-day realised vol annualised.
        """
        ret = close.pct_change().dropna()
        log_vol = np.log(
            ret.rolling(5).std().replace(0, np.nan).dropna() * np.sqrt(252) + 1e-6
        )
        common = ret.align(log_vol, join="inner")[0]
        log_vol = log_vol.loc[common.index]
        obs = np.column_stack([common.values, log_vol.values])
        return obs.astype(np.float64)

    # ---- Training ----------------------------------------------------------

    def fit(self, close: pd.Series) -> "RegimeDetector":
        """
        Fit the HMM to a closing-price series.
        Requires hmmlearn: pip install hmmlearn
        """
        try:
            from hmmlearn.hmm import GaussianHMM
        except ImportError:
            self._fitted = False
            return self

        obs = self._build_obs(close)
        model = GaussianHMM(
            n_components=self.n_states,
            covariance_type=self.covariance_type,
            n_iter=self.n_iter,
            random_state=self.random_state,
        )
        model.fit(obs)
        self._model = model

        # Determine state ordering by mean return
        means = model.means_[:, 0]  # first column is return
        self._state_order = list(np.argsort(means))  # index 0=lowest mean
        self._fitted = True
        return self

    def _ranked_state(self, raw_state: int) -> int:
        """Convert HMM state index to rank (0=lowest return, N-1=highest)."""
        if self._state_order is None:
            return raw_state
        return self._state_order.index(raw_state)

    # ---- Inference ---------------------------------------------------------

    def predict_states(self, close: pd.Series) -> np.ndarray:
        """Return array of ranked state indices for each observation."""
        if not self._fitted or self._model is None:
            return np.zeros(len(close), dtype=int)
        obs = self._build_obs(close)
        raw = self._model.predict(obs)
        return np.array([self._ranked_state(s) for s in raw])

    def current_state(self, close: pd.Series) -> int:
        """Return ranked state index for the most recent bar."""
        states = self.predict_states(close)
        return int(states[-1]) if len(states) else 0

    def state_label(self, ranked_state: int) -> str:
        """Map a ranked state index to a human-readable label."""
        if self.n_states == 3:
            return self.LABEL_MAP_3.get(ranked_state, "UNKNOWN")
        return self.LABEL_MAP_2.get(min(ranked_state, 1), "UNKNOWN")

    def state_probabilities(self, close: pd.Series) -> dict[str, float]:
        """
        Return posterior probability of each regime at the most recent bar.
        """
        if not self._fitted or self._model is None:
            return {"BULL": 0.33, "BEAR": 0.33, "RANGING": 0.34}

        obs = self._build_obs(close)
        _, posteriors = self._model.score_samples(obs)
        last = posteriors[-1]  # shape (n_states,)

        result = {}
        for raw_state, prob in enumerate(last):
            ranked = self._ranked_state(raw_state)
            label = self.state_label(ranked)
            result[label] = round(float(prob), 4)
        return result

    def regime_durations(self, close: pd.Series) -> list[dict]:
        """
        Return a list of contiguous regime segments with start/end/duration.
        """
        states = self.predict_states(close)
        index = close.index[-len(states) :]
        segments = []
        if len(states) == 0:
            return segments

        cur_state = states[0]
        start = index[0]

        for i in range(1, len(states)):
            if states[i] != cur_state:
                segments.append(
                    {
                        "label": self.state_label(cur_state),
                        "start": str(start.date()),
                        "end": str(index[i - 1].date()),
                        "duration_bars": i - len(segments),
                    }
                )
                cur_state = states[i]
                start = index[i]

        segments.append(
            {
                "label": self.state_label(cur_state),
                "start": str(start.date()),
                "end": str(index[-1].date()),
                "duration_bars": len(states)
                - sum(s["duration_bars"] for s in segments),
            }
        )
        return segments

    # ---- Persistence -------------------------------------------------------

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        meta = {
            "n_states": self.n_states,
            "n_iter": self.n_iter,
            "covariance_type": self.covariance_type,
            "state_order": self._state_order,
            "fitted": self._fitted,
        }
        with open(os.path.join(path, "regime_meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

        if self._fitted and self._model is not None:
            import joblib

            joblib.dump(self._model, os.path.join(path, "hmm_model.joblib"))

    @classmethod
    def load(cls, path: str) -> "RegimeDetector":
        with open(os.path.join(path, "regime_meta.json")) as f:
            meta = json.load(f)
        det = cls(
            n_states=meta["n_states"],
            n_iter=meta["n_iter"],
            covariance_type=meta["covariance_type"],
        )
        det._state_order = meta.get("state_order")
        det._fitted = meta.get("fitted", False)
        model_path = os.path.join(path, "hmm_model.joblib")
        if os.path.exists(model_path):
            import joblib

            det._model = joblib.load(model_path)
        return det
