from django.urls import re_path
from .consumers import ConfortConsumer

websocket_urlpatterns = [
    re_path(r"ws/salle/(?P<salle_id>\d+)/$", ConfortConsumer.as_asgi()),
]
