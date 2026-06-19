from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView


class RootView(APIView):
    """API root / health check."""

    def get(self, request):
        return Response(
            {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "status": "operational",
                "docs": "/docs/",
                "redoc": "/redoc/",
            }
        )


class HealthView(APIView):
    """Detailed health check."""

    def get(self, request):
        from django.conf import settings as s
        from django.db import connection

        db_ok = True
        cache_ok = True

        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False

        try:
            import redis as redis_lib

            r = redis_lib.from_url(s.REDIS_URL)
            r.ping()
        except ImportError:
            # redis package not installed (e.g. minimal test environment)
            cache_ok = False
        except Exception:
            cache_ok = False

        status = "ok" if (db_ok and cache_ok) else "degraded"
        return Response(
            {
                "status": status,
                "version": s.APP_VERSION,
                "database": "ok" if db_ok else "error",
                "cache": "ok" if cache_ok else "error",
            }
        )
