from apps.rates.consumers import RateStreamConsumer
from django.urls import re_path

websocket_urlpatterns = [
    re_path(r"ws/rates/(?P<pair>[A-Za-z]+)/$", RateStreamConsumer.as_asgi()),
    re_path(r"ws/rates/$", RateStreamConsumer.as_asgi()),
]
