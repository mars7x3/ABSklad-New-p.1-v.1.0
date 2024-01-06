from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify

from account.models import DealerProfile
from chat.constants import CHATS_IGNORE_COLS, CHAT_FIELDS_SUBSTITUTES


def convert_to_int(page, default: int):
    try:
        return abs(int(page))
    except (ValueError, TypeError):
        return default


def get_limit_and_offset(req_data: dict[str, Any], max_page_size: int, default_page_size: int = 10):
    page = convert_to_int(req_data.get('page'), 1)
    limit = convert_to_int(req_data.get('page_size'), default_page_size)
    if limit > max_page_size:
        limit = max_page_size

    offset = limit * (page - 1) if page > 1 else 0
    return limit, offset + 1 if offset > 1 else 0


def get_chat_receivers(chat):
    dealer = chat.dealer
    receivers = [slugify(dealer.username)]

    profile = get_dealer_profile(dealer)
    if not profile or not profile.city:
        return receivers

    manager_usernames = list(
        get_user_model().objects.filter(
            status='manager',
            manager_profile__city=profile.city
        ).values_list("username", flat=True)
    )
    receivers += list(map(lambda username: slugify(username), manager_usernames))
    return receivers


def get_dealer_profile(user) -> DealerProfile | None:
    try:
        return user.dealer_profile
    except ObjectDoesNotExist:
        return


def get_manager_profile(user) -> DealerProfile | None:
    try:
        return user.manager_profile
    except ObjectDoesNotExist:
        return


def get_dealer_name(chat):
    dealer = chat.dealer
    return dealer.name or dealer.email


def ws_send_message(chat, message_data):
    channel_layer = get_channel_layer()
    event = {'type': 'send_message', 'data': {"message_type": "new_message", "results": message_data}}

    for receiver in set(get_chat_receivers(chat)):
        async_to_sync(channel_layer.group_send)(receiver, event)


def build_chats_data(chats_data) -> list[dict[str, Any]]:
    collected_data = []
    for chat_data in chats_data:
        data = {}
        for field, value in chat_data.items():
            if field in CHATS_IGNORE_COLS:
                continue

            if value and field in CHAT_FIELDS_SUBSTITUTES:
                value = CHAT_FIELDS_SUBSTITUTES[field](value)

            data[field] = value

        if data:
            collected_data.append(data)
    return collected_data
