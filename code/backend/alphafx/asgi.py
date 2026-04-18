"""
ASGI config for AlphaFX project.
Supports HTTP and WebSocket via Django Channels.
"""

import os

import apps.rates.routing
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alphafx.settings.base")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(apps.rates.routing.websocket_urlpatterns)
        ),
    }
)
