from django.urls import re_path

from chat.consumers import ManagerConsumer, DealerConsumer


websocket_urlpatterns = [
    re_path(r"ws/chat/manager/(?P<access_token>[^/]+)", ManagerConsumer.as_asgi()),
    re_path(r"ws/chat/dealer/(?P<access_token>[^/]+)", DealerConsumer.as_asgi()),
]
