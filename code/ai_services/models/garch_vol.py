"""
AlphaFX AI Services - GARCH Volatility Forecaster
Fits GARCH(p,q) and GJR-GARCH models to model conditional heteroskedasticity
in FX returns.  Produces multi-step volatility forecasts used for:
  - Option pricing with forward-looking vol
  - Position sizing based on predicted ATR
  - Risk limit calibration
  - Regime-conditional VaR

Dependencies: arch (pip install arch)

Usage:
  from ai_services.models.garch_vol import GARCHForecaster
  gf = GARCHForecaster(pair="EURUSD")
  gf.fit(close_series)
  forecast = gf.forecast(horizon=10)
  print(forecast["annualized_vol_pct"])
"""

import json
import os
from typing import Optional

import numpy as np
import pandas as pd


class GARCHForecaster:
    """
    Wrapper around the arch library GARCH family models.

    Models supported:
      garch    - Standard GARCH(p, q)
      gjr      - GJR-GARCH (asymmetric, captures leverage effect)
      egarch   - EGARCH (log volatility, no positivity constraint)

    Distribution:
      normal, t, skewt (recommended for FX - captures fat tails and skew)
    """

    def __init__(
        self,
        pair: str = "EURUSD",
        p: int = 1,
        q: int = 1,
        model: str = "gjr",  # garch | gjr | egarch
        dist: str = "skewt",  # normal | t | skewt
        mean: str = "Constant",  # Constant | Zero | AR
    ):
        self.pair = pair
        self.p = p
        self.q = q
        self.model = model
        self.dist = dist
        self.mean = mean
        self._result = None
        self._fitted = False
        self._last_returns: Optional[pd.Series] = None

    # ---- Fitting -----------------------------------------------------------

    def fit(self, close: pd.Series) -> "GARCHForecaster":
        """Fit the GARCH model to a closing-price series."""
        try:
            from arch import arch_model
        except ImportError:
            self._fitted = False
            return self

        ret = np.log(close / close.shift(1)).dropna() * 100  # percent returns
        self._last_returns = ret

        vol_map = {"garch": "GARCH", "gjr": "GARCH", "egarch": "EGARCH"}
        vol_type = vol_map.get(self.model, "GARCH")

        am = arch_model(
            ret,
            vol=vol_type,
            p=self.p,
            q=self.q,
            o=(1 if self.model == "gjr" else 0),  # GJR asymmetry order
            dist=self.dist,
            mean=self.mean,
            rescale=False,
        )
        self._result = am.fit(disp="off", show_warning=False)
        self._fitted = True
        return self

    # ---- Forecasting -------------------------------------------------------

    def forecast(self, horizon: int = 10) -> dict:
        """
        Produce multi-step conditional variance forecasts.

        Returns a dict with:
          daily_vol_pct     - list of daily vol forecasts in percent
          annualized_vol_pct - annualised equiv (vol * sqrt(252))
          var_95_pct        - parametric 95% VaR as % of position
          current_vol       - last in-sample conditional vol
        """
        if not self._fitted or self._result is None:
            vol = 0.7  # rough FX daily vol fallback in pct
            daily_vols = [vol] * horizon
        else:
            fc = self._result.forecast(horizon=horizon, reindex=False)
            # variance is in (pct)^2 -- take sqrt
            daily_vols = list(np.sqrt(fc.variance.values[-1]))

        annualized = [v * np.sqrt(252) for v in daily_vols]
        from scipy.stats import norm

        var_95 = [norm.ppf(0.95) * v / 100 for v in daily_vols]

        return {
            "pair": self.pair,
            "horizon_days": horizon,
            "daily_vol_pct": [round(v, 4) for v in daily_vols],
            "annualized_vol_pct": [round(v, 4) for v in annualized],
            "var_95_1day_pct": round(var_95[0] * 100, 4) if var_95 else 0.0,
            "current_vol_pct": round(daily_vols[0], 4) if daily_vols else 0.0,
            "model": self.model,
            "dist": self.dist,
        }

    def current_conditional_vol(self) -> float:
        """Return the most recent in-sample conditional daily vol (pct)."""
        if not self._fitted or self._result is None:
            return 0.7
        cond_vol = np.sqrt(self._result.conditional_volatility)
        return float(cond_vol.iloc[-1])

    def news_impact_curve(self, shock_range: Optional[np.ndarray] = None) -> list[dict]:
        """
        Compute the News Impact Curve: how a shock of size epsilon
        affects next-period conditional variance.
        """
        if shock_range is None:
            shock_range = np.linspace(-5.0, 5.0, 41)

        if not self._fitted or self._result is None:
            return [{"shock": float(s), "conditional_vol": 0.7} for s in shock_range]

        params = self._result.params
        omega = params.get("omega", 0.01)
        alpha = params.get("alpha[1]", 0.08)
        beta = params.get("beta[1]", 0.88)
        gamma = params.get("gamma[1]", 0.05)  # GJR term
        last_var = self.current_conditional_vol() ** 2

        results = []
        for eps in shock_range:
            if self.model == "gjr":
                indicator = 1.0 if eps < 0 else 0.0
                new_var = omega + (alpha + gamma * indicator) * eps**2 + beta * last_var
            else:
                new_var = omega + alpha * eps**2 + beta * last_var
            results.append(
                {
                    "shock": round(float(eps), 2),
                    "conditional_vol": round(float(np.sqrt(max(new_var, 0))), 4),
                }
            )
        return results

    # ---- Summary -----------------------------------------------------------

    def summary(self) -> dict:
        """Return model diagnostics and parameter estimates."""
        if not self._fitted or self._result is None:
            return {"fitted": False}

        params = dict(self._result.params)
        pvals = dict(self._result.pvalues)
        return {
            "pair": self.pair,
            "model": self.model,
            "dist": self.dist,
            "aic": round(float(self._result.aic), 2),
            "bic": round(float(self._result.bic), 2),
            "log_likelihood": round(float(self._result.loglikelihood), 2),
            "parameters": {k: round(float(v), 6) for k, v in params.items()},
            "p_values": {k: round(float(v), 4) for k, v in pvals.items()},
        }

    # ---- Persistence -------------------------------------------------------

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        meta = {
            "pair": self.pair,
            "p": self.p,
            "q": self.q,
            "model": self.model,
            "dist": self.dist,
            "fitted": self._fitted,
        }
        with open(os.path.join(path, "garch_meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        if self._fitted and self._result is not None:
            import joblib

            joblib.dump(self._result, os.path.join(path, "garch_result.joblib"))

    @classmethod
    def load(cls, path: str) -> "GARCHForecaster":
        with open(os.path.join(path, "garch_meta.json")) as f:
            meta = json.load(f)
        g = cls(**{k: meta[k] for k in ("pair", "p", "q", "model", "dist")})
        g._fitted = meta.get("fitted", False)
        r_path = os.path.join(path, "garch_result.joblib")
        if os.path.exists(r_path):
            import joblib

            g._result = joblib.load(r_path)
        return g
