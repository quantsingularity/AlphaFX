import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Portfolio",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("base_currency", models.CharField(default="USD", max_length=3)),
                (
                    "initial_balance",
                    models.DecimalField(
                        decimal_places=2, default=100000, max_digits=18
                    ),
                ),
                ("description", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Position",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("pair", models.CharField(max_length=6)),
                (
                    "side",
                    models.CharField(
                        choices=[("buy", "Buy"), ("sell", "Sell")], max_length=4
                    ),
                ),
                ("notional", models.DecimalField(decimal_places=2, max_digits=18)),
                ("entry_rate", models.DecimalField(decimal_places=6, max_digits=12)),
                (
                    "stop_loss",
                    models.DecimalField(
                        blank=True, decimal_places=6, max_digits=12, null=True
                    ),
                ),
                (
                    "take_profit",
                    models.DecimalField(
                        blank=True, decimal_places=6, max_digits=12, null=True
                    ),
                ),
                (
                    "leverage",
                    models.DecimalField(decimal_places=2, default=1.0, max_digits=6),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("open", "Open"), ("closed", "Closed")],
                        default="open",
                        max_length=6,
                    ),
                ),
                (
                    "close_rate",
                    models.DecimalField(
                        blank=True, decimal_places=6, max_digits=12, null=True
                    ),
                ),
                (
                    "realized_pnl",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=18, null=True
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True)),
                ("opened_at", models.DateTimeField(auto_now_add=True)),
                ("closed_at", models.DateTimeField(null=True, blank=True)),
                (
                    "portfolio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="positions",
                        to="portfolio.portfolio",
                    ),
                ),
            ],
            options={"ordering": ["-opened_at"]},
        ),
        migrations.CreateModel(
            name="PriceAlert",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("pair", models.CharField(max_length=6)),
                ("target_price", models.DecimalField(decimal_places=6, max_digits=12)),
                (
                    "condition",
                    models.CharField(
                        choices=[("above", "Price Above"), ("below", "Price Below")],
                        max_length=5,
                    ),
                ),
                ("triggered", models.BooleanField(default=False)),
                ("triggered_at", models.DateTimeField(blank=True, null=True)),
                ("message", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="TradeHistory",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("pair", models.CharField(max_length=6)),
                ("side", models.CharField(max_length=4)),
                ("notional", models.DecimalField(decimal_places=2, max_digits=18)),
                ("entry_rate", models.DecimalField(decimal_places=6, max_digits=12)),
                ("close_rate", models.DecimalField(decimal_places=6, max_digits=12)),
                ("realized_pnl", models.DecimalField(decimal_places=2, max_digits=18)),
                ("pnl_pct", models.DecimalField(decimal_places=4, max_digits=8)),
                (
                    "leverage",
                    models.DecimalField(decimal_places=2, default=1.0, max_digits=6),
                ),
                ("opened_at", models.DateTimeField()),
                ("closed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "duration_hours",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "portfolio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trade_history",
                        to="portfolio.portfolio",
                    ),
                ),
            ],
            options={"ordering": ["-closed_at"]},
        ),
    ]
