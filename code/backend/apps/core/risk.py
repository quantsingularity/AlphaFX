"""
AlphaFX Risk Analytics Engine
VaR (Historical Simulation), Expected Shortfall, Net Currency Exposure,
Herfindahl-Hirschman Index, Macro Scenario Analysis.
"""

import numpy as np
from apps.core.pricing import FALLBACK_RATES

# ─── P&L calculation ──────────────────────────────────────────────────────────


def position_pnl(
    pair: str,
    side: str,
    notional: float,
    entry_rate: float,
    current_rate: float,
) -> float:
    """
    Calculate unrealized P&L for an FX position in USD terms.
    USD-quote pairs: direct rate difference.
    USD-base pairs: inverse calculation.
    Cross pairs: approximate via rate difference.
    """
    pair = pair.upper()
    if pair.endswith("USD"):
        raw = (current_rate - entry_rate) * notional
    elif pair.startswith("USD"):
        raw = (1 / entry_rate - 1 / current_rate) * notional
    else:
        # Cross pair — express PnL in quote currency, approximate to USD
        raw = (current_rate - entry_rate) * notional

    return raw if side.lower() == "buy" else -raw


# ─── Value at Risk ─────────────────────────────────────────────────────────────


def portfolio_var(
    positions: list[dict],
    confidence_level: float = 0.99,
    holding_period_days: int = 1,
    lookback_days: int = 252,
) -> dict:
    """
    Historical simulation VaR and Expected Shortfall.
    Simulates 252-day GBM paths per position, aggregates portfolio P&L,
    then takes percentile at (1 - confidence_level).
    Scaled to holding_period by square-root-of-time rule.
    """
    if not positions:
        return {
            "var_1d": 0.0,
            "var_10d": 0.0,
            "expected_shortfall": 0.0,
            "confidence_level": confidence_level,
            "holding_period_days": holding_period_days,
        }

    rng = np.random.default_rng(42)
    n = lookback_days
    pnl_series = np.zeros(n)

    for pos in positions:
        pair = pos["pair"].upper()
        side = pos["side"]
        notional = pos["notional"]
        spot = FALLBACK_RATES.get(pair, 1.0)

        # Pair-specific vol from representative matrix
        daily_vol = _daily_vol(pair)
        log_rets = rng.normal(0.00005, daily_vol, n)

        rates_path = spot * np.exp(np.cumsum(log_rets))
        prev_rates = np.roll(rates_path, 1)
        prev_rates[0] = spot

        if pair.endswith("USD"):
            daily_pnl = (rates_path - prev_rates) * notional
        elif pair.startswith("USD"):
            daily_pnl = (1 / rates_path - 1 / prev_rates) * notional
        else:
            daily_pnl = (rates_path - prev_rates) * notional / spot

        if side.lower() == "sell":
            daily_pnl = -daily_pnl

        pnl_series += daily_pnl

    # Scale to holding period
    scaled = pnl_series * np.sqrt(holding_period_days)
    cutoff = np.percentile(scaled, (1 - confidence_level) * 100)
    es = float(np.mean(scaled[scaled <= cutoff]))
    var_1d = float(np.percentile(pnl_series, (1 - confidence_level) * 100))
    var_10d = float(
        np.percentile(pnl_series * np.sqrt(10), (1 - confidence_level) * 100)
    )

    return {
        "var_1d": abs(var_1d),
        "var_10d": abs(var_10d),
        "expected_shortfall": abs(es),
        "confidence_level": confidence_level,
        "holding_period_days": holding_period_days,
    }


def _daily_vol(pair: str) -> float:
    """Representative daily volatility per pair."""
    vols = {
        "EURUSD": 0.006,
        "GBPUSD": 0.007,
        "USDJPY": 0.0065,
        "USDCHF": 0.006,
        "AUDUSD": 0.008,
        "NZDUSD": 0.009,
        "USDCAD": 0.007,
        "EURGBP": 0.005,
        "EURJPY": 0.008,
        "GBPJPY": 0.009,
        "USDTRY": 0.018,
        "USDZAR": 0.015,
        "USDMXN": 0.010,
    }
    return vols.get(pair.upper(), 0.007)


# ─── Currency exposure ─────────────────────────────────────────────────────────


def net_currency_exposure(positions: list[dict]) -> dict[str, float]:
    """
    Net long/short exposure by currency (in notional terms).
    Decomposes each pair into base and quote legs.
    """
    exposure: dict[str, float] = {}
    for pos in positions:
        pair = pos["pair"].upper()
        if len(pair) != 6:
            continue
        base = pair[:3]
        quote = pair[3:]
        notional = pos["notional"]

        if pos["side"].lower() == "buy":
            exposure[base] = exposure.get(base, 0.0) + notional
            exposure[quote] = exposure.get(quote, 0.0) - notional
        else:
            exposure[base] = exposure.get(base, 0.0) - notional
            exposure[quote] = exposure.get(quote, 0.0) + notional

    return {k: round(v, 2) for k, v in exposure.items()}


# ─── Concentration ────────────────────────────────────────────────────────────


def herfindahl_index(positions: list[dict]) -> float:
    """
    Herfindahl-Hirschman Index for position concentration.
    0 = fully diversified, 1 = single position monopoly.
    """
    if not positions:
        return 0.0
    total = sum(p["notional"] for p in positions)
    if total == 0:
        return 0.0
    weights = [p["notional"] / total for p in positions]
    return float(sum(w**2 for w in weights))


# ─── Scenario analysis ────────────────────────────────────────────────────────

STANDARD_SCENARIOS = [
    ("USD Strength +5%", {"USD": 0.05}),
    ("USD Weakness -5%", {"USD": -0.05}),
    ("EUR Rally +3%", {"EUR": 0.03}),
    ("EUR Selloff -3%", {"EUR": -0.03}),
    ("JPY Safe Haven +10%", {"JPY": 0.10}),
    ("JPY Carry Unwind -10%", {"JPY": -0.10}),
    ("Risk-Off (USD+5, JPY+3, CHF+2)", {"USD": 0.05, "JPY": 0.03, "CHF": 0.02}),
    ("Risk-On (USD-3, AUD+2, NZD+2)", {"USD": -0.03, "AUD": 0.02, "NZD": 0.02}),
    ("EM Crisis (USD+8, TRY-20, ZAR-10)", {"USD": 0.08, "TRY": -0.20, "ZAR": -0.10}),
    ("Commodity Boom (AUD+5, CAD+4, USD-2)", {"AUD": 0.05, "CAD": 0.04, "USD": -0.02}),
]


def run_fx_scenarios(
    positions: list[dict],
    base_equity: float,
) -> list[dict]:
    """Run all standard macro scenarios and return P&L impact."""
    results = []
    for name, shifts in STANDARD_SCENARIOS:
        pnl = _scenario_pnl(positions, shifts)
        results.append(
            {
                "scenario_name": name,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl / base_equity * 100 if base_equity else 0.0, 4),
                "new_equity": round(base_equity + pnl, 2),
            }
        )
    return results


def _scenario_pnl(positions: list[dict], shifts: dict[str, float]) -> float:
    """Calculate total P&L for a given set of currency shifts."""
    total = 0.0
    for pos in positions:
        pair = pos["pair"].upper()
        if len(pair) != 6:
            continue
        base = pair[:3]
        quote = pair[3:]
        spot = FALLBACK_RATES.get(pair, 1.0)
        notional = pos["notional"]

        base_shift = shifts.get(base, 0.0)
        quote_shift = shifts.get(quote, 0.0)
        net_shift = base_shift - quote_shift
        new_spot = spot * (1 + net_shift)

        if pair.endswith("USD"):
            raw_pnl = (new_spot - spot) * notional
        elif pair.startswith("USD"):
            raw_pnl = (1 / new_spot - 1 / spot) * notional
        else:
            raw_pnl = (new_spot - spot) * notional / spot

        total += raw_pnl if pos["side"].lower() == "buy" else -raw_pnl

    return total
