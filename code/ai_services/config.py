"""
AlphaFX AI Services Configuration
"""

import os
from dataclasses import dataclass


@dataclass
class AIConfig:
    # Model storage
    model_dir: str = os.environ.get("AI_MODEL_DIR", "./saved_models")

    # Forecasting
    lstm_lookback: int = 60  # bars of history fed to LSTM
    lstm_horizon: int = 5  # bars ahead to forecast
    lstm_epochs: int = 50
    lstm_batch_size: int = 32
    lstm_hidden_size: int = 64
    lstm_num_layers: int = 2
    lstm_dropout: float = 0.2

    # Regime detection
    hmm_n_states: int = 3  # Bull / Bear / Ranging
    hmm_n_iter: int = 100

    # Sentiment
    sentiment_model: str = "ProsusAI/finbert"
    sentiment_cache_ttl: int = 300  # seconds

    # GARCH
    garch_p: int = 1
    garch_q: int = 1
    garch_dist: str = "skewt"

    # Anomaly detection
    isolation_forest_contamination: float = 0.05
    zscore_window: int = 20
    zscore_threshold: float = 3.0

    # Feature engineering
    feature_lookback: int = 252  # trading days for feature window

    # Serving
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/1")


config = AIConfig()
