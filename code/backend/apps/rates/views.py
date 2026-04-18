"""
Rates API views: spot, forward, cross-rate, options, carry, calendar, pip value.
"""

import asyncio

from apps.core.data_feed import build_pair_quotes, economic_calendar
from apps.core.pricing import (
    ALL_PAIRS,
    FALLBACK_RATES,
    INTEREST_RATES,
    MAJOR_PAIRS,
    OptionRequest,
    carry_opportunities,
    compute_cross_rate,
    compute_forward_rate,
    garman_kohlhagen,
    get_spot_rate,
    implied_volatility_surface,
    pip_size,
    pip_value,
    spread_pips,
    volatility_risk_reversal,
)
from apps.rates.serializers import (
    CrossRateRequestSerializer,
    ForwardRateRequestSerializer,
    FXOptionRequestSerializer,
    SpotRateRequestSerializer,
)
from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView


def _run_async(coro):
    """Run a coroutine from a sync Django view without deprecation warnings."""
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


class MajorPairsView(APIView):
    """GET /api/v1/rates/ — All major pair live quotes."""

    @extend_schema(tags=["rates"], summary="List major pair quotes")
    def get(self, request):
        cache_key = "major_pairs_quotes"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        quotes = _run_async(build_pair_quotes(MAJOR_PAIRS))
        result = {"pairs": quotes, "count": len(quotes)}
        cache.set(cache_key, result, timeout=10)
        return Response(result)


class SpotRateView(APIView):
    """GET /api/v1/rates/spot/{pair} — Single pair bid/ask/mid."""

    @extend_schema(tags=["rates"], summary="Get spot rate for a single pair")
    def get(self, request, pair):
        pair = pair.upper()
        if len(pair) != 6:
            raise ValidationError(
                f"Invalid pair format: {pair}. Expected 6-character code."
            )

        spot = get_spot_rate(pair)
        if spot == 1.0 and pair not in FALLBACK_RATES:
            raise NotFound(f"Pair {pair} not found.")

        sp = spread_pips(pair)
        ps = pip_size(pair)
        half = sp * ps / 2

        from datetime import datetime, timezone

        return Response(
            {
                "pair": pair,
                "base": pair[:3],
                "quote": pair[3:],
                "bid": round(spot - half, 5),
                "ask": round(spot + half, 5),
                "mid": round(spot, 5),
                "spread_pips": sp,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


class SpotRateBatchView(APIView):
    """POST /api/v1/rates/spot — Batch spot quotes."""

    @extend_schema(tags=["rates"], summary="Batch spot rates for multiple pairs")
    def post(self, request):
        ser = SpotRateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        quotes = _run_async(build_pair_quotes(ser.validated_data["pairs"]))
        return Response({"quotes": quotes}, status=status.HTTP_200_OK)


class ForwardRateView(APIView):
    """POST /api/v1/rates/forward — Forward rate via CIP."""

    @extend_schema(tags=["rates"], summary="Calculate forward rate (CIP)")
    def post(self, request):
        ser = ForwardRateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        pair = f"{d['base'].upper()}{d['quote'].upper()}"
        spot = get_spot_rate(pair)
        r_base = d.get("base_rate") or INTEREST_RATES.get(d["base"].upper(), 0.03)
        r_quote = d.get("quote_rate") or INTEREST_RATES.get(d["quote"].upper(), 0.05)

        fwd, pts = compute_forward_rate(spot, r_base, r_quote, d["tenor_days"])

        return Response(
            {
                "base": d["base"].upper(),
                "quote": d["quote"].upper(),
                "spot": round(spot, 5),
                "forward_rate": round(fwd, 5),
                "forward_points": round(pts, 4),
                "tenor_days": d["tenor_days"],
                "base_rate": r_base,
                "quote_rate": r_quote,
                "annualized_swap_cost_bps": round((r_quote - r_base) * 10_000, 1),
            }
        )


class CrossRateView(APIView):
    """POST /api/v1/rates/cross — Cross-rate via USD triangulation."""

    @extend_schema(tags=["rates"], summary="Compute cross-rate via triangulation")
    def post(self, request):
        ser = CrossRateRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        rate = compute_cross_rate(d["base"], d["quote"], d.get("via", "USD"))
        return Response(
            {
                "base": d["base"].upper(),
                "quote": d["quote"].upper(),
                "via": d.get("via", "USD").upper(),
                "rate": round(rate, 5),
            }
        )


class FXOptionView(APIView):
    """POST /api/v1/rates/option — Garman-Kohlhagen option pricer."""

    @extend_schema(tags=["options"], summary="Price FX option (Garman-Kohlhagen)")
    def post(self, request):
        ser = FXOptionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        req = OptionRequest(
            base=d["base"],
            quote=d["quote"],
            spot=d["spot"],
            strike=d["strike"],
            tenor_days=d["tenor_days"],
            volatility=d["volatility"],
            base_rate=d["base_rate"],
            quote_rate=d["quote_rate"],
            option_type=d["option_type"],
            notional=d["notional"],
        )
        result = garman_kohlhagen(req)

        return Response(
            {
                "option_type": result.option_type,
                "spot": round(result.spot, 5),
                "strike": round(result.strike, 5),
                "tenor_days": result.tenor_days,
                "volatility_pct": round(result.volatility_pct, 2),
                "price": round(result.price, 6),
                "price_pct": round(result.price_pct, 4),
                "notional_value": round(result.notional_value, 2),
                "greeks": {
                    "delta": round(result.delta, 5),
                    "gamma": round(result.gamma, 8),
                    "vega": round(result.vega, 6),
                    "theta": round(result.theta, 6),
                    "rho": round(result.rho, 6),
                },
                "intrinsic_value": round(result.intrinsic_value, 6),
                "time_value": round(result.time_value, 6),
                "breakeven": round(result.breakeven, 5),
            }
        )


class VolatilitySurfaceView(APIView):
    """GET /api/v1/rates/option/vol-surface/{pair}"""

    @extend_schema(tags=["options"], summary="Implied volatility surface")
    def get(self, request, pair):
        return Response(implied_volatility_surface(pair.upper()))


class RiskReversalView(APIView):
    """GET /api/v1/rates/option/risk-reversal/{pair}"""

    @extend_schema(tags=["options"], summary="25-delta risk reversal and butterfly")
    def get(self, request, pair):
        return Response(volatility_risk_reversal(pair.upper()))


class CarryScreenView(APIView):
    """GET /api/v1/rates/carry — Carry trade opportunities."""

    @extend_schema(
        tags=["rates"],
        summary="Carry trade screener",
        parameters=[
            OpenApiParameter(
                "min_carry_bps", float, description="Minimum carry threshold"
            )
        ],
    )
    def get(self, request):
        min_bps = float(request.query_params.get("min_carry_bps", 0.0))
        opps = carry_opportunities(min_bps)
        return Response({"opportunities": opps, "count": len(opps)})


class InterestRatesView(APIView):
    """GET /api/v1/rates/interest-rates — Central bank policy rates."""

    @extend_schema(tags=["rates"], summary="Central bank interest rates")
    def get(self, request):
        return Response({"rates": INTEREST_RATES})


class EconomicCalendarView(APIView):
    """GET /api/v1/rates/calendar — Economic event calendar."""

    @extend_schema(tags=["rates"], summary="Economic calendar")
    def get(self, request):
        return Response({"events": economic_calendar()})


class PipValueView(APIView):
    """GET /api/v1/rates/pip-value/{pair}"""

    @extend_schema(
        tags=["rates"],
        summary="Pip value in USD",
        parameters=[
            OpenApiParameter("notional", float, description="Position notional")
        ],
    )
    def get(self, request, pair):
        pair = pair.upper()
        notional = float(request.query_params.get("notional", 100_000))
        spot = get_spot_rate(pair)
        pv = pip_value(pair, notional, spot)
        return Response(
            {
                "pair": pair,
                "notional": notional,
                "spot": round(spot, 5),
                "pip_value_usd": round(pv, 4),
            }
        )


class AllPairsView(APIView):
    """GET /api/v1/rates/all-pairs — Full pair list with rates."""

    @extend_schema(tags=["rates"], summary="All available pairs")
    def get(self, request):
        return Response(
            {
                "major_pairs": MAJOR_PAIRS,
                "all_pairs": ALL_PAIRS,
                "count": len(ALL_PAIRS),
            }
        )
