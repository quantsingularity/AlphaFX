"""
AlphaFX Django Settings
Institutional-grade FX analytics and trading intelligence platform.

Designed to work with or without django-environ / dj-database-url installed,
falling back to sensible defaults so tests always run with just:
  pip install -r requirements.txt
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Try django-environ; fall back to raw os.environ with defaults
# ---------------------------------------------------------------------------

try:
    import environ

    env = environ.Env(
        DEBUG=(bool, False),
        ALLOWED_HOSTS=(list, ["*"]),
        CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000", "http://localhost:5173"]),
        DATABASE_URL=(str, f"sqlite:///{BASE_DIR}/db.sqlite3"),
        REDIS_URL=(str, "redis://localhost:6379/0"),
        SECRET_KEY=(str, "django-insecure-alphafx-dev-key-change-in-production"),
        CACHE_TTL=(int, 60),
        RISK_FREE_RATE=(float, 0.05),
        EXCHANGERATE_API_KEY=(str, ""),
        ALPHA_VANTAGE_KEY=(str, ""),
    )
    _env_file = BASE_DIR / ".env"
    if _env_file.exists():
        environ.Env.read_env(_env_file)

    SECRET_KEY = env("SECRET_KEY")
    DEBUG = env("DEBUG")
    ALLOWED_HOSTS = env("ALLOWED_HOSTS")
    _DATABASE_URL = env("DATABASE_URL")
    REDIS_URL = env("REDIS_URL")
    CACHE_TTL = env("CACHE_TTL")
    RISK_FREE_RATE = env("RISK_FREE_RATE")
    EXCHANGERATE_API_KEY = env("EXCHANGERATE_API_KEY")
    ALPHA_VANTAGE_KEY = env("ALPHA_VANTAGE_KEY")
    CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

except ImportError:
    # django-environ not installed — read directly from os.environ
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "django-insecure-alphafx-dev-key-change-in-production"
    )
    DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")
    ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")
    _DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR}/db.sqlite3")
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL = int(os.environ.get("CACHE_TTL", "60"))
    RISK_FREE_RATE = float(os.environ.get("RISK_FREE_RATE", "0.05"))
    EXCHANGERATE_API_KEY = os.environ.get("EXCHANGERATE_API_KEY", "")
    ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
    CORS_ALLOWED_ORIGINS = os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")


APP_NAME = "AlphaFX"
APP_VERSION = "2.0.0"

# ---------------------------------------------------------------------------
# Installed apps
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "channels",
    # Internal apps
    "apps.core",
    "apps.auth_api",
    "apps.rates",
    "apps.portfolio",
    "apps.analytics",
    "apps.technical",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "alphafx.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "alphafx" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "alphafx.asgi.application"
WSGI_APPLICATION = "alphafx.wsgi.application"

# ---------------------------------------------------------------------------
# Database — try dj-database-url, fall back to plain sqlite config
# ---------------------------------------------------------------------------

try:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.config(
            default=_DATABASE_URL,
            conn_max_age=600,
        )
    }
except ImportError:
    # Minimal fallback: always use SQLite so tests work without PostgreSQL
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Cache — try django-redis, fall back to LocMemCache so tests work without Redis
# ---------------------------------------------------------------------------

try:
    import django_redis  # noqa: F401 — just checking it is importable

    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
            },
            "TIMEOUT": CACHE_TTL,
        }
    }
except ImportError:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# ---------------------------------------------------------------------------
# Channel layers — try channels-redis, fall back to InMemoryChannelLayer
# ---------------------------------------------------------------------------

try:
    import channels_redis  # noqa: F401

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
except ImportError:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/minute",
        "user": "1000/minute",
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG

# ---------------------------------------------------------------------------
# API Schema
# ---------------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "AlphaFX API",
    "DESCRIPTION": "Institutional-grade FX analytics and trading intelligence platform",
    "VERSION": APP_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "rates", "description": "Spot rates, forwards, cross-rates"},
        {"name": "options", "description": "Garman-Kohlhagen FX options pricing"},
        {"name": "portfolio", "description": "Portfolio and position management"},
        {"name": "risk", "description": "VaR, exposure, scenario analysis"},
        {"name": "technical", "description": "Technical indicators and signals"},
        {"name": "analytics", "description": "Position sizing, risk-reward, PPP"},
        {"name": "alerts", "description": "Price alerts and notifications"},
        {"name": "health", "description": "API health check"},
    ],
}

# ---------------------------------------------------------------------------
# JWT (SimpleJWT)
# ---------------------------------------------------------------------------

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

try:
    import whitenoise  # noqa: F401

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
except ImportError:
    pass  # Django will use its default static file storage

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
