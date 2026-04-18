from apps.rates import views
from django.urls import path

urlpatterns = [
    path("", views.MajorPairsView.as_view(), name="rates-list"),
    path("all-pairs/", views.AllPairsView.as_view(), name="rates-all-pairs"),
    path("spot/", views.SpotRateBatchView.as_view(), name="rates-spot-batch"),
    path("spot/<str:pair>/", views.SpotRateView.as_view(), name="rates-spot"),
    path("forward/", views.ForwardRateView.as_view(), name="rates-forward"),
    path("cross/", views.CrossRateView.as_view(), name="rates-cross"),
    path("option/", views.FXOptionView.as_view(), name="rates-option"),
    path(
        "option/vol-surface/<str:pair>/",
        views.VolatilitySurfaceView.as_view(),
        name="rates-vol-surface",
    ),
    path(
        "option/risk-reversal/<str:pair>/",
        views.RiskReversalView.as_view(),
        name="rates-risk-reversal",
    ),
    path("carry/", views.CarryScreenView.as_view(), name="rates-carry"),
    path("interest-rates/", views.InterestRatesView.as_view(), name="rates-interest"),
    path("calendar/", views.EconomicCalendarView.as_view(), name="rates-calendar"),
    path("pip-value/<str:pair>/", views.PipValueView.as_view(), name="rates-pip-value"),
]
