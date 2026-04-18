"""
AlphaFX Pricing Engine
Core quantitative models: spot rates, cross-rates, CIP forwards, Garman-Kohlhagen options,
carry screening, pip value, implied volatility surface.
"""

import math
from dataclasses import dataclass
from typing import Optional

from scipy.stats import norm

# ─── Rate matrices ────────────────────────────────────────────────────────────

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
    "EURCHF",
    "AUDJPY",
    "GBPCHF",
    "CADJPY",
    "AUDNZD",
]

MINOR_PAIRS = [
    "USDSGD",
    "USDHKD",
    "USDMXN",
    "USDZAR",
    "USDTRY",
    "EURNOK",
    "EURSEK",
    "GBPNOK",
    "GBPSEK",
    "AUDCAD",
]

ALL_PAIRS = MAJOR_PAIRS + MINOR_PAIRS

JPY_PAIRS = {"USDJPY", "EURJPY", "GBPJPY", "CADJPY", "AUDJPY", "NZDJPY", "CHFJPY"}

FALLBACK_RATES: dict[str, float] = {
    "EURUSD": 1.0842,
    "GBPUSD": 1.2654,
    "USDJPY": 154.32,
    "USDCHF": 0.9012,
    "AUDUSD": 0.6523,
    "NZDUSD": 0.5987,
    "USDCAD": 1.3654,
    "EURGBP": 0.8567,
    "EURJPY": 167.24,
    "GBPJPY": 195.12,
    "EURCHF": 0.9765,
    "AUDJPY": 100.67,
    "GBPCHF": 1.1412,
    "CADJPY": 113.05,
    "AUDNZD": 1.0892,
    "USDSGD": 1.3421,
    "USDHKD": 7.8213,
    "USDMXN": 17.2345,
    "USDZAR": 18.7654,
    "USDTRY": 32.1456,
    "EURNOK": 11.6523,
    "EURSEK": 11.4231,
    "GBPNOK": 13.5672,
    "GBPSEK": 13.2341,
    "AUDCAD": 0.8923,
}

INTEREST_RATES: dict[str, float] = {
    "USD": 0.0533,
    "EUR": 0.0425,
    "GBP": 0.0525,
    "JPY": 0.001,
    "CHF": 0.015,
    "AUD": 0.0435,
    "NZD": 0.055,
    "CAD": 0.05,
    "SGD": 0.037,
    "HKD": 0.053,
    "MXN": 0.11,
    "ZAR": 0.082,
    "TRY": 0.50,
    "NOK": 0.045,
    "SEK": 0.04,
}

SPREAD_PIPS: dict[str, float] = {
    "EURUSD": 0.8,
    "GBPUSD": 1.0,
    "USDJPY": 0.9,
    "USDCHF": 1.2,
    "AUDUSD": 1.1,
    "NZDUSD": 1.5,
    "USDCAD": 1.3,
    "EURGBP": 1.2,
    "EURJPY": 1.4,
    "GBPJPY": 2.1,
    "EURCHF": 1.5,
    "AUDJPY": 2.0,
    "GBPCHF": 1.8,
    "CADJPY": 2.3,
    "AUDNZD": 2.5,
}

# IMF Purchasing Power Parity estimates
PPP_RATES: dict[str, float] = {
    "EURUSD": 1.10,
    "GBPUSD": 1.25,
    "USDJPY": 130.0,
    "USDCHF": 0.95,
    "AUDUSD": 0.68,
    "USDCAD": 1.28,
    "NZDUSD": 0.63,
    "EURGBP": 0.88,
    "EURJPY": 143.0,
}

# ─── Basic helpers ─────────────────────────────────────────────────────────────


def pip_size(pair: str) -> float:
    """Return pip size: 0.01 for JPY pairs, 0.0001 otherwise."""
    return 0.01 if pair.upper() in JPY_PAIRS else 0.0001


def spread_pips(pair: str) -> float:
    """Return typical bid-ask spread in pips."""
    return SPREAD_PIPS.get(pair.upper(), 2.5)


def get_spot_rate(pair: str) -> float:
    """Retrieve spot rate from fallback matrix with inverse lookup."""
    pair = pair.upper()
    if pair in FALLBACK_RATES:
        return FALLBACK_RATES[pair]
    if len(pair) == 6:
        inverse = f"{pair[3:]}{pair[:3]}"
        if inverse in FALLBACK_RATES:
            return 1.0 / FALLBACK_RATES[inverse]
    return 1.0


def pip_value(pair: str, notional: float, spot: float) -> float:
    """Calculate pip value in USD for a given notional."""
    pair = pair.upper()
    ps = pip_size(pair)
    if pair.endswith("USD"):
        return ps * notional
    if pair.startswith("USD"):
        return ps * notional / spot
    # Cross pair — approximate via USD
    return ps * notional / spot


# ─── Cross-rate ────────────────────────────────────────────────────────────────


def compute_cross_rate(base: str, quote: str, via: str = "USD") -> float:
    """Compute cross-rate via triangulation."""
    base, quote, via = base.upper(), quote.upper(), via.upper()

    if base == quote:
        return 1.0

    direct = f"{base}{quote}"
    if direct in FALLBACK_RATES:
        return FALLBACK_RATES[direct]

    inverse = f"{quote}{base}"
    if inverse in FALLBACK_RATES:
        return 1.0 / FALLBACK_RATES[inverse]

    def _rate_to_usd(ccy: str) -> Optional[float]:
        if ccy == "USD":
            return 1.0
        pair_direct = f"{ccy}USD"
        pair_inverse = f"USD{ccy}"
        if pair_direct in FALLBACK_RATES:
            return FALLBACK_RATES[pair_direct]
        if pair_inverse in FALLBACK_RATES:
            return 1.0 / FALLBACK_RATES[pair_inverse]
        return None

    base_usd = _rate_to_usd(base)
    quote_usd = _rate_to_usd(quote)
    if base_usd and quote_usd:
        return base_usd / quote_usd

    return 1.0


# ─── Forward rates (CIP) ───────────────────────────────────────────────────────


def compute_forward_rate(
    spot: float,
    base_rate: float,
    quote_rate: float,
    tenor_days: int,
) -> tuple[float, float]:
    """
    Compute forward rate using Covered Interest Parity.
    F = S * exp((r_quote - r_base) * T)
    Returns (forward_rate, forward_points_in_pips).
    """
    t = tenor_days / 365.0
    forward = spot * math.exp((quote_rate - base_rate) * t)
    forward_points = (forward - spot) * 10_000
    return forward, forward_points


# ─── Garman-Kohlhagen FX Option Pricer ────────────────────────────────────────


@dataclass
class OptionRequest:
    base: str
    quote: str
    spot: float
    strike: float
    tenor_days: int
    volatility: float
    base_rate: float
    quote_rate: float
    option_type: str  # "call" or "put"
    notional: float = 1_000_000


@dataclass
class OptionResult:
    option_type: str
    spot: float
    strike: float
    tenor_days: int
    volatility_pct: float
    price: float
    price_pct: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    intrinsic_value: float
    time_value: float
    breakeven: float
    notional_value: float


def garman_kohlhagen(req: OptionRequest) -> OptionResult:
    """
    Full Garman-Kohlhagen FX options pricer.
    Extends Black-Scholes for continuous foreign interest rate (dividend yield).
    Returns option price plus all five Greeks.
    """
    S = req.spot
    K = req.strike
    T = req.tenor_days / 365.0
    sigma = req.volatility
    r_d = req.quote_rate  # domestic (quote) rate
    r_f = req.base_rate  # foreign (base) rate
    is_call = req.option_type.lower() == "call"

    # Handle degenerate cases
    if T <= 0 or sigma <= 0:
        intrinsic = max(0.0, (S - K) if is_call else (K - S))
        return OptionResult(
            option_type=req.option_type,
            spot=S,
            strike=K,
            tenor_days=req.tenor_days,
            volatility_pct=sigma * 100,
            price=intrinsic,
            price_pct=intrinsic / S * 100,
            delta=(
                1.0
                if (is_call and S > K)
                else (-1.0 if (not is_call and S < K) else 0.0)
            ),
            gamma=0.0,
            vega=0.0,
            theta=0.0,
            rho=0.0,
            intrinsic_value=intrinsic,
            time_value=0.0,
            breakeven=S + intrinsic if is_call else S - intrinsic,
            notional_value=intrinsic * req.notional,
        )

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r_d - r_f + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    exp_rf_T = math.exp(-r_f * T)
    exp_rd_T = math.exp(-r_d * T)

    nd1 = norm.cdf(d1)
    nd2 = norm.cdf(d2)
    nnd1 = norm.cdf(-d1)
    nnd2 = norm.cdf(-d2)
    npd1 = norm.pdf(d1)

    if is_call:
        price = S * exp_rf_T * nd1 - K * exp_rd_T * nd2
        delta = exp_rf_T * nd1
        intrinsic = max(0.0, S - K)
        breakeven = K + price
        rho = K * T * exp_rd_T * nd2 / 100
        theta = (
            -(S * exp_rf_T * npd1 * sigma) / (2 * sqrt_T)
            + r_f * S * exp_rf_T * nd1
            - r_d * K * exp_rd_T * nd2
        ) / 365
    else:
        price = K * exp_rd_T * nnd2 - S * exp_rf_T * nnd1
        delta = -exp_rf_T * nnd1
        intrinsic = max(0.0, K - S)
        breakeven = K - price
        rho = -K * T * exp_rd_T * nnd2 / 100
        theta = (
            -(S * exp_rf_T * npd1 * sigma) / (2 * sqrt_T)
            - r_f * S * exp_rf_T * nnd1
            + r_d * K * exp_rd_T * nnd2
        ) / 365

    gamma = exp_rf_T * npd1 / (S * sigma * sqrt_T)
    vega = S * exp_rf_T * npd1 * sqrt_T / 100

    return OptionResult(
        option_type=req.option_type,
        spot=S,
        strike=K,
        tenor_days=req.tenor_days,
        volatility_pct=sigma * 100,
        price=price,
        price_pct=price / S * 100,
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta=theta,
        rho=rho,
        intrinsic_value=intrinsic,
        time_value=price - intrinsic,
        breakeven=breakeven,
        notional_value=price * req.notional,
    )


# ─── Carry trade screening ─────────────────────────────────────────────────────


def carry_opportunities(min_carry_bps: float = 0.0) -> list[dict]:
    """
    Screen all pairs for carry trade opportunities.
    Ranks by |r_base - r_quote| in basis points descending.
    """
    results = []
    for pair, spot in FALLBACK_RATES.items():
        if len(pair) != 6:
            continue
        base = pair[:3]
        quote = pair[3:]
        r_b = INTEREST_RATES.get(base, 0.0)
        r_q = INTEREST_RATES.get(quote, 0.0)
        carry_bps = (r_b - r_q) * 10_000
        if abs(carry_bps) < min_carry_bps:
            continue

        long_ccy = base if carry_bps > 0 else quote
        short_ccy = quote if carry_bps > 0 else base

        # Carry-to-vol ratio (Sharpe proxy)
        vol_ann = _pair_vol(pair)
        carry_to_vol = abs(r_b - r_q) / vol_ann if vol_ann > 0 else 0.0

        results.append(
            {
                "pair": pair,
                "long_currency": long_ccy,
                "short_currency": short_ccy,
                "carry_rate_bps": abs(carry_bps),
                "spot_rate": spot,
                "annualized_carry_pct": abs(r_b - r_q) * 100,
                "volatility_pct": round(vol_ann * 100, 2),
                "carry_to_vol_ratio": round(carry_to_vol, 3),
            }
        )

    return sorted(results, key=lambda x: x["carry_rate_bps"], reverse=True)


def _pair_vol(pair: str) -> float:
    """Representative annualised volatility per pair."""
    vols = {
        "EURUSD": 0.065,
        "GBPUSD": 0.075,
        "USDJPY": 0.068,
        "USDCHF": 0.062,
        "AUDUSD": 0.082,
        "NZDUSD": 0.088,
        "USDCAD": 0.071,
        "EURGBP": 0.058,
        "EURJPY": 0.079,
        "GBPJPY": 0.093,
        "USDTRY": 0.25,
        "USDZAR": 0.18,
        "USDMXN": 0.12,
    }
    return vols.get(pair.upper(), 0.075)


# ─── Implied volatility surface ────────────────────────────────────────────────


def implied_volatility_surface(pair: str) -> dict:
    """
    Build a representative implied volatility surface.
    Tenors: 1D, 7D, 1M, 2M, 3M, 6M, 1Y
    Deltas: 10Δ, 25Δ, ATM(50), 75Δ, 90Δ
    Models the vol smile (higher vol at wings, term structure upward sloping).
    """
    base_vol = _pair_vol(pair)
    tenors = [1, 7, 30, 60, 90, 180, 365]
    deltas = [10, 25, 50, 75, 90]
    surface = {}

    for t in tenors:
        # Term structure: slight upward slope with square-root dampening
        term_adj = 1.0 + 0.015 * (t / 365) ** 0.4
        term_vol = base_vol * term_adj
        surface[f"{t}D"] = {}
        for d in deltas:
            # Smile: symmetric, higher at wings
            smile_adj = 1.0 + 0.002 * ((d - 50) / 10) ** 2
            surface[f"{t}D"][str(d)] = round(term_vol * smile_adj, 5)

    return {
        "pair": pair.upper(),
        "tenors": tenors,
        "deltas": deltas,
        "surface": surface,
    }


# ─── Risk reversals & butterflies ─────────────────────────────────────────────


def volatility_risk_reversal(pair: str) -> dict:
    """
    Compute 25Δ risk reversal and butterfly for the pair.
    Risk Reversal = IV(25Δ call) - IV(25Δ put)
    Butterfly = (IV(25Δ call) + IV(25Δ put))/2 - IV(ATM)
    """
    surf = implied_volatility_surface(pair)
    atm_30d = surf["surface"]["30D"]["50"]
    c25_30d = surf["surface"]["30D"]["75"]  # 75Δ ≈ 25Δ call
    p25_30d = surf["surface"]["30D"]["25"]  # 25Δ put
    rr_25d = round(c25_30d - p25_30d, 5)
    fly_25d = round((c25_30d + p25_30d) / 2 - atm_30d, 5)
    return {
        "pair": pair.upper(),
        "rr_25d_30d": rr_25d,
        "fly_25d_30d": fly_25d,
        "atm_30d": atm_30d,
    }
