from apps.portfolio.models import Portfolio, Position, PriceAlert, TradeHistory
from django.contrib import admin


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("name", "base_currency", "initial_balance", "created_at")
    search_fields = ("name",)
    list_filter = ("base_currency",)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = (
        "pair",
        "side",
        "notional",
        "entry_rate",
        "status",
        "portfolio",
        "opened_at",
    )
    list_filter = ("status", "side", "pair")
    search_fields = ("pair",)


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ("pair", "condition", "target_price", "triggered", "created_at")
    list_filter = ("triggered", "condition")


@admin.register(TradeHistory)
class TradeHistoryAdmin(admin.ModelAdmin):
    list_display = ("pair", "side", "notional", "realized_pnl", "pnl_pct", "closed_at")
    list_filter = ("side", "pair")
    ordering = ("-closed_at",)
