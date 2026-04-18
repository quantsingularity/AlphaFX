from apps.analytics import views
from django.urls import path

urlpatterns = [
    path(
        "position-size/",
        views.PositionSizeView.as_view(),
        name="analytics-position-size",
    ),
    path("risk-reward/", views.RiskRewardView.as_view(), name="analytics-risk-reward"),
    path("pip-value/", views.PipValueView.as_view(), name="analytics-pip-value"),
    path("swap-rates/", views.SwapRatesView.as_view(), name="analytics-swap-rates"),
    path("purchasing-power-parity/", views.PPPView.as_view(), name="analytics-ppp"),
    path("sabr-smile/", views.SABRSmileView.as_view(), name="analytics-sabr"),
    path(
        "strategy-builder/",
        views.StrategyBuilderView.as_view(),
        name="analytics-strategy",
    ),
    path("fixing-rates/", views.FXFixingRateView.as_view(), name="analytics-fixing"),
]
