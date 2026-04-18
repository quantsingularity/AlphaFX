"""
Portfolio app models.
Full persistent storage replacing the original in-memory dict store.
"""

import uuid

from django.db import models


class Portfolio(models.Model):
    """FX trading portfolio."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    base_currency = models.CharField(max_length=3, default="USD")
    initial_balance = models.DecimalField(
        max_digits=18, decimal_places=2, default=100_000
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.base_currency})"

    @property
    def id_str(self):
        return str(self.id)


class Position(models.Model):
    """Individual FX position within a portfolio."""

    SIDE_CHOICES = [("buy", "Buy"), ("sell", "Sell")]
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="positions"
    )
    pair = models.CharField(max_length=6)
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    notional = models.DecimalField(max_digits=18, decimal_places=2)
    entry_rate = models.DecimalField(max_digits=12, decimal_places=6)
    stop_loss = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    take_profit = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    leverage = models.DecimalField(max_digits=6, decimal_places=2, default=1.0)
    status = models.CharField(max_length=6, choices=STATUS_CHOICES, default="open")
    close_rate = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    realized_pnl = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(blank=True, null=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self):
        return f"{self.side.upper()} {self.pair} x{self.notional}"

    @property
    def id_str(self):
        return str(self.id)


class PriceAlert(models.Model):
    """Price alert for a currency pair."""

    CONDITION_CHOICES = [
        ("above", "Price Above"),
        ("below", "Price Below"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pair = models.CharField(max_length=6)
    target_price = models.DecimalField(max_digits=12, decimal_places=6)
    condition = models.CharField(max_length=5, choices=CONDITION_CHOICES)
    triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.pair} {self.condition} {self.target_price}"


class TradeHistory(models.Model):
    """Closed trade record for performance tracking."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="trade_history"
    )
    pair = models.CharField(max_length=6)
    side = models.CharField(max_length=4)
    notional = models.DecimalField(max_digits=18, decimal_places=2)
    entry_rate = models.DecimalField(max_digits=12, decimal_places=6)
    close_rate = models.DecimalField(max_digits=12, decimal_places=6)
    realized_pnl = models.DecimalField(max_digits=18, decimal_places=2)
    pnl_pct = models.DecimalField(max_digits=8, decimal_places=4)
    leverage = models.DecimalField(max_digits=6, decimal_places=2, default=1.0)
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(auto_now_add=True)
    duration_hours = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ["-closed_at"]
