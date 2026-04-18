"""
Technical Analysis API views:
- Full indicator suite (RSI, MACD, Bollinger, ATR, Stochastic, Williams %R,
  Ichimoku, VWAP, Pivot Points)
- Multi-pair signal scan
- Rolling correlation matrix
- Support & resistance levels (new)
- Fibonacci retracement (new)
"""

from apps.core.pricing import MAJOR_PAIRS
from apps.core.technical import (
    correlation_matrix,
    full_analysis,
    pivot_points,
    synthetic_ohlcv,
)
from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView


class TechnicalAnalysisView(APIView):
    """GET /api/v1/technical/{pair}/ — Full technical analysis for a pair."""

    @extend_schema(
        tags=["technical"],
        summary="Full technical analysis for a currency pair",
        parameters=[OpenApiParameter("n", int, description="Lookback bars (50–500)")],
    )
    def get(self, request, pair):
        pair = pair.upper()
        n = int(request.query_params.get("n", 252))
        n = max(50, min(500, n))

        cache_key = f"technical:{pair}:{n}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        result = full_analysis(pair, n)
        cache.set(cache_key, result, timeout=30)
        return Response(result)


class TechnicalScanView(APIView):
    """GET /api/v1/technical/ — Scan all major pairs for signals."""

    @extend_schema(
        tags=["technical"],
        summary="Signal scan across all major pairs",
        parameters=[OpenApiParameter("n", int, description="Lookback bars")],
    )
    def get(self, request):
        n = int(request.query_params.get("n", 100))
        n = max(50, min(252, n))

        cache_key = f"technical_scan:{n}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        results = []
        for pair in MAJOR_PAIRS:
            try:
                a = full_analysis(pair, n)
                results.append(
                    {
                        "pair": a["pair"],
                        "current_price": a["current_price"],
                        "change_pct": a["change_pct"],
                        "signal": a["signal"],
                        "bullish_count": a["bullish_count"],
                        "bearish_count": a["bearish_count"],
                        "rsi": a["indicators"]["rsi_14"],
                        "macd_hist": a["indicators"]["macd_hist"],
                        "stoch_k": a["indicators"]["stoch_k"],
                        "williams_r": a["indicators"]["williams_r"],
                        "annualized_vol_pct": a["annualized_volatility_pct"],
                        "pivot": a["pivot_points"]["pivot"],
                    }
                )
            except Exception:
                continue

        response = {"signals": results, "count": len(results)}
        cache.set(cache_key, response, timeout=30)
        return Response(response)


class CorrelationMatrixView(APIView):
    """GET /api/v1/technical/correlation/ — Rolling correlation matrix."""

    @extend_schema(
        tags=["technical"],
        summary="Rolling correlation matrix",
        parameters=[
            OpenApiParameter("pairs", str, description="Comma-separated pairs"),
            OpenApiParameter("n", int, description="Lookback days"),
        ],
    )
    def get(self, request):
        pairs_str = request.query_params.get(
            "pairs", "EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD"
        )
        pair_list = [p.strip().upper() for p in pairs_str.split(",") if p.strip()]

        if len(pair_list) < 2:
            raise ValidationError("Provide at least 2 pairs.")

        n = int(request.query_params.get("n", 60))
        n = max(20, min(252, n))

        cache_key = f"correlation:{'_'.join(sorted(pair_list))}:{n}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        result = correlation_matrix(pair_list, n)
        cache.set(cache_key, result, timeout=60)
        return Response(result)


class SupportResistanceView(APIView):
    """GET /api/v1/technical/{pair}/support-resistance/ — S/R levels."""

    @extend_schema(
        tags=["technical"],
        summary="Support and resistance levels",
        parameters=[OpenApiParameter("n", int, description="Lookback bars")],
    )
    def get(self, request, pair):
        pair = pair.upper()
        n = int(request.query_params.get("n", 100))
        n = max(50, min(252, n))

        df = synthetic_ohlcv(pair, n)
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # Identify swing highs and lows
        swing_highs = []
        swing_lows = []
        window = 5

        for i in range(window, len(df) - window):
            h = float(high.iloc[i])
            l = float(low.iloc[i])
            if h == float(high.iloc[i - window : i + window + 1].max()):
                swing_highs.append(
                    {"price": round(h, 5), "index": i, "date": str(df.index[i].date())}
                )
            if l == float(low.iloc[i - window : i + window + 1].min()):
                swing_lows.append(
                    {"price": round(l, 5), "index": i, "date": str(df.index[i].date())}
                )

        # Cluster nearby levels (within 0.3% of each other)
        def cluster(levels, tol_pct=0.003):
            if not levels:
                return []
            sorted_levels = sorted(levels, key=lambda x: x["price"])
            clusters = []
            group = [sorted_levels[0]]
            for lv in sorted_levels[1:]:
                if (lv["price"] - group[-1]["price"]) / group[-1]["price"] < tol_pct:
                    group.append(lv)
                else:
                    avg = sum(g["price"] for g in group) / len(group)
                    clusters.append(
                        {
                            "price": round(avg, 5),
                            "strength": len(group),
                            "last_date": group[-1]["date"],
                        }
                    )
                    group = [lv]
            if group:
                avg = sum(g["price"] for g in group) / len(group)
                clusters.append(
                    {
                        "price": round(avg, 5),
                        "strength": len(group),
                        "last_date": group[-1]["date"],
                    }
                )
            return sorted(clusters, key=lambda x: x["strength"], reverse=True)[:5]

        resistance = cluster(swing_highs)
        support = cluster(swing_lows)
        current = round(float(close.iloc[-1]), 5)

        return Response(
            {
                "pair": pair,
                "current_price": current,
                "resistance": resistance,
                "support": support,
                "pivot_points": pivot_points(
                    float(high.iloc[-1]), float(low.iloc[-1]), current
                ),
            }
        )


class FibonacciView(APIView):
    """GET /api/v1/technical/{pair}/fibonacci/ — Fibonacci retracement levels."""

    @extend_schema(
        tags=["technical"],
        summary="Fibonacci retracement and extension levels",
        parameters=[OpenApiParameter("n", int, description="Lookback bars for swing")],
    )
    def get(self, request, pair):
        pair = pair.upper()
        n = int(request.query_params.get("n", 100))
        n = max(50, min(252, n))

        df = synthetic_ohlcv(pair, n)
        high = float(df["high"].max())
        low = float(df["low"].min())
        diff = high - low

        fib_levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        fib_ext = [1.272, 1.414, 1.618, 2.0, 2.618]

        retracements = [
            {"level": lvl, "price": round(high - lvl * diff, 5)} for lvl in fib_levels
        ]
        extensions = [
            {"level": lvl, "price": round(high + (lvl - 1) * diff, 5)}
            for lvl in fib_ext
        ]

        current = round(float(df["close"].iloc[-1]), 5)
        # Find nearest fib level
        nearest = min(retracements, key=lambda x: abs(x["price"] - current))

        return Response(
            {
                "pair": pair,
                "current_price": current,
                "swing_high": round(high, 5),
                "swing_low": round(low, 5),
                "retracements": retracements,
                "extensions": extensions,
                "nearest_level": nearest,
            }
        )


class VolatilityAnalysisView(APIView):
    """GET /api/v1/technical/{pair}/volatility/ — Historical volatility term structure."""

    @extend_schema(
        tags=["technical"],
        summary="Historical volatility term structure",
    )
    def get(self, request, pair):
        pair = pair.upper()
        df = synthetic_ohlcv(pair, 252)
        ret = df["close"].pct_change().dropna()

        windows = [5, 10, 21, 42, 63, 126, 252]
        hv_term = []
        for w in windows:
            if len(ret) >= w:
                hv = float(ret.tail(w).std()) * (252**0.5) * 100
                hv_term.append({"window_days": w, "hv_pct": round(hv, 3)})

        # Volatility percentile (current 21d vs 252d history)
        hv21 = float(ret.tail(21).std()) * (252**0.5) * 100
        roll_21 = ret.rolling(21).std() * (252**0.5) * 100
        pct_rank = float((roll_21.dropna() < hv21 / 100).mean() * 100)

        return Response(
            {
                "pair": pair,
                "current_hv_21d_pct": round(hv21, 3),
                "hv_percentile_rank": round(pct_rank, 1),
                "term_structure": hv_term,
            }
        )
