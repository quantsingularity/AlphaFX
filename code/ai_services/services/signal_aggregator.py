"""
AlphaFX AI Services - ML Signal Aggregator
Combines outputs from LSTM forecaster, regime detector, GARCH volatility,
sentiment analyser, and technical rules into a single unified trading
signal with confidence score and reasoning.

Output schema
-------------
{
    "pair":          "EURUSD",
    "signal":        "BUY" | "SELL" | "NEUTRAL",
    "confidence":    0.74,          # 0.0 - 1.0
    "regime":        "BULL",
    "vol_regime":    "LOW_VOL",     # LOW_VOL | HIGH_VOL | EXTREME_VOL
    "components": {
        "lstm":       {"direction": 1, "prob": 0.72},
        "regime":     {"label": "BULL", "probs": {...}},
        "garch_vol":  {"daily_vol_pct": 0.52, "signal": "NORMAL"},
        "sentiment":  {"net_score": 0.18, "signal": "BULLISH"},
        "technical":  {"signal": "BULLISH", "rsi": 58.4, "macd_hist": 0.0003},
    },
    "risk_adjustment": {
        "suggested_size_pct": 0.8,   # fraction of normal position
        "stop_atr_multiplier": 1.5,
    },
}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    import pandas as pd
    from ai_services.models.garch_vol import GARCHForecaster
    from ai_services.models.lstm_forecaster import LSTMForecaster
    from ai_services.models.regime_detector import RegimeDetector
    from ai_services.services.sentiment import SentimentService


# ---------------------------------------------------------------------------
# Component weight config (sum = 1.0)
# ---------------------------------------------------------------------------

WEIGHTS = {
    "lstm": 0.30,
    "regime": 0.20,
    "sentiment": 0.15,
    "technical": 0.25,
    "garch": 0.10,  # vol regime adjusts size, not direction directly
}


class SignalAggregator:
    """
    Assembles all AI and technical signals into a single actionable signal.

    Each component contributes a direction score in [-1, +1]:
      +1.0 = strong buy
       0.0 = neutral
      -1.0 = strong sell

    The final score is a weighted average.  A vol-regime multiplier
    then scales position sizing downward in high-vol environments.
    """

    def __init__(
        self,
        lstm_model: Optional["LSTMForecaster"] = None,
        regime_model: Optional["RegimeDetector"] = None,
        garch_model: Optional["GARCHForecaster"] = None,
        sentiment_svc: Optional["SentimentService"] = None,
        weights: Optional[dict[str, float]] = None,
    ):
        self.lstm_model = lstm_model
        self.regime_model = regime_model
        self.garch_model = garch_model
        self.sentiment_svc = sentiment_svc
        self.weights = weights or WEIGHTS

    # ---- Individual component scorers -------------------------------------

    def _lstm_score(
        self,
        X_seq: Optional[np.ndarray],
    ) -> dict:
        if self.lstm_model is None or X_seq is None:
            return {"direction": 0, "prob": 0.5, "score": 0.0}
        prob = float(self.lstm_model.predict_proba(X_seq[-1:])[-1])
        score = (prob - 0.5) * 2  # map [0,1] -> [-1,+1]
        return {
            "direction": 1 if prob > 0.5 else -1,
            "prob": round(prob, 4),
            "score": round(score, 4),
        }

    def _regime_score(self, close: "pd.Series") -> dict:
        if self.regime_model is None:
            return {"label": "UNKNOWN", "probs": {}, "score": 0.0}
        probs = self.regime_model.state_probabilities(close)
        state = self.regime_model.state_label(self.regime_model.current_state(close))
        bull_p = probs.get("BULL", 0.33)
        bear_p = probs.get("BEAR", 0.33)
        score = bull_p - bear_p
        return {"label": state, "probs": probs, "score": round(score, 4)}

    def _garch_score(self) -> dict:
        if self.garch_model is None:
            return {"daily_vol_pct": 0.7, "signal": "NORMAL", "size_mult": 1.0}
        vol = self.garch_model.current_conditional_vol()
        if vol < 0.5:
            signal, mult = "LOW_VOL", 1.1
        elif vol < 1.0:
            signal, mult = "NORMAL", 1.0
        elif vol < 1.5:
            signal, mult = "HIGH_VOL", 0.8
        else:
            signal, mult = "EXTREME_VOL", 0.5
        return {"daily_vol_pct": round(vol, 4), "signal": signal, "size_mult": mult}

    def _sentiment_score(self, headlines: Optional[list[str]]) -> dict:
        if self.sentiment_svc is None or not headlines:
            return {"net_score": 0.0, "signal": "NEUTRAL", "score": 0.0}
        macro = self.sentiment_svc.macro_sentiment_index(headlines)
        index = macro["index"]
        score = max(-1.0, min(1.0, index * 2))  # amplify slightly
        signal = (
            "BULLISH" if index > 0.15 else "BEARISH" if index < -0.15 else "NEUTRAL"
        )
        return {
            "net_score": round(index, 4),
            "signal": signal,
            "score": round(score, 4),
        }

    def _technical_score(self, technical_result: Optional[dict]) -> dict:
        if technical_result is None:
            return {"signal": "NEUTRAL", "score": 0.0}
        sig_map = {
            "STRONG_BULLISH": 1.0,
            "BULLISH": 0.6,
            "NEUTRAL": 0.0,
            "BEARISH": -0.6,
            "STRONG_BEARISH": -1.0,
        }
        sig = technical_result.get("signal", "NEUTRAL")
        score = sig_map.get(sig, 0.0)
        return {
            "signal": sig,
            "rsi": technical_result.get("indicators", {}).get("rsi_14"),
            "macd_hist": technical_result.get("indicators", {}).get("macd_hist"),
            "score": score,
        }

    # ---- Main aggregation -------------------------------------------------

    def aggregate(
        self,
        pair: str,
        close: Optional["pd.Series"] = None,
        X_seq: Optional[np.ndarray] = None,
        headlines: Optional[list[str]] = None,
        technical_result: Optional[dict] = None,
    ) -> dict:
        """
        Compute the aggregated trading signal.

        Parameters
        ----------
        pair             Currency pair code (e.g. "EURUSD")
        close            Closing price series for regime and GARCH
        X_seq            Sequence array for LSTM (shape N, lookback, features)
        headlines        News headlines for sentiment analysis
        technical_result Full output from core.technical.full_analysis()
        """
        lstm_comp = self._lstm_score(X_seq)
        regime_comp = (
            self._regime_score(close)
            if close is not None
            else {"label": "UNKNOWN", "probs": {}, "score": 0.0}
        )
        garch_comp = self._garch_score()
        sentiment_comp = self._sentiment_score(headlines)
        tech_comp = self._technical_score(technical_result)

        # Weighted direction score [-1, +1]
        w = self.weights
        direction_score = (
            w["lstm"] * lstm_comp["score"]
            + w["regime"] * regime_comp["score"]
            + w["sentiment"] * sentiment_comp["score"]
            + w["technical"] * tech_comp["score"]
            # GARCH doesn't directly contribute to direction
        )

        # Convert to signal label
        if direction_score > 0.25:
            signal = "BUY"
        elif direction_score < -0.25:
            signal = "SELL"
        else:
            signal = "NEUTRAL"

        # Confidence: absolute direction score mapped to [0.5, 1.0]
        confidence = 0.5 + min(abs(direction_score), 1.0) * 0.5

        # Vol-regime size adjustment
        size_mult = garch_comp.get("size_mult", 1.0)
        stop_mult = 1.0 + (1.0 - size_mult)  # wider stops in high vol

        return {
            "pair": pair.upper(),
            "signal": signal,
            "direction_score": round(direction_score, 4),
            "confidence": round(confidence, 4),
            "regime": regime_comp["label"],
            "vol_regime": garch_comp["signal"],
            "components": {
                "lstm": lstm_comp,
                "regime": regime_comp,
                "garch_vol": garch_comp,
                "sentiment": sentiment_comp,
                "technical": tech_comp,
            },
            "risk_adjustment": {
                "suggested_size_pct": round(size_mult * 100, 1),
                "stop_atr_multiplier": round(stop_mult, 2),
            },
        }
