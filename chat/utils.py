from typing import Any, Iterable
from urllib.parse import urljoin

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify

from account.models import DealerProfile, MyUser
from account.utils import send_push_notification as mobile_notification
from chat.constants import CHATS_IGNORE_COLS, CHAT_FIELDS_SUBSTITUTES
from chat.models import Chat


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


def collect_chat_receivers(chat):
    dealer = chat.dealer
    receivers = [slugify(dealer.username)]

    profile = get_dealer_profile(dealer)
    if not profile:
        return receivers
    receivers += list(map(lambda username: slugify(username), profile.managers.values_list("username", flat=True)))
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
    return chat.dealer.name or chat.dealer.email


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


def build_file_url(file_path):
    return urljoin(settings.SERVER_URL, file_path)


def create_chats_for_dealers(user_ids: Iterable[int] = None) -> list[Chat] | None:
    user_model = get_user_model()

    dealers = user_model.objects.filter(status="dealer").exclude(
        id__in=Chat.objects.all().values_list("dealer_id", flat=True)
    ).values_list("id", flat=True)

    if user_ids is None:
        user_ids = dealers
    else:
        created_chat_user_ids = list(Chat.objects.all().values_list("dealer_id", flat=True))
        user_ids = [
            user_id
            for user_id in user_ids
            if user_id in dealers and user_id not in created_chat_user_ids
        ]

    new_chats = [
        Chat(dealer_id=new_user_id)
        for new_user_id in user_ids
    ]
    if new_chats:
        return Chat.objects.bulk_create(new_chats)


async def is_room_active(channel_layer, room_name) -> bool:
    channels = await channel_layer.group_channels(room_name)
    return len(channels) > 0


def ws_send_message(chat, message_data):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    event = {'type': 'send_message', 'data': {"message_type": "new_message", "results": message_data}}

    for receiver in set(collect_chat_receivers(chat)):
        # if not async_to_sync(is_room_active)(channel_layer, receiver):
        #     user = MyUser.objects.filter(username=receiver).first()
        #     if not user:
        #         async_to_sync(channel_layer.group_send)(receiver, event)
        #         continue
        #
        #     fb_tokens = list(user.fb_tokens.all().values_list('token', flat=True))
        #     if fb_tokens:
        #         text = message_data["text"]
        #         files = message_data["files"]
        #
        #         if files:
        #             files_count = len(files)
        #             text = f"{files_count} files" if files_count > 1 else "1 file"
        #
        #         mobile_notification(
        #             text=text,
        #             title=message_data["sender"]["name"],
        #             tokens=fb_tokens,
        #             link_id=message_data["chat_id"],
        #             status="chat",
        #         )
        #         continue
        async_to_sync(channel_layer.group_send)(receiver, event)
