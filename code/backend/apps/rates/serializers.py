from rest_framework import serializers


class SpotRateRequestSerializer(serializers.Serializer):
    pairs = serializers.ListField(
        child=serializers.CharField(max_length=6),
        min_length=1,
        max_length=20,
    )


class ForwardRateRequestSerializer(serializers.Serializer):
    base = serializers.CharField(max_length=3)
    quote = serializers.CharField(max_length=3)
    tenor_days = serializers.IntegerField(min_value=1, max_value=3650)
    base_rate = serializers.FloatField(required=False, allow_null=True)
    quote_rate = serializers.FloatField(required=False, allow_null=True)


class CrossRateRequestSerializer(serializers.Serializer):
    base = serializers.CharField(max_length=3)
    quote = serializers.CharField(max_length=3)
    via = serializers.CharField(max_length=3, default="USD")


class FXOptionRequestSerializer(serializers.Serializer):
    OPTION_TYPES = [("call", "Call"), ("put", "Put")]

    base = serializers.CharField(max_length=3)
    quote = serializers.CharField(max_length=3)
    spot = serializers.FloatField(min_value=0.0001)
    strike = serializers.FloatField(min_value=0.0001)
    tenor_days = serializers.IntegerField(min_value=1, max_value=3650)
    volatility = serializers.FloatField(min_value=0.0001, max_value=5.0)
    base_rate = serializers.FloatField(min_value=-0.1, max_value=0.5)
    quote_rate = serializers.FloatField(min_value=-0.1, max_value=0.5)
    option_type = serializers.ChoiceField(choices=OPTION_TYPES, default="call")
    notional = serializers.FloatField(min_value=1.0, default=1_000_000)
