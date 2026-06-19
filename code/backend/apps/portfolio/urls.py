from apps.portfolio import views
from django.urls import path

urlpatterns = [
    # Non-parameterized routes must appear before <str:pid>/ or they get swallowed.
    path("", views.PortfolioListCreateView.as_view(), name="portfolio-list"),
    # Price alerts (global -- not scoped to a single portfolio)
    path("alerts/", views.PriceAlertListCreateView.as_view(), name="alerts-list"),
    path(
        "alerts/<str:alert_id>/",
        views.PriceAlertDetailView.as_view(),
        name="alerts-detail",
    ),
    # Per-portfolio routes
    path("<str:pid>/", views.PortfolioDetailView.as_view(), name="portfolio-detail"),
    path(
        "<str:pid>/positions/",
        views.PositionListCreateView.as_view(),
        name="position-list",
    ),
    path(
        "<str:pid>/positions/<str:pos_id>/",
        views.PositionDetailView.as_view(),
        name="position-detail",
    ),
    path("<str:pid>/risk/", views.PortfolioRiskView.as_view(), name="portfolio-risk"),
    path(
        "<str:pid>/scenarios/",
        views.PortfolioScenariosView.as_view(),
        name="portfolio-scenarios",
    ),
    path("<str:pid>/history/", views.TradeHistoryView.as_view(), name="trade-history"),
    path(
        "<str:pid>/performance/",
        views.PerformanceView.as_view(),
        name="portfolio-performance",
    ),
]
