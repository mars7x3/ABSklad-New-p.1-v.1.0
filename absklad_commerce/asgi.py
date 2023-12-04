"""
ASGI config for server project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "absklad_commerce.settings")

django_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
#from channels.security.websocket import AllowedHostsOriginValidator

from chat.routers import websocket_urlpatterns
from chat.middlewares import TokenAuthMiddlewareStack

application = ProtocolTypeRouter({
    'http': django_application,
    "websocket": TokenAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
