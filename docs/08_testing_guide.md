# AlphaFX Testing Guide

---

## Test Suite Overview

| Suite            | Location                                   | Framework              | Count |
| ---------------- | ------------------------------------------ | ---------------------- | ----- |
| Backend unit     | code/backend/tests/test_alphafx.py         | pytest + pytest-django | 88    |
| AI services unit | code/ai_services/tests/test_ai_services.py | pytest                 | 20    |
| Total            |                                            |                        | 108   |

---

## Running Backend Tests

```bash
cd code/backend
python -m pytest tests/ -v

# Run a specific class
python -m pytest tests/test_alphafx.py::TestGarmanKohlhagen -v

# Run with coverage
pip install pytest-cov
python -m pytest tests/ --cov=apps --cov-report=term-missing
```

---

## Backend Test Classes

| Class                 | Tests | Coverage area                                       |
| --------------------- | ----- | --------------------------------------------------- |
| TestSpotRates         | 8     | Known pairs, inverse lookup, JPY, pip size, pip val |
| TestCrossRates        | 3     | Same-currency identity, direct, triangulation       |
| TestForwardRates      | 5     | Positive/negative carry, flat, sign, tenor ordering |
| TestGarmanKohlhagen   | 11    | Price, delta bounds, gamma, vega, parity, ITM/OTM   |
| TestCarryTrade        | 5     | List, sorted descending, filter, carry-to-vol, TRY  |
| TestVolSurface        | 3     | Tenors present, ATM positive, wing >= ATM           |
| TestTechnicalAnalysis | 9     | Signal set, RSI/stoch/WR range, indicators present  |
| TestRiskEngine        | 10    | P&L sign, VaR positive, ES >= VaR, HHI, scenarios   |
| TestRatesAPI          | 12    | All rate endpoints, option Greeks, 400/404 handling |
| TestPortfolioAPI      | 8     | Full CRUD, position open, risk, 10 scenarios        |
| TestAnalyticsAPI      | 7     | Position size, R:R=2.0, SABR smile, strategy        |
| TestTechnicalAPI      | 6     | Analysis, scan, correlation, S/R, Fibonacci, HV     |
| TestHealthEndpoints   | 2     | Root returns name, health status present            |

---

## AI Services Test Classes

| Class                  | Tests | Coverage area                                     |
| ---------------------- | ----- | ------------------------------------------------- |
| TestFeatureEngineering | 7     | Matrix shape, target binary, RSI range, sequences |
| TestLSTMForecaster     | 4     | Fit/predict, binary output, fallback, save/load   |
| TestRegimeDetector     | 4     | State labels, prob sum=1, duration coverage       |
| TestGARCHForecaster    | 3     | Forecast shape, positive vol, NIC length=41       |
| TestAnomalyDetector    | 3     | Columns, severity set, crash injection detected   |
| TestSentimentService   | 4     | Rule scores, CCY detection, macro range, dict     |
| TestSignalAggregator   | 3     | Valid signal, technical score, risk_adjustment    |

---

## Key Assertions

### Put-call parity (TestGarmanKohlhagen)

Verifies: C - P = S _ exp(-r_f _ T) - K _ exp(-r_d _ T)
Tolerance: 5e-5

### VaR monotonicity (TestRiskEngine)

Verifies: VaR_10d >= VaR_1d and ES >= VaR_1d
(Both hold under square-root-of-time scaling)

### HHI edge cases (TestRiskEngine)

Single position: HHI = 1.0 (maximum concentration)
Two equal positions: HHI = 0.5

### Risk/reward ratio (TestAnalyticsAPI)

Entry=1.0850, SL=1.0800, TP=1.0950, side=buy
Expected: risk_pips=50, reward_pips=100, rr=2.0

### Strategy builder straddle (TestAnalyticsAPI)

Two legs (call+put, same strike, same tenor, both long)
Expected strategy_name: "Long Straddle"
Expected payoff table length: 21 (11 points from -10% to +10%)

---

## CI Pipeline

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: "3.12" }
      - run: pip install -r code/backend/requirements.txt
      - run: cd code/backend && python -m pytest tests/ -v
```

---

## Test Configuration

The backend pytest configuration is in `code/backend/pytest.ini`:

| Setting                | Value                 |
| ---------------------- | --------------------- |
| DJANGO_SETTINGS_MODULE | alphafx.settings.base |
| python_files           | tests/test\_\*.py     |
| python_classes         | Test\*                |
| python_functions       | test\_\*              |
| addopts                | -v --tb=short         |

---

## Writing New Tests

### Backend API test pattern

```python
class TestMyFeature(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_my_endpoint(self):
        resp = self.client.get("/api/v1/my-endpoint/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("expected_key", resp.data)
```

### AI service test pattern

```python
class TestMyModel(TestCase):
    @pytest.fixture(autouse=True)
    def setup(self, sample_ohlcv):
        self.df = sample_ohlcv

    def test_model_output(self):
        from ai_services.models.my_model import MyModel
        model = MyModel()
        model.fit(self.df["close"])
        result = model.predict(self.df["close"])
        assert result is not None
```
