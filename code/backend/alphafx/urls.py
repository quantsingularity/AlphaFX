"""AlphaFX URL Configuration"""

from apps.core.views import HealthView, RootView
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RootView.as_view(), name="root"),
    path("health", HealthView.as_view(), name="health"),
    # API v1 -- auth
    path("api/v1/auth/", include("apps.auth_api.urls")),
    # API v1 -- domain
    path("api/v1/rates/", include("apps.rates.urls")),
    path("api/v1/portfolios/", include("apps.portfolio.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/technical/", include("apps.technical.urls")),
    # API Schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
