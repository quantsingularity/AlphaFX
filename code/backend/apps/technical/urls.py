from apps.technical import views
from django.urls import path

urlpatterns = [
    path("", views.TechnicalScanView.as_view(), name="technical-scan"),
    path(
        "correlation/",
        views.CorrelationMatrixView.as_view(),
        name="technical-correlation",
    ),
    path(
        "<str:pair>/", views.TechnicalAnalysisView.as_view(), name="technical-analysis"
    ),
    path(
        "<str:pair>/support-resistance/",
        views.SupportResistanceView.as_view(),
        name="technical-sr",
    ),
    path(
        "<str:pair>/fibonacci/",
        views.FibonacciView.as_view(),
        name="technical-fibonacci",
    ),
    path(
        "<str:pair>/volatility/",
        views.VolatilityAnalysisView.as_view(),
        name="technical-volatility",
    ),
]
