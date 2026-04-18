"""
AlphaFX AI Services - FastAPI Application
Serves all ML model predictions as REST endpoints.
Runs on port 8001 alongside the main Django backend (port 8000).

Endpoints:
  POST /ai/forecast/{pair}           LSTM direction probability
  GET  /ai/regime/{pair}             Market regime (BULL/BEAR/RANGING)
  GET  /ai/volatility/{pair}         GARCH volatility forecast
  POST /ai/sentiment                 Headline sentiment analysis
  GET  /ai/sentiment/macro           Macro risk-on/off index
  GET  /ai/anomaly/{pair}            Flash crash / anomaly detection
  POST /ai/signal/{pair}             Aggregated ML trading signal
  GET  /ai/health                    Service health check
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from ai_services.models.anomaly_detector import AnomalyDetector
from ai_services.models.garch_vol import GARCHForecaster
from ai_services.models.lstm_forecaster import LSTMForecaster
from ai_services.models.regime_detector import RegimeDetector
from ai_services.services.sentiment import SentimentService
from ai_services.services.signal_aggregator import SignalAggregator
from ai_services.utils.features import build_feature_matrix, build_sequences
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AlphaFX AI Services",
    version="2.0.0",
    description="Machine learning and AI model serving for AlphaFX",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Shared data utility (synthetic OHLCV for demo -- replace with live feed)
# ---------------------------------------------------------------------------


def _get_ohlcv(pair: str, n: int = 300) -> pd.DataFrame:
    """Generate synthetic OHLCV -- wire up to live data feed in production."""
    try:
        # Try to import the Django pricing module for consistent fallback rates
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from apps.core.pricing import FALLBACK_RATES

        base_price = FALLBACK_RATES.get(pair.upper(), 1.0)
    except ImportError:
        base_price = 1.0850 if pair.upper() == "EURUSD" else 1.0

    rng = np.random.default_rng(abs(hash(pair)) % (2**31))
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


def _get_features_and_sequences(pair: str, lookback: int = 60):
    df = _get_ohlcv(pair, 300)
    feat = build_feature_matrix(df, include_target=True).dropna()
    target = feat["target_label"].values
    fmat = feat.drop(columns=["target_ret", "target_label"], errors="ignore").values
    X, y = build_sequences(fmat.astype(np.float32), target.astype(np.float32), lookback)
    return df, feat, X, y


# ---------------------------------------------------------------------------
# Lazy-loaded model registry
# ---------------------------------------------------------------------------

_models: dict[str, dict] = {}


def _get_models(pair: str) -> dict:
    if pair not in _models:
        df, feat, X, y = _get_features_and_sequences(pair)
        n_features = X.shape[2] if X.ndim == 3 else 30

        lstm = LSTMForecaster(n_features=n_features, epochs=10, hidden_size=32)
        if len(X) > 10:
            lstm.fit(X, y)

        regime = RegimeDetector(n_states=3)
        regime.fit(df["close"])

        garch = GARCHForecaster(pair=pair)
        garch.fit(df["close"])

        anomaly = AnomalyDetector()
        anomaly.fit(df)

        _models[pair] = {
            "lstm": lstm,
            "regime": regime,
            "garch": garch,
            "anomaly": anomaly,
            "df": df,
            "X": X,
        }
    return _models[pair]


_sentiment_svc: Optional[SentimentService] = None


def _get_sentiment() -> SentimentService:
    global _sentiment_svc
    if _sentiment_svc is None:
        _sentiment_svc = SentimentService()
    return _sentiment_svc


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class SentimentRequest(BaseModel):
    headlines: list[str] = Field(min_length=1, max_length=100)


class ForecastRequest(BaseModel):
    lookback: int = Field(default=60, ge=20, le=120)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/ai/health")
def health():
    return {
        "status": "ok",
        "service": "AlphaFX AI Services",
        "version": "2.0.0",
    }


@app.post("/ai/forecast/{pair}")
def forecast_direction(pair: str, req: ForecastRequest = ForecastRequest()):
    """LSTM price direction probability for the next N bars."""
    pair = pair.upper()
    try:
        m = _get_models(pair)
        X = m["X"]
        if len(X) == 0:
            raise HTTPException(status_code=422, detail="Insufficient data for LSTM")
        lstm = m["lstm"]
        prob = float(lstm.predict_proba(X[-1:])[-1])
        return {
            "pair": pair,
            "prob_up": round(prob, 4),
            "prob_down": round(1 - prob, 4),
            "direction": "UP" if prob > 0.5 else "DOWN",
            "confidence": round(abs(prob - 0.5) * 2, 4),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/regime/{pair}")
def market_regime(pair: str):
    """Current HMM market regime and state probabilities."""
    pair = pair.upper()
    try:
        m = _get_models(pair)
        model = m["regime"]
        close = m["df"]["close"]
        state = model.current_state(close)
        label = model.state_label(state)
        probs = model.state_probabilities(close)
        dur = model.regime_durations(close)
        return {
            "pair": pair,
            "regime": label,
            "state_index": state,
            "probabilities": probs,
            "current_duration_bars": dur[-1]["duration_bars"] if dur else 0,
            "recent_regimes": dur[-5:] if dur else [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/volatility/{pair}")
def volatility_forecast(pair: str, horizon: int = 10):
    """GARCH conditional volatility forecast."""
    pair = pair.upper()
    try:
        m = _get_models(pair)
        g = m["garch"]
        forecast = g.forecast(horizon=min(horizon, 30))
        summary = g.summary()
        nic = g.news_impact_curve()
        return {
            **forecast,
            "model_summary": summary,
            "news_impact_curve": nic,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/sentiment")
def analyse_sentiment(req: SentimentRequest):
    """Analyse a batch of news headlines for FX sentiment."""
    svc = _get_sentiment()
    results = svc.analyse_batch(req.headlines)
    ccy_agg = svc.aggregate_currency_sentiment(req.headlines)
    macro = svc.macro_sentiment_index(req.headlines)
    return {
        "headlines": results,
        "currency_sentiment": ccy_agg,
        "macro_index": macro,
    }


@app.get("/ai/sentiment/macro")
def macro_sentiment():
    """Sample macro risk-on/off sentiment from placeholder headlines."""
    placeholder = [
        "Federal Reserve signals further rate hikes amid persistent inflation",
        "Eurozone GDP growth beats expectations in Q3",
        "Bank of Japan maintains ultra-loose monetary policy stance",
        "Risk sentiment improves as US jobs data surprises to the upside",
        "Oil prices surge on supply concerns boosting commodity currencies",
    ]
    svc = _get_sentiment()
    macro = svc.macro_sentiment_index(placeholder)
    ccy = svc.aggregate_currency_sentiment(placeholder)
    return {"macro_index": macro, "currency_sentiment": ccy}


@app.get("/ai/anomaly/{pair}")
def anomaly_detection(pair: str):
    """Detect anomalous price bars in recent history."""
    pair = pair.upper()
    try:
        m = _get_models(pair)
        detector = m["anomaly"]
        df = m["df"]
        latest = detector.detect_latest(df)
        recent = detector.detect(df).tail(10)
        recent_list = [
            {
                "date": str(recent.index[i].date()),
                "anomaly": bool(recent.iloc[i]["anomaly"]),
                "severity": recent.iloc[i]["severity"],
                "ret_z": round(float(recent.iloc[i]["ret_z"]), 3),
            }
            for i in range(len(recent))
        ]
        return {
            "pair": pair,
            "latest": latest,
            "recent_10": recent_list,
            "anomaly_count": sum(1 for r in recent_list if r["anomaly"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/signal/{pair}")
def aggregated_signal(pair: str, req: SentimentRequest = None):
    """Full ML-aggregated trading signal combining all model outputs."""
    pair = pair.upper()
    try:
        m = _get_models(pair)
        close = m["df"]["close"]
        X = m["X"]
        headlines = req.headlines if req else []

        # Get technical analysis from Django backend module
        try:
            from apps.core.technical import full_analysis

            tech = full_analysis(pair, 252)
        except ImportError:
            tech = None

        aggregator = SignalAggregator(
            lstm_model=m["lstm"],
            regime_model=m["regime"],
            garch_model=m["garch"],
            sentiment_svc=_get_sentiment(),
        )
        result = aggregator.aggregate(
            pair=pair,
            close=close,
            X_seq=X if len(X) > 0 else None,
            headlines=headlines,
            technical_result=tech,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
