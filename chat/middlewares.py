from channels.db import database_sync_to_async
from channels.sessions import CookieMiddleware
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_from_token(token):
    from django.contrib.auth.models import AnonymousUser
    from django.core.exceptions import ObjectDoesNotExist

    try:
        access_token = AccessToken(token)
        return get_user_model().objects.get(id=access_token['user_id'])
    except (ObjectDoesNotExist, TokenError):
        return AnonymousUser()


class AccessTokenAuthMiddleware:
    def __init__(self, inner):
        self.app = inner

    @staticmethod
    def access_token_from_url(scope) -> str:
        return [i for i in scope.get('path').split('/') if i.strip()][-1]

    async def __call__(self, scope, receive, send):
        access_token = self.access_token_from_url(scope)
        user = await get_user_from_token(access_token)
        return await self.app(dict(scope, user=user), receive, send)


def TokenAuthMiddlewareStack(inner):
    return CookieMiddleware(AccessTokenAuthMiddleware(inner))
