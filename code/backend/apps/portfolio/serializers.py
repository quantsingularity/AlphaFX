from apps.portfolio.models import Portfolio, Position, PriceAlert, TradeHistory
from rest_framework import serializers


class PortfolioSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    open_positions = serializers.IntegerField(read_only=True, default=0)
    total_pnl = serializers.FloatField(read_only=True, default=0.0)
    equity = serializers.FloatField(read_only=True, default=None, allow_null=True)
    used_margin = serializers.FloatField(read_only=True, default=None, allow_null=True)
    free_margin = serializers.FloatField(read_only=True, default=None, allow_null=True)

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "name",
            "base_currency",
            "initial_balance",
            "description",
            "created_at",
            "open_positions",
            "total_pnl",
            "equity",
            "used_margin",
            "free_margin",
        ]
        read_only_fields = ["id", "created_at"]


class PositionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Position
        fields = [
            "id",
            "pair",
            "side",
            "notional",
            "entry_rate",
            "stop_loss",
            "take_profit",
            "leverage",
            "status",
            "close_rate",
            "realized_pnl",
            "notes",
            "opened_at",
        ]
        read_only_fields = ["id", "opened_at", "status", "close_rate", "realized_pnl"]


class PositionCreateSerializer(serializers.Serializer):
    pair = serializers.CharField(max_length=6)
    side = serializers.ChoiceField(choices=["buy", "sell"])
    notional = serializers.FloatField(min_value=1.0)
    entry_rate = serializers.FloatField(min_value=0.0001)
    stop_loss = serializers.FloatField(required=False, allow_null=True)
    take_profit = serializers.FloatField(required=False, allow_null=True)
    leverage = serializers.FloatField(min_value=1.0, max_value=500.0, default=1.0)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_pair(self, value):
        return value.upper()


class ClosePositionSerializer(serializers.Serializer):
    close_rate = serializers.FloatField(min_value=0.0001)
    notes = serializers.CharField(required=False, allow_blank=True)


class PriceAlertSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = PriceAlert
        fields = [
            "id",
            "pair",
            "target_price",
            "condition",
            "triggered",
            "triggered_at",
            "message",
            "created_at",
        ]
        read_only_fields = ["id", "triggered", "triggered_at", "created_at"]


class TradeHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeHistory
        fields = "__all__"
