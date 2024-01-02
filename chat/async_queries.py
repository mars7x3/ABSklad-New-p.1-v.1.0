from channels.db import database_sync_to_async

from chat.models import Message, Chat
from chat.serializers import MessageSerializer, ChatSerializer
from chat.utils import get_dealer_name, get_manager_profile, get_chat_receivers


@database_sync_to_async
def get_chats_by_dealer(current_user, dealer_id, limit, offset):
    return ChatSerializer(
        instance=Chat.objects.filter(dealer_id=dealer_id)[offset:offset + limit],
        many=True,
        context={"user": current_user}
    ).data


@database_sync_to_async
def get_manager_city_id(user):
    profile = get_manager_profile(user)
    if profile:
        return getattr(profile, 'city_id', None)


@database_sync_to_async
def get_chats_by_city(current_user, city_id: int, limit: int, offset: int, search: str = None):
    queryset = Chat.objects.filter(dealer__dealer_profile__city_id=city_id)
    if search:
        queryset = queryset.filter(dealer__name__icontains=search)

    return ChatSerializer(
        instance=queryset[offset:offset + limit],
        many=True,
        context={"user": current_user}
    ).data


@database_sync_to_async
def is_dealer_message(msg_id):
    message = Message.objects.filter(id=msg_id).first()
    return message and message.sender == message.chat.dealer


@database_sync_to_async
def get_chat_receivers_by_chat(chat_id):
    chat = Chat.objects.filter(id=chat_id).first()
    if chat:
        return get_chat_receivers(chat)


@database_sync_to_async
def get_chat_receivers_by_msg(msg_id):
    message = Message.objects.filter(id=msg_id).select_related('chat').first()
    if message:
        return get_chat_receivers(message.chat)


@database_sync_to_async
def get_dealer_name_by_chat_id(chat_id):
    chat = Chat.objects.filter(id=chat_id).first()
    if not chat:
        return get_dealer_name(chat)


@database_sync_to_async
def get_dealer_name_by_msg_id(msg_id):
    message = Message.objects.filter(id=msg_id).first()
    if message:
        return get_dealer_name(message.chat)


@database_sync_to_async
def get_chat_messages(chat_id: str, limit, offset, search: str = None):
    base_queryset = Message.objects.filter(chat_id=chat_id).select_related("sender").order_by('-created_at')
    if search:
        base_queryset = base_queryset.filter(dealer__name__icontains=search)

    page = list(base_queryset[offset:offset + limit])
    if page:
        page.reverse()
    return MessageSerializer(instance=page, many=True).data


@database_sync_to_async
def create_db_message(user_id: int, chat_id: str, text: str) -> dict:
    return MessageSerializer(
        instance=Message.objects.create(sender_id=user_id, chat_id=chat_id, text=text),
        many=False
    ).data


@database_sync_to_async
def set_read_message(msg_id: str):
    msg = Message.objects.filter(id=msg_id).first()
    if msg:
        msg.is_read = True
        msg.save()
        return MessageSerializer(instance=msg, many=False).data
