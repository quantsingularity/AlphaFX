"""
Portfolio API views: portfolio CRUD, position management, risk analytics,
scenario analysis, price alerts, trade history, performance metrics.
"""

from datetime import datetime, timezone

from apps.core.pricing import get_spot_rate, pip_value
from apps.core.risk import (
    herfindahl_index,
    net_currency_exposure,
    portfolio_var,
    position_pnl,
    run_fx_scenarios,
)
from apps.portfolio.models import Portfolio, Position, PriceAlert, TradeHistory
from apps.portfolio.serializers import (
    ClosePositionSerializer,
    PortfolioSerializer,
    PositionCreateSerializer,
    PriceAlertSerializer,
    TradeHistorySerializer,
)
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _pos_to_dict(pos: Position) -> dict:
    return {
        "id": str(pos.id),
        "portfolio_id": str(pos.portfolio_id),
        "pair": pos.pair,
        "side": pos.side,
        "notional": float(pos.notional),
        "entry_rate": float(pos.entry_rate),
        "stop_loss": float(pos.stop_loss) if pos.stop_loss else None,
        "take_profit": float(pos.take_profit) if pos.take_profit else None,
        "leverage": float(pos.leverage),
        "status": pos.status,
    }


def _enrich_position(pos: Position) -> dict:
    """Add live P&L metrics to a position dict."""
    d = _pos_to_dict(pos)
    current_rate = get_spot_rate(pos.pair)
    pnl = position_pnl(
        pos.pair, pos.side, float(pos.notional), float(pos.entry_rate), current_rate
    )
    pnl_pct = pnl / float(pos.notional) * 100
    pv = pip_value(pos.pair, float(pos.notional), current_rate)
    margin = float(pos.notional) / float(pos.leverage)

    # Check SL/TP
    sl_distance_pips = None
    tp_distance_pips = None
    from apps.core.pricing import pip_size

    ps = pip_size(pos.pair)
    if pos.stop_loss:
        sl_distance_pips = round(abs(current_rate - float(pos.stop_loss)) / ps, 1)
    if pos.take_profit:
        tp_distance_pips = round(abs(float(pos.take_profit) - current_rate) / ps, 1)

    return {
        **d,
        "current_rate": round(current_rate, 5),
        "unrealized_pnl": round(pnl, 2),
        "unrealized_pnl_pct": round(pnl_pct, 4),
        "pip_value": round(pv, 4),
        "margin_used": round(margin, 2),
        "sl_distance_pips": sl_distance_pips,
        "tp_distance_pips": tp_distance_pips,
        "opened_at": pos.opened_at.isoformat(),
    }


# ─── Portfolio CRUD ────────────────────────────────────────────────────────────


class PortfolioListCreateView(APIView):

    @extend_schema(tags=["portfolio"], summary="List all portfolios")
    def get(self, request):
        portfolios = Portfolio.objects.all()
        result = []
        for p in portfolios:
            positions = list(p.positions.filter(status="open"))
            [_pos_to_dict(pos) for pos in positions]
            total_pnl = sum(
                position_pnl(
                    pos.pair,
                    pos.side,
                    float(pos.notional),
                    float(pos.entry_rate),
                    get_spot_rate(pos.pair),
                )
                for pos in positions
            )
            equity = float(p.initial_balance) + total_pnl
            used_margin = sum(
                float(pos.notional) / float(pos.leverage) for pos in positions
            )
            result.append(
                {
                    "id": str(p.id),
                    "name": p.name,
                    "base_currency": p.base_currency,
                    "initial_balance": float(p.initial_balance),
                    "description": p.description,
                    "created_at": p.created_at.isoformat(),
                    "open_positions": len(positions),
                    "total_pnl": round(total_pnl, 2),
                    "equity": round(equity, 2),
                    "used_margin": round(used_margin, 2),
                    "free_margin": round(equity - used_margin, 2),
                }
            )
        return Response(result)

    @extend_schema(tags=["portfolio"], summary="Create portfolio")
    def post(self, request):
        ser = PortfolioSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        p = Portfolio.objects.create(
            **{
                k: v
                for k, v in ser.validated_data.items()
                if k
                not in (
                    "open_positions",
                    "total_pnl",
                    "equity",
                    "used_margin",
                    "free_margin",
                )
            }
        )
        return Response(
            {
                "id": str(p.id),
                "name": p.name,
                "base_currency": p.base_currency,
                "initial_balance": float(p.initial_balance),
                "description": p.description,
                "created_at": p.created_at.isoformat(),
                "open_positions": 0,
            },
            status=status.HTTP_201_CREATED,
        )


class PortfolioDetailView(APIView):

    def _get_portfolio(self, pid):
        try:
            return Portfolio.objects.get(pk=pid)
        except (Portfolio.DoesNotExist, Exception):
            raise NotFound("Portfolio not found.")

    @extend_schema(tags=["portfolio"], summary="Get portfolio detail")
    def get(self, request, pid):
        p = self._get_portfolio(pid)
        positions = list(p.positions.filter(status="open"))
        total_pnl = sum(
            position_pnl(
                pos.pair,
                pos.side,
                float(pos.notional),
                float(pos.entry_rate),
                get_spot_rate(pos.pair),
            )
            for pos in positions
        )
        equity = float(p.initial_balance) + total_pnl
        used_margin = sum(
            float(pos.notional) / float(pos.leverage) for pos in positions
        )
        return Response(
            {
                "id": str(p.id),
                "name": p.name,
                "base_currency": p.base_currency,
                "initial_balance": float(p.initial_balance),
                "description": p.description,
                "created_at": p.created_at.isoformat(),
                "open_positions": len(positions),
                "total_pnl": round(total_pnl, 2),
                "equity": round(equity, 2),
                "used_margin": round(used_margin, 2),
                "free_margin": round(equity - used_margin, 2),
                "margin_level_pct": (
                    round(equity / used_margin * 100, 2) if used_margin > 0 else None
                ),
            }
        )

    @extend_schema(tags=["portfolio"], summary="Update portfolio")
    def patch(self, request, pid):
        p = self._get_portfolio(pid)
        for field in ("name", "description"):
            if field in request.data:
                setattr(p, field, request.data[field])
        p.save()
        return Response({"id": str(p.id), "name": p.name, "description": p.description})

    @extend_schema(tags=["portfolio"], summary="Delete portfolio")
    def delete(self, request, pid):
        p = self._get_portfolio(pid)
        p.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Position management ───────────────────────────────────────────────────────


class PositionListCreateView(APIView):

    def _get_portfolio(self, pid):
        try:
            return Portfolio.objects.get(pk=pid)
        except (Portfolio.DoesNotExist, Exception):
            raise NotFound("Portfolio not found.")

    @extend_schema(tags=["portfolio"], summary="List open positions")
    def get(self, request, pid):
        self._get_portfolio(pid)
        positions = Position.objects.filter(portfolio_id=pid, status="open")
        enriched = [_enrich_position(pos) for pos in positions]
        total_pnl = sum(p["unrealized_pnl"] for p in enriched)
        return Response(
            {
                "positions": enriched,
                "count": len(enriched),
                "total_pnl": round(total_pnl, 2),
            }
        )

    @extend_schema(tags=["portfolio"], summary="Open new position")
    def post(self, request, pid):
        portfolio = self._get_portfolio(pid)
        ser = PositionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        pos = Position.objects.create(
            portfolio=portfolio,
            pair=d["pair"],
            side=d["side"],
            notional=d["notional"],
            entry_rate=d["entry_rate"],
            stop_loss=d.get("stop_loss"),
            take_profit=d.get("take_profit"),
            leverage=d.get("leverage", 1.0),
            notes=d.get("notes"),
            status="open",
        )
        return Response(_enrich_position(pos), status=status.HTTP_201_CREATED)


class PositionDetailView(APIView):

    def _get_position(self, pid, pos_id):
        try:
            return Position.objects.get(pk=pos_id, portfolio_id=pid)
        except (Position.DoesNotExist, Exception):
            raise NotFound("Position not found.")

    @extend_schema(tags=["portfolio"], summary="Get position detail")
    def get(self, request, pid, pos_id):
        pos = self._get_position(pid, pos_id)
        return Response(_enrich_position(pos))

    @extend_schema(tags=["portfolio"], summary="Close a position")
    def delete(self, request, pid, pos_id):
        pos = self._get_position(pid, pos_id)

        ser = ClosePositionSerializer(data=request.data)
        if ser.is_valid():
            close_rate = ser.validated_data["close_rate"]
        else:
            close_rate = get_spot_rate(pos.pair)

        realized = position_pnl(
            pos.pair,
            pos.side,
            float(pos.notional),
            float(pos.entry_rate),
            close_rate,
        )
        pnl_pct = realized / float(pos.notional) * 100

        # Record in history
        duration = (datetime.now(timezone.utc) - pos.opened_at).total_seconds() / 3600
        TradeHistory.objects.create(
            portfolio=pos.portfolio,
            pair=pos.pair,
            side=pos.side,
            notional=pos.notional,
            entry_rate=pos.entry_rate,
            close_rate=close_rate,
            realized_pnl=realized,
            pnl_pct=pnl_pct,
            leverage=pos.leverage,
            opened_at=pos.opened_at,
            duration_hours=round(duration, 2),
        )

        pos.status = "closed"
        pos.close_rate = close_rate
        pos.realized_pnl = realized
        pos.closed_at = datetime.now(timezone.utc)
        pos.save()

        return Response(
            {
                "closed": True,
                "realized_pnl": round(realized, 2),
                "pnl_pct": round(pnl_pct, 4),
                "close_rate": close_rate,
            }
        )


# ─── Risk analytics ────────────────────────────────────────────────────────────


class PortfolioRiskView(APIView):

    @extend_schema(tags=["risk"], summary="Portfolio VaR and exposure metrics")
    def get(self, request, pid):
        try:
            p = Portfolio.objects.get(pk=pid)
        except (Portfolio.DoesNotExist, Exception):
            raise NotFound("Portfolio not found.")

        confidence = float(request.query_params.get("confidence", 0.99))
        positions = list(p.positions.filter(status="open"))
        pos_dicts = [_pos_to_dict(pos) for pos in positions]

        var_metrics = portfolio_var(pos_dicts, confidence_level=confidence)
        exposure = net_currency_exposure(pos_dicts)
        hhi = herfindahl_index(pos_dicts)
        total_notional = sum(float(pos.notional) for pos in positions)
        largest_pct = (
            max(
                (float(pos.notional) / total_notional for pos in positions), default=0.0
            )
            * 100
        )

        return Response(
            {
                "portfolio_id": pid,
                "total_notional": total_notional,
                "net_exposure_by_currency": exposure,
                "largest_position_pct": round(largest_pct, 2),
                "concentration_hhi": round(hhi, 4),
                **var_metrics,
            }
        )


class PortfolioScenariosView(APIView):

    @extend_schema(tags=["risk"], summary="Run macro scenario analysis")
    def post(self, request, pid):
        try:
            p = Portfolio.objects.get(pk=pid)
        except (Portfolio.DoesNotExist, Exception):
            raise NotFound("Portfolio not found.")

        positions = list(p.positions.filter(status="open"))
        pos_dicts = [_pos_to_dict(pos) for pos in positions]
        total_pnl = sum(
            position_pnl(
                pos.pair,
                pos.side,
                float(pos.notional),
                float(pos.entry_rate),
                get_spot_rate(pos.pair),
            )
            for pos in positions
        )
        equity = float(p.initial_balance) + total_pnl
        results = run_fx_scenarios(pos_dicts, equity)

        return Response(
            {
                "portfolio_id": pid,
                "base_equity": round(equity, 2),
                "scenarios": results,
            }
        )


# ─── Price alerts ──────────────────────────────────────────────────────────────


class PriceAlertListCreateView(APIView):

    @extend_schema(tags=["alerts"], summary="List price alerts")
    def get(self, request):
        alerts = PriceAlert.objects.all()
        ser = PriceAlertSerializer(alerts, many=True)
        return Response({"alerts": ser.data, "count": len(ser.data)})

    @extend_schema(tags=["alerts"], summary="Create price alert")
    def post(self, request):
        ser = PriceAlertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        alert = PriceAlert.objects.create(**ser.validated_data)
        return Response(
            PriceAlertSerializer(alert).data, status=status.HTTP_201_CREATED
        )


class PriceAlertDetailView(APIView):

    def _get_alert(self, alert_id):
        try:
            return PriceAlert.objects.get(pk=alert_id)
        except (PriceAlert.DoesNotExist, Exception):
            raise NotFound("Alert not found.")

    @extend_schema(tags=["alerts"], summary="Delete price alert")
    def delete(self, request, alert_id):
        alert = self._get_alert(alert_id)
        alert.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=["alerts"], summary="Check if alert is triggered")
    def get(self, request, alert_id):
        alert = self._get_alert(alert_id)
        current_rate = get_spot_rate(alert.pair)
        triggered = (
            alert.condition == "above" and current_rate >= float(alert.target_price)
        ) or (alert.condition == "below" and current_rate <= float(alert.target_price))
        if triggered and not alert.triggered:
            alert.triggered = True
            alert.triggered_at = datetime.now(timezone.utc)
            alert.save()
        return Response(PriceAlertSerializer(alert).data)


# ─── Trade history & performance ───────────────────────────────────────────────


class TradeHistoryView(APIView):

    @extend_schema(tags=["portfolio"], summary="Trade history for a portfolio")
    def get(self, request, pid):
        try:
            Portfolio.objects.get(pk=pid)
        except (Portfolio.DoesNotExist, Exception):
            raise NotFound("Portfolio not found.")

        trades = TradeHistory.objects.filter(portfolio_id=pid).order_by("-closed_at")
        ser = TradeHistorySerializer(trades, many=True)
        return Response({"trades": ser.data, "count": len(ser.data)})


class PerformanceView(APIView):

    @extend_schema(tags=["portfolio"], summary="Portfolio performance statistics")
    def get(self, request, pid):
        try:
            p = Portfolio.objects.get(pk=pid)
        except (Portfolio.DoesNotExist, Exception):
            raise NotFound("Portfolio not found.")

        trades = list(TradeHistory.objects.filter(portfolio_id=pid))
        if not trades:
            return Response(
                {
                    "portfolio_id": pid,
                    "total_trades": 0,
                    "win_rate_pct": 0.0,
                    "total_realized_pnl": 0.0,
                    "avg_pnl_per_trade": 0.0,
                    "best_trade": None,
                    "worst_trade": None,
                    "profit_factor": None,
                }
            )

        pnls = [float(t.realized_pnl) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        win_rate = len(wins) / len(pnls) * 100 if pnls else 0
        profit_factor = abs(sum(wins) / sum(losses)) if losses else None

        return Response(
            {
                "portfolio_id": pid,
                "total_trades": len(trades),
                "winning_trades": len(wins),
                "losing_trades": len(losses),
                "win_rate_pct": round(win_rate, 2),
                "total_realized_pnl": round(sum(pnls), 2),
                "avg_pnl_per_trade": round(sum(pnls) / len(pnls), 2),
                "best_trade_pnl": round(max(pnls), 2),
                "worst_trade_pnl": round(min(pnls), 2),
                "profit_factor": round(profit_factor, 3) if profit_factor else None,
                "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
                "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
            }
        )
