# AlphaFX AI and ML Services

The AI services layer provides machine learning inference on top of the core
quantitative analytics. It runs as a separate FastAPI microservice on port 8001
and communicates with the Django backend through internal HTTP calls.

---

## Model Inventory

| Model             | File                          | Algorithm            | Output                           |
| ----------------- | ----------------------------- | -------------------- | -------------------------------- |
| LSTM Forecaster   | models/lstm_forecaster.py     | BiLSTM + Attention   | P(price up) in [0, 1]            |
| Regime Detector   | models/regime_detector.py     | Gaussian HMM         | BULL / BEAR / RANGING + probs    |
| GARCH Forecaster  | models/garch_vol.py           | GJR-GARCH, skewed-t  | Daily/annual vol forecast        |
| Anomaly Detector  | models/anomaly_detector.py    | Isolation Forest + Z | anomaly flag, severity, scores   |
| Sentiment Service | services/sentiment.py         | FinBERT + lexicon    | label, score, per-currency aggr. |
| Signal Aggregator | services/signal_aggregator.py | Weighted ensemble    | BUY/SELL/NEUTRAL + confidence    |

---

## LSTM Price Direction Forecaster

### Architecture

```
Input: (batch, lookback=60, n_features=40+)
  -> BiLSTM layer 1 (hidden=64, bidirectional -> 128)
  -> BiLSTM layer 2 (hidden=64, bidirectional -> 128)
  -> Temporal Attention (128 -> context vector of size 128)
  -> Dropout (0.2)
  -> Dense 128 -> 32 -> ReLU -> Dropout -> Dense 1 -> Sigmoid
Output: scalar probability in [0, 1]
```

### Training procedure

| Hyperparameter    | Value                          |
| ----------------- | ------------------------------ |
| Optimiser         | Adam                           |
| Learning rate     | 1e-3                           |
| LR scheduler      | ReduceLROnPlateau (patience=5) |
| Gradient clipping | 1.0                            |
| Epochs            | 50                             |
| Batch size        | 32                             |
| Validation split  | 15%                            |
| Early stopping    | Best val_loss checkpoint saved |
| Loss function     | Binary cross-entropy           |

### Feature set (40+ features)

| Category    | Features                                           |
| ----------- | -------------------------------------------------- |
| Momentum    | Returns at 1, 2, 3, 5, 10, 21 bars                 |
| Trend       | Price / SMA ratio at 10, 20, 50, 100, 200 bars     |
| EMA crosses | EMA20/50, EMA50/200 ratio                          |
| RSI         | RSI-7, RSI-14, RSI-21 (normalised to [0,1])        |
| MACD        | MACD line, signal, histogram (normalised by price) |
| Bollinger   | Band position [-1, +1]                             |
| ATR         | ATR-7, ATR-14 (normalised by price)                |
| Stochastic  | %K, %D, cross                                      |
| Williams %R | Williams %R (normalised to [0,1])                  |
| Volatility  | HV-5, HV-10, HV-21, HV-63, vol ratio 5/21          |
| Volume      | Volume ratio, volume trend                         |
| Candle      | Body size, upper wick, lower wick, bullish flag    |
| Levels      | Distance from 52-week high and low                 |
| Lag returns | Lagged returns at 1, 2, 3, 5 bars                  |

### Fallback

When PyTorch is not available, the model falls back to logistic regression
using scikit-learn on the flattened feature matrix.

---

## Regime Detector

### Hidden Markov Model

A 3-state Gaussian HMM is fit to a 2-dimensional observation vector:

```
observation = [daily_return, log(rolling_5d_vol * sqrt(252))]
```

After fitting, states are ranked by mean return:

- Rank 0 (lowest mean return): BEAR
- Rank 1 (middle mean return): RANGING
- Rank 2 (highest mean return): BULL

### Output

| Field            | Type   | Description                          |
| ---------------- | ------ | ------------------------------------ |
| regime           | string | Current state label                  |
| probabilities    | dict   | Posterior probability for each state |
| current_duration | int    | Consecutive bars in current regime   |
| recent_regimes   | list   | Last 5 regime segments with dates    |

---

## GARCH Volatility Forecasting

### Model specification

GJR-GARCH(1,1) with skewed Student-t innovations:

```
r_t = mu + epsilon_t
epsilon_t = sigma_t * z_t,   z_t ~ skewed-t(eta, lambda)
sigma_t^2 = omega + (alpha + gamma * I(epsilon_{t-1}<0)) * epsilon_{t-1}^2 + beta * sigma_{t-1}^2
```

The asymmetry term gamma captures the leverage effect (negative shocks
increase volatility more than positive shocks of equal magnitude).

### News Impact Curve

The NIC plots next-period conditional variance as a function of the
current period innovation:

```
For GJR:  h(epsilon) = omega + (alpha + gamma * I(epsilon<0)) * epsilon^2 + beta * h_last
```

### Volatility regime mapping

| Daily vol (pct) | Regime      | Position size multiplier |
| --------------- | ----------- | ------------------------ |
| < 0.5%          | LOW_VOL     | 1.1 (increase size)      |
| 0.5% to 1.0%    | NORMAL      | 1.0                      |
| 1.0% to 1.5%    | HIGH_VOL    | 0.8 (reduce size)        |
| > 1.5%          | EXTREME_VOL | 0.5 (halve size)         |

---

## Anomaly Detector

### Two-layer architecture

Layer 1: Z-score on returns and range:

```
z_ret   = (r_t - rolling_mean(r, 20)) / rolling_std(r, 20)
z_range = (hl_range_t - rolling_mean(hl, 20)) / rolling_std(hl, 20)
flag    = |z_ret| > 3.5  OR  |z_range| > 3.5
```

Layer 2: Isolation Forest on 7-dimensional feature space including
returns, range, gap, volume Z-score, return Z-score, range Z-score.

### Severity classification

| Condition                        | Severity |
| -------------------------------- | -------- | ----------------------- | ------ |
| No flag from either layer        | NORMAL   |
| Either layer flags, mild signals | LOW      |
|                                  | ret_z    | > 4 or IF score < -0.20 | MEDIUM |
|                                  | ret_z    | > 5 or IF score < -0.30 | HIGH   |

---

## Sentiment Service

### Primary model: FinBERT

ProsusAI/finbert is a BERT model fine-tuned on financial news.
It classifies text into positive/negative/neutral with associated
probability scores.

If the model or network is unavailable, the service degrades to
a rule-based lexicon scorer using curated FX-relevant keywords.

### Currency mention detection

Each headline is scanned for terms associated with each G10 currency:

| Currency | Detection terms                              |
| -------- | -------------------------------------------- |
| USD      | dollar, usd, fed, fomc, powell, us economy   |
| EUR      | euro, eur, ecb, lagarde, eurozone            |
| GBP      | pound, gbp, boe, bank of england, uk economy |
| JPY      | yen, jpy, boj, bank of japan, ueda           |
| AUD      | aussie, aud, rba, australia                  |
| NZD      | kiwi, nzd, rbnz, new zealand                 |
| CAD      | loonie, cad, boc, bank of canada, oil price  |
| CHF      | franc, chf, snb, swiss                       |

### Macro sentiment index

```
index = mean(positive_score - negative_score) over all headlines
regime = RISK_ON  if index > +0.15
regime = RISK_OFF if index < -0.15
regime = NEUTRAL  otherwise
```

---

## Signal Aggregator

### Component weights

| Component | Weight | Direction score range       |
| --------- | ------ | --------------------------- |
| Technical | 0.25   | [-1, +1]                    |
| LSTM      | 0.30   | (prob - 0.5) \* 2           |
| Regime    | 0.20   | P(BULL) - P(BEAR)           |
| Sentiment | 0.15   | index \* 2 (capped at +/-1) |
| GARCH     | 0.10   | Size adjustment only        |

### Final signal thresholds

| Weighted score | Signal  |
| -------------- | ------- |
| > +0.25        | BUY     |
| -0.25 to +0.25 | NEUTRAL |
| < -0.25        | SELL    |

Confidence is mapped as: confidence = 0.5 + |score| \* 0.5

---

## Training Pipeline

Run the training pipeline from the ai_services directory:

```bash
# Train all major pairs
python -m training.train_all --pairs all --output-dir ./saved_models

# Train specific pairs
python -m training.train_all --pairs EURUSD GBPUSD USDJPY

# Custom lookback window
python -m training.train_all --pairs EURUSD --lookback 90
```

### Output structure per pair

| File                                | Contents                        |
| ----------------------------------- | ------------------------------- |
| saved_models/EURUSD/lstm/           | weights.pt + meta.json          |
| saved_models/EURUSD/regime/         | hmm_model.joblib + meta.json    |
| saved_models/EURUSD/garch/          | garch_result.joblib + meta.json |
| saved_models/EURUSD/anomaly/        | iso_forest.joblib + meta.json   |
| saved_models/training_manifest.json | Training summary + metrics      |

---

## AI Service Tests

Run from the ai_services directory:

```bash
pytest tests/test_ai_services.py -v
```

| Test class             | Coverage                                       |
| ---------------------- | ---------------------------------------------- |
| TestFeatureEngineering | Matrix shape, target binary, RSI range, no NaN |
| TestLSTMForecaster     | Fit, predict, fallback, save/load              |
| TestRegimeDetector     | State labels, prob sum=1, duration coverage    |
| TestGARCHForecaster    | Forecast shape, positive vol, NIC length       |
| TestAnomalyDetector    | Detect columns, severity set, crash injection  |
| TestSentimentService   | Rule-based scores, CCY detection, macro range  |
| TestSignalAggregator   | Valid signal, risk_adjustment present          |
