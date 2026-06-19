"""
Analytics API views:
- Position sizing (fixed-risk / Kelly)
- Risk-reward ratio
- Swap rates
- Purchasing Power Parity
- SABR smile calibration (new)
- Multi-leg FX strategy builder (new)
- Correlation-adjusted position sizing (new)
"""

import math

from apps.core.pricing import (
    FALLBACK_RATES,
    INTEREST_RATES,
    PPP_RATES,
    OptionRequest,
    _pair_vol,
    compute_forward_rate,
    garman_kohlhagen,
    get_spot_rate,
    pip_size,
    pip_value,
)
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

# ─── Serializers ───────────────────────────────────────────────────────────────


class PositionSizeSerializer(serializers.Serializer):
    account_balance = serializers.FloatField(min_value=1.0)
    risk_pct = serializers.FloatField(min_value=0.01, max_value=100.0, default=1.0)
    stop_loss_pips = serializers.FloatField(min_value=0.1)
    pair = serializers.CharField(max_length=6)
    leverage = serializers.FloatField(min_value=1.0, default=1.0)


class RiskRewardSerializer(serializers.Serializer):
    entry = serializers.FloatField(min_value=0.0001)
    stop_loss = serializers.FloatField(min_value=0.0001)
    take_profit = serializers.FloatField(min_value=0.0001)
    pair = serializers.CharField(max_length=6)
    side = serializers.ChoiceField(choices=["buy", "sell"], default="buy")


class PipValueSerializer(serializers.Serializer):
    pair = serializers.CharField(max_length=6)
    notional = serializers.FloatField(min_value=1.0)


class SABRSerializer(serializers.Serializer):
    pair = serializers.CharField(max_length=6)
    forward = serializers.FloatField(min_value=0.0001)
    tenor_days = serializers.IntegerField(min_value=1, max_value=3650)
    atm_vol = serializers.FloatField(min_value=0.001, max_value=5.0)
    rr_25d = serializers.FloatField(default=0.0, help_text="25-delta risk reversal")
    fly_25d = serializers.FloatField(default=0.003, help_text="25-delta butterfly")


class StrategyLegSerializer(serializers.Serializer):
    option_type = serializers.ChoiceField(choices=["call", "put"])
    strike = serializers.FloatField(min_value=0.0001)
    tenor_days = serializers.IntegerField(min_value=1, max_value=3650)
    notional = serializers.FloatField(min_value=1.0, default=1_000_000)
    direction = serializers.ChoiceField(choices=["long", "short"], default="long")


class StrategyBuilderSerializer(serializers.Serializer):
    pair = serializers.CharField(max_length=6)
    legs = StrategyLegSerializer(many=True, min_length=1, max_length=6)
    spot = serializers.FloatField(min_value=0.0001, required=False)
    volatility = serializers.FloatField(min_value=0.001, max_value=5.0, default=0.08)
    base_rate = serializers.FloatField(min_value=-0.1, max_value=0.5, required=False)
    quote_rate = serializers.FloatField(min_value=-0.1, max_value=0.5, required=False)


# ─── Views ─────────────────────────────────────────────────────────────────────


class PositionSizeView(APIView):
    """POST /api/v1/analytics/position-size — Fixed-risk position sizing."""

    @extend_schema(
        tags=["analytics"], summary="Calculate position size from risk parameters"
    )
    def post(self, request):
        ser = PositionSizeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        pair = d["pair"].upper()
        spot = get_spot_rate(pair)
        pv = pip_value(pair, 1.0, spot)

        if pv == 0:
            return Response(
                {"error": "Cannot compute pip value for this pair"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        risk_amount = d["account_balance"] * d["risk_pct"] / 100
        raw_units = risk_amount / (d["stop_loss_pips"] * pv)
        lots = raw_units / 100_000
        margin_req = (raw_units * spot) / d["leverage"]

        # Kelly fraction approximation (simplified)
        win_rate_est = 0.5
        avg_rr_est = 1.5
        kelly_pct = win_rate_est - (1 - win_rate_est) / avg_rr_est
        kelly_units = (
            d["account_balance"] * max(kelly_pct, 0) / (d["stop_loss_pips"] * pv)
        )

        return Response(
            {
                "pair": pair,
                "account_balance": d["account_balance"],
                "risk_pct": d["risk_pct"],
                "risk_amount_usd": round(risk_amount, 2),
                "stop_loss_pips": d["stop_loss_pips"],
                "recommended_units": round(raw_units),
                "recommended_lots": round(lots, 2),
                "notional": round(raw_units * spot, 2),
                "margin_required": round(margin_req, 2),
                "pip_value_per_unit": round(pv, 6),
                "spot_rate": round(spot, 5),
                "kelly_units": round(kelly_units),
                "kelly_lots": round(kelly_units / 100_000, 2),
            }
        )


class RiskRewardView(APIView):
    """POST /api/v1/analytics/risk-reward — Risk-reward ratio."""

    @extend_schema(tags=["analytics"], summary="Calculate risk-reward ratio")
    def post(self, request):
        ser = RiskRewardSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        pair = d["pair"].upper()
        ps = pip_size(pair)

        if d["side"] == "buy":
            risk_pips = (d["entry"] - d["stop_loss"]) / ps
            reward_pips = (d["take_profit"] - d["entry"]) / ps
        else:
            risk_pips = (d["stop_loss"] - d["entry"]) / ps
            reward_pips = (d["entry"] - d["take_profit"]) / ps

        rr = reward_pips / risk_pips if risk_pips > 0 else 0.0
        breakeven_wr = 1 / (1 + rr) * 100 if rr > 0 else 50.0

        # Expected value at 50% win rate
        ev_50 = 0.5 * reward_pips - 0.5 * abs(risk_pips)

        return Response(
            {
                "pair": pair,
                "side": d["side"],
                "entry": d["entry"],
                "stop_loss": d["stop_loss"],
                "take_profit": d["take_profit"],
                "risk_pips": round(risk_pips, 1),
                "reward_pips": round(reward_pips, 1),
                "risk_reward_ratio": round(rr, 2),
                "breakeven_win_rate_pct": round(breakeven_wr, 1),
                "expected_value_at_50pct_wr": round(ev_50, 1),
            }
        )


class PipValueView(APIView):
    """POST /api/v1/analytics/pip-value — Pip value for any notional."""

    @extend_schema(tags=["analytics"], summary="Calculate pip value")
    def post(self, request):
        ser = PipValueSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        pair = d["pair"].upper()
        spot = get_spot_rate(pair)
        pv = pip_value(pair, d["notional"], spot)

        return Response(
            {
                "pair": pair,
                "notional": d["notional"],
                "spot": round(spot, 5),
                "pip_size": pip_size(pair),
                "pip_value_usd": round(pv, 4),
            }
        )


class SwapRatesView(APIView):
    """GET /api/v1/analytics/swap-rates — Swap / rollover rates for all pairs."""

    @extend_schema(tags=["analytics"], summary="Swap rates for all pairs")
    def get(self, request):
        results = []
        for pair, spot in FALLBACK_RATES.items():
            if len(pair) != 6:
                continue
            base = pair[:3]
            quote = pair[3:]
            r_b = INTEREST_RATES.get(base, 0.03)
            r_q = INTEREST_RATES.get(quote, 0.03)
            fwd_1w, pts_1w = compute_forward_rate(spot, r_b, r_q, 7)
            fwd_1m, pts_1m = compute_forward_rate(spot, r_b, r_q, 30)
            fwd_3m, pts_3m = compute_forward_rate(spot, r_b, r_q, 90)

            # Daily swap cost in pips
            daily_pts = pts_1w / 7

            results.append(
                {
                    "pair": pair,
                    "spot": round(spot, 5),
                    "base_rate": r_b,
                    "quote_rate": r_q,
                    "carry_bps": round((r_b - r_q) * 10_000, 1),
                    "forward_points_1w": round(pts_1w, 4),
                    "forward_points_1m": round(pts_1m, 4),
                    "forward_points_3m": round(pts_3m, 4),
                    "daily_swap_pips": round(daily_pts, 4),
                    "annualized_swap_pct": round((r_q - r_b) * 100, 3),
                }
            )

        results.sort(key=lambda x: abs(x["carry_bps"]), reverse=True)
        return Response({"swap_rates": results})


class PPPView(APIView):
    """GET /api/v1/analytics/purchasing-power-parity — PPP deviation analysis."""

    @extend_schema(tags=["analytics"], summary="Purchasing Power Parity analysis")
    def get(self, request):
        results = []
        for pair, ppp in PPP_RATES.items():
            spot = get_spot_rate(pair)
            dev = (spot - ppp) / ppp * 100
            vol = _pair_vol(pair) * 100

            # Z-score: how many vols away from fair value?
            z_score = dev / vol if vol > 0 else 0.0

            results.append(
                {
                    "pair": pair,
                    "spot": round(spot, 5),
                    "ppp_rate": ppp,
                    "deviation_pct": round(dev, 2),
                    "overvalued": dev > 0,
                    "vol_pct": round(vol, 2),
                    "z_score": round(z_score, 2),
                    "mean_reversion_signal": (
                        "STRONG_SELL"
                        if dev > 2 * vol
                        else (
                            "SELL"
                            if dev > vol
                            else (
                                "STRONG_BUY"
                                if dev < -2 * vol
                                else "BUY" if dev < -vol else "NEUTRAL"
                            )
                        )
                    ),
                }
            )

        results.sort(key=lambda x: abs(x["deviation_pct"]), reverse=True)
        return Response({"ppp_analysis": results})


class SABRSmileView(APIView):
    """POST /api/v1/analytics/sabr-smile — SABR smile calibration."""

    @extend_schema(tags=["analytics"], summary="SABR volatility smile calibration")
    def post(self, request):
        ser = SABRSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        F = d["forward"]
        T = d["tenor_days"] / 365.0
        atm = d["atm_vol"]
        rr = d["rr_25d"]
        fly = d["fly_25d"]

        # Approximate SABR beta=1 calibration from market quotes
        # ATM vol → alpha; RR → rho; Butterfly → nu
        alpha = atm
        rho = -rr / (2 * 0.66)  # Simplified mapping
        nu = math.sqrt(2 * fly / T) if T > 0 else 0.2
        beta = 1.0  # FX convention: log-normal backbone

        strikes = [
            round(F * math.exp(-0.66 * atm * math.sqrt(T)), 5),  # 25Δ put
            round(F * math.exp(-0.25 * atm * math.sqrt(T)), 5),
            round(F, 5),  # ATM
            round(F * math.exp(+0.25 * atm * math.sqrt(T)), 5),
            round(F * math.exp(+0.66 * atm * math.sqrt(T)), 5),  # 25Δ call
        ]

        smile = []
        for K in strikes:
            # Hagan et al. SABR formula (simplified approximation)
            if abs(F - K) < 1e-10:
                vol = alpha / (F ** (1 - beta))
            else:
                log_fk = math.log(F / K)
                fk_mid = (F * K) ** ((1 - beta) / 2)
                z = (nu / alpha) * fk_mid * log_fk
                chi = (
                    math.log((math.sqrt(1 - 2 * rho * z + z**2) + z - rho) / (1 - rho))
                    if abs(z) > 1e-10
                    else 1.0
                )
                vol = alpha / fk_mid * (z / chi if abs(chi) > 1e-10 else 1.0)

            smile.append(
                {
                    "strike": K,
                    "moneyness": round(math.log(K / F) / (atm * math.sqrt(T)), 3),
                    "implied_vol": round(max(vol, 0.001), 5),
                }
            )

        return Response(
            {
                "pair": d["pair"].upper(),
                "forward": F,
                "tenor_days": d["tenor_days"],
                "parameters": {
                    "alpha": round(alpha, 5),
                    "beta": beta,
                    "rho": round(rho, 4),
                    "nu": round(nu, 4),
                },
                "smile": smile,
            }
        )


class StrategyBuilderView(APIView):
    """POST /api/v1/analytics/strategy-builder — Multi-leg FX option strategy."""

    @extend_schema(tags=["analytics"], summary="Multi-leg FX options strategy builder")
    def post(self, request):
        ser = StrategyBuilderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        pair = d["pair"].upper()
        spot = d.get("spot") or get_spot_rate(pair)
        base = pair[:3]
        quote = pair[3:]
        r_b = d.get("base_rate") or INTEREST_RATES.get(base, 0.03)
        r_q = d.get("quote_rate") or INTEREST_RATES.get(quote, 0.05)
        sigma = d["volatility"]

        legs_result = []
        total_premium = 0.0
        net_delta = 0.0
        net_gamma = 0.0
        net_vega = 0.0
        net_theta = 0.0

        for leg in d["legs"]:
            req = OptionRequest(
                base=base,
                quote=quote,
                spot=spot,
                strike=leg["strike"],
                tenor_days=leg["tenor_days"],
                volatility=sigma,
                base_rate=r_b,
                quote_rate=r_q,
                option_type=leg["option_type"],
                notional=leg["notional"],
            )
            result = garman_kohlhagen(req)
            sign = 1 if leg["direction"] == "long" else -1

            total_premium += sign * result.price * leg["notional"]
            net_delta += sign * result.delta * leg["notional"]
            net_gamma += sign * result.gamma * leg["notional"]
            net_vega += sign * result.vega * leg["notional"]
            net_theta += sign * result.theta * leg["notional"]

            legs_result.append(
                {
                    "option_type": leg["option_type"],
                    "direction": leg["direction"],
                    "strike": leg["strike"],
                    "tenor_days": leg["tenor_days"],
                    "notional": leg["notional"],
                    "premium": round(result.price * leg["notional"], 2),
                    "delta": round(result.delta, 5),
                    "gamma": round(result.gamma, 8),
                    "vega": round(result.vega, 6),
                    "theta": round(result.theta, 6),
                }
            )

        # Identify strategy type
        strategy_name = _classify_strategy(d["legs"])

        # Breakeven analysis across spot range
        spot_range = [round(spot * (1 + i * 0.01), 5) for i in range(-10, 11)]
        payoff_at_expiry = []
        for s in spot_range:
            pnl = 0.0
            for i, leg in enumerate(d["legs"]):
                sign = 1 if leg["direction"] == "long" else -1
                if leg["option_type"] == "call":
                    intrinsic = max(0.0, s - leg["strike"])
                else:
                    intrinsic = max(0.0, leg["strike"] - s)
                pnl += sign * (intrinsic * leg["notional"] - legs_result[i]["premium"])
            payoff_at_expiry.append({"spot": s, "pnl": round(pnl, 2)})

        return Response(
            {
                "pair": pair,
                "spot": round(spot, 5),
                "strategy_name": strategy_name,
                "legs": legs_result,
                "total_premium": round(total_premium, 2),
                "net_greeks": {
                    "delta": round(net_delta, 2),
                    "gamma": round(net_gamma, 6),
                    "vega": round(net_vega, 4),
                    "theta": round(net_theta, 4),
                },
                "payoff_at_expiry": payoff_at_expiry,
            }
        )


def _classify_strategy(legs: list[dict]) -> str:
    """Heuristically classify a multi-leg strategy by its structure."""
    n = len(legs)
    types = [l["option_type"] for l in legs]
    dirs = [l["direction"] for l in legs]

    if n == 1:
        return f"Vanilla {dirs[0].title()} {types[0].title()}"
    if n == 2:
        if types[0] != types[1] and set(dirs) == {"long"}:
            return (
                "Long Strangle"
                if legs[0]["strike"] != legs[1]["strike"]
                else "Long Straddle"
            )
        if types[0] != types[1] and set(dirs) == {"short"}:
            return (
                "Short Strangle"
                if legs[0]["strike"] != legs[1]["strike"]
                else "Short Straddle"
            )
        if types.count("call") == 2:
            return "Bull Call Spread" if "long" in dirs else "Bear Call Spread"
        if types.count("put") == 2:
            return "Bear Put Spread" if "long" in dirs else "Bull Put Spread"
    if n == 3 and types.count("call") == 3:
        return "Call Butterfly"
    if n == 3 and types.count("put") == 3:
        return "Put Butterfly"
    if n == 4:
        return "Iron Condor" if len(set(types)) == 2 else "Box Spread"
    return f"Custom {n}-Leg Strategy"


class FXFixingRateView(APIView):
    """GET /api/v1/analytics/fixing-rates — WM/Reuters-style FX fixing rates."""

    @extend_schema(tags=["analytics"], summary="WM/R-style FX fixing rates")
    def get(self, request):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        fixing_time = "16:00 London"

        fixings = []
        for pair, spot in FALLBACK_RATES.items():
            if len(pair) != 6:
                continue
            # Simulate fixing rate with small variation from mid
            import random

            random.seed(int(now.strftime("%Y%m%d")) + hash(pair))
            fixing = round(spot * (1 + random.gauss(0, 0.0001)), 5)
            fixings.append(
                {
                    "pair": pair,
                    "fixing_rate": fixing,
                    "mid_rate": round(spot, 5),
                    "deviation_pips": round((fixing - spot) / 0.0001, 2),
                    "fixing_time": fixing_time,
                    "date": now.strftime("%Y-%m-%d"),
                }
            )

        return Response({"fixings": fixings, "fixing_time": fixing_time})
