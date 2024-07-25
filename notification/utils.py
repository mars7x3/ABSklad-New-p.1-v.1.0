import base64
import json
from logging import getLogger

from cryptography.hazmat.primitives import serialization
from django.conf import settings
from pywebpush import webpush, WebPushException, Vapid

from notification.models import Subscription

logger = getLogger(__name__)


def send_web_push_notification(user_id: int, title: str, msg: str = None, data=None, message_type: str = None):
    subscribers = Subscription.objects.filter(user_id=user_id)

    if not subscribers.exists():
        raise Exception(f"Subscriptions for user {user_id} not found")

    subscribers = subscribers.values_list("id", "subscription_info")

    msg_data = {
        "title": title,
        "body": msg or "",
        "icon": settings.NOTIFICATION_ICON,
        "data": data or {},
        "message_type": message_type
    }

    to_delete = []

    for subscriber_id, subscriber_info in subscribers:
        try:
            webpush(
                subscription_info=subscriber_info,
                data=json.dumps(msg_data),
                vapid_private_key=settings.VAPID_PRIVATE,
                vapid_claims={"sub": f"mailto:{settings.WEB_PUSH_EMAIL}"}
            )
        except WebPushException as ex:
            logger.error(ex)

            if ex.response.status_code == 410:
                to_delete.append(subscriber_id)

    if to_delete:
        Subscription.objects.filter(id__in=to_delete).delete()


def generate_vapid_keys():
    vapid = Vapid()
    vapid.generate_keys()

    public_key = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    private_key = vapid.private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    serialized_public_key = serialization.load_pem_public_key(public_key.encode())
    raw_public_key = serialized_public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    base64_public_key = base64.urlsafe_b64encode(raw_public_key).decode('utf-8')
    return {
        "public": public_key,
        "private": private_key,
        "public_base64": base64_public_key
    }
