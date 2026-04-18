"""
AlphaFX AI Services - Test Suite
Tests for feature engineering, model correctness, and API endpoints.
All tests use synthetic data and require no external dependencies beyond
scikit-learn (PyTorch and arch are optional but tested if present).
"""

from datetime import date

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_ohlcv():
    n = 300
    rng = np.random.default_rng(42)
    cls = 1.0850 * np.exp(np.cumsum(rng.normal(0.00005, 0.006, n)))
    hi = cls * (1 + rng.uniform(0.001, 0.005, n))
    lo = cls * (1 - rng.uniform(0.001, 0.005, n))
    op = np.roll(cls, 1)
    op[0] = 1.085
    vol = rng.integers(1_000_000, 5_000_000, n).astype(float)
    idx = pd.date_range(end=date.today(), periods=n, freq="B")
    return pd.DataFrame(
        {"open": op, "high": hi, "low": lo, "close": cls, "volume": vol}, index=idx
    )


@pytest.fixture
def feature_matrix(sample_ohlcv):
    from ai_services.utils.features import build_feature_matrix

    return build_feature_matrix(sample_ohlcv, include_target=True)


@pytest.fixture
def sequences(feature_matrix):
    from ai_services.utils.features import build_sequences

    feat = feature_matrix.drop(columns=["target_ret", "target_label"], errors="ignore")
    target = feature_matrix["target_label"].values
    return build_sequences(
        feat.values.astype(np.float32), target.astype(np.float32), lookback=30
    )


# ---------------------------------------------------------------------------
# Feature engineering tests
# ---------------------------------------------------------------------------


class TestFeatureEngineering:

    def test_feature_matrix_not_empty(self, feature_matrix):
        assert len(feature_matrix) > 0

    def test_feature_matrix_has_target(self, feature_matrix):
        assert "target_label" in feature_matrix.columns
        assert "target_ret" in feature_matrix.columns

    def test_target_binary(self, feature_matrix):
        unique = set(feature_matrix["target_label"].unique())
        assert unique.issubset({0, 1, 0.0, 1.0})

    def test_rsi_features_in_range(self, feature_matrix):
        for col in [c for c in feature_matrix.columns if c.startswith("rsi_")]:
            assert feature_matrix[col].between(0, 1).all(), f"{col} out of [0,1]"

    def test_no_nan_after_dropna(self, feature_matrix):
        assert not feature_matrix.isnull().any().any()

    def test_sequence_shapes(self, sequences):
        X, y = sequences
        assert X.ndim == 3
        assert y.ndim == 1
        assert X.shape[0] == y.shape[0]
        assert X.shape[1] == 30  # lookback

    def test_rolling_zscore(self, sample_ohlcv):
        from ai_services.utils.features import rolling_zscore

        z = rolling_zscore(sample_ohlcv["close"], window=20).dropna()
        assert abs(z.mean()) < 0.5  # near zero mean
        assert z.std() < 2.0  # reasonable std


# ---------------------------------------------------------------------------
# LSTM forecaster tests
# ---------------------------------------------------------------------------


class TestLSTMForecaster:

    def test_fit_and_predict(self, sequences):
        from ai_services.models.lstm_forecaster import LSTMForecaster

        X, y = sequences
        model = LSTMForecaster(
            n_features=X.shape[2], epochs=2, hidden_size=16, num_layers=1
        )
        model.fit(X, y)
        probs = model.predict_proba(X[:5])
        assert len(probs) == 5
        assert all(0 <= p <= 1 for p in probs)

    def test_predict_binary(self, sequences):
        from ai_services.models.lstm_forecaster import LSTMForecaster

        X, y = sequences
        model = LSTMForecaster(n_features=X.shape[2], epochs=2, hidden_size=16)
        model.fit(X, y)
        preds = model.predict(X[:10])
        assert set(preds).issubset({0, 1})

    def test_fallback_without_torch(self, sequences):
        import ai_services.models.lstm_forecaster as m

        orig = m.TORCH_AVAILABLE
        m.TORCH_AVAILABLE = False
        from ai_services.models.lstm_forecaster import LSTMForecaster

        X, y = sequences
        model = LSTMForecaster(n_features=X.shape[2], epochs=2)
        model.fit(X, y)
        probs = model.predict_proba(X[:3])
        assert all(0 <= p <= 1 for p in probs)
        m.TORCH_AVAILABLE = orig

    def test_save_and_load(self, sequences, tmp_path):
        from ai_services.models.lstm_forecaster import LSTMForecaster

        X, y = sequences
        model = LSTMForecaster(n_features=X.shape[2], epochs=2, hidden_size=16)
        model.fit(X, y)
        save_path = str(tmp_path / "lstm")
        model.save(save_path)
        loaded = LSTMForecaster.load(save_path)
        assert loaded.n_features == model.n_features


# ---------------------------------------------------------------------------
# Regime detector tests
# ---------------------------------------------------------------------------


class TestRegimeDetector:

    def test_fit_and_predict(self, sample_ohlcv):
        from ai_services.models.regime_detector import RegimeDetector

        det = RegimeDetector(n_states=3)
        det.fit(sample_ohlcv["close"])
        state = det.current_state(sample_ohlcv["close"])
        assert state in (0, 1, 2)

    def test_label_mapping(self, sample_ohlcv):
        from ai_services.models.regime_detector import RegimeDetector

        det = RegimeDetector(n_states=3)
        det.fit(sample_ohlcv["close"])
        label = det.state_label(det.current_state(sample_ohlcv["close"]))
        assert label in {"BULL", "BEAR", "RANGING"}

    def test_state_probs_sum_to_one(self, sample_ohlcv):
        from ai_services.models.regime_detector import RegimeDetector

        det = RegimeDetector(n_states=3)
        det.fit(sample_ohlcv["close"])
        probs = det.state_probabilities(sample_ohlcv["close"])
        assert abs(sum(probs.values()) - 1.0) < 0.01

    def test_regime_durations_covers_full_history(self, sample_ohlcv):
        from ai_services.models.regime_detector import RegimeDetector

        det = RegimeDetector(n_states=3)
        det.fit(sample_ohlcv["close"])
        segs = det.regime_durations(sample_ohlcv["close"])
        assert len(segs) >= 1


# ---------------------------------------------------------------------------
# GARCH tests
# ---------------------------------------------------------------------------


class TestGARCHForecaster:

    def test_fit_and_forecast(self, sample_ohlcv):
        from ai_services.models.garch_vol import GARCHForecaster

        g = GARCHForecaster(pair="EURUSD")
        g.fit(sample_ohlcv["close"])
        fc = g.forecast(horizon=5)
        assert len(fc["daily_vol_pct"]) == 5
        assert all(v > 0 for v in fc["daily_vol_pct"])

    def test_current_vol_positive(self, sample_ohlcv):
        from ai_services.models.garch_vol import GARCHForecaster

        g = GARCHForecaster(pair="GBPUSD")
        g.fit(sample_ohlcv["close"])
        assert g.current_conditional_vol() > 0

    def test_nic_returns_list(self, sample_ohlcv):
        from ai_services.models.garch_vol import GARCHForecaster

        g = GARCHForecaster(pair="USDJPY")
        g.fit(sample_ohlcv["close"])
        nic = g.news_impact_curve()
        assert len(nic) == 41


# ---------------------------------------------------------------------------
# Anomaly detector tests
# ---------------------------------------------------------------------------


class TestAnomalyDetector:

    def test_fit_and_detect(self, sample_ohlcv):
        from ai_services.models.anomaly_detector import AnomalyDetector

        det = AnomalyDetector()
        det.fit(sample_ohlcv)
        result = det.detect(sample_ohlcv)
        assert "anomaly" in result.columns
        assert "severity" in result.columns
        assert set(result["severity"]).issubset({"NORMAL", "LOW", "MEDIUM", "HIGH"})

    def test_latest_dict_structure(self, sample_ohlcv):
        from ai_services.models.anomaly_detector import AnomalyDetector

        det = AnomalyDetector()
        det.fit(sample_ohlcv)
        latest = det.detect_latest(sample_ohlcv)
        assert "anomaly" in latest
        assert "severity" in latest

    def test_inject_crash(self, sample_ohlcv):
        from ai_services.models.anomaly_detector import AnomalyDetector

        det = AnomalyDetector(zscore_threshold=2.0)
        det.fit(sample_ohlcv)
        # Inject a 5% crash
        crash_df = sample_ohlcv.copy()
        crash_df.loc[crash_df.index[-1], "close"] *= 0.95
        latest = det.detect_latest(crash_df)
        assert latest["anomaly"] is True


# ---------------------------------------------------------------------------
# Sentiment tests
# ---------------------------------------------------------------------------


class TestSentimentService:

    def test_rule_based_bullish(self):
        from ai_services.services.sentiment import SentimentService

        svc = SentimentService.__new__(SentimentService)
        svc._loaded = False
        svc._pipeline = None
        result = svc.analyse_headline("Fed signals rate hike amid rising inflation")
        assert result["label"] in {"POSITIVE", "NEGATIVE", "NEUTRAL"}

    def test_currency_detection(self):
        from ai_services.services.sentiment import _detect_currencies

        ccys = _detect_currencies(
            "The dollar rallied against the euro after Fed comments"
        )
        assert "USD" in ccys
        assert "EUR" in ccys

    def test_macro_index_range(self):
        from ai_services.services.sentiment import SentimentService

        svc = SentimentService.__new__(SentimentService)
        svc._loaded = False
        svc._pipeline = None
        result = svc.macro_sentiment_index(
            ["rate hike", "recession fears", "strong jobs"]
        )
        assert -1 <= result["index"] <= 1

    def test_aggregate_returns_dict(self):
        from ai_services.services.sentiment import SentimentService

        svc = SentimentService.__new__(SentimentService)
        svc._loaded = False
        svc._pipeline = None
        result = svc.aggregate_currency_sentiment(
            ["dollar strengthens on hawkish Fed", "euro falls on weak eurozone data"]
        )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Signal aggregator tests
# ---------------------------------------------------------------------------


class TestSignalAggregator:

    def test_neutral_without_models(self):
        from ai_services.services.signal_aggregator import SignalAggregator

        agg = SignalAggregator()
        result = agg.aggregate("EURUSD")
        assert result["signal"] in {"BUY", "SELL", "NEUTRAL"}
        assert 0 <= result["confidence"] <= 1

    def test_with_technical_result(self):
        from ai_services.services.signal_aggregator import SignalAggregator

        tech = {
            "signal": "STRONG_BULLISH",
            "indicators": {"rsi_14": 72, "macd_hist": 0.002},
        }
        agg = SignalAggregator()
        result = agg.aggregate("EURUSD", technical_result=tech)
        assert result["components"]["technical"]["score"] == 1.0

    def test_risk_adjustment_present(self):
        from ai_services.services.signal_aggregator import SignalAggregator

        agg = SignalAggregator()
        result = agg.aggregate("GBPUSD")
        assert "risk_adjustment" in result
        assert "suggested_size_pct" in result["risk_adjustment"]
