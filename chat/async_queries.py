from channels.db import database_sync_to_async
from django.http import HttpRequest

from chat.models import Message, Chat
from chat.serializers import MessageSerializer, ChatSerializer
from chat.utils import get_dealer_name, get_manager_profile, get_chat_receivers


@database_sync_to_async
def get_chats_by_dealer(user, limit, offset):
    chats = Chat.objects.filter(dealer_id=user.id)[offset:offset + limit]
    serializer = ChatSerializer(instance=chats, many=True)
    data = serializer.data
    return data


@database_sync_to_async
def get_manager_city_id(user):
    profile = get_manager_profile(user)
    if not profile:
        return
    return getattr(profile, 'city_id', None)


@database_sync_to_async
def get_chats_by_city(user, city_id: int, limit: int, offset: int, search: str = None):
    queryset = Chat.objects.filter(dealer__dealer_profile__city_id=city_id)
    if search:
        queryset = queryset.filter(dealer__dealer_profile__name__icontains=search)

    chats = queryset[offset:offset + limit]
    request = HttpRequest()
    request.user = user
    serializer = ChatSerializer(instance=chats, many=True, context={'request': request})
    data = serializer.data
    request.close()
    return data


@database_sync_to_async
def is_dealer_message(msg_id):
    message = Message.objects.filter(id=msg_id).first()
    return message and message.sender == message.chat.dealer


@database_sync_to_async
def get_chat_receivers_by_chat(chat_id):
    chat = Chat.objects.filter(id=chat_id).first()
    if not chat:
        return

    return get_chat_receivers(chat)


@database_sync_to_async
def get_chat_receivers_by_msg(msg_id):
    message = Message.objects.filter(id=msg_id).select_related('chat').first()
    if not message:
        return

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
    base_queryset = Message.objects.filter(chat_id=chat_id).order_by('-created_at')
    if search:
        base_queryset = base_queryset.filter(dealer__dealer_profile__name__icontains=search)

    queryset = base_queryset[offset:offset + limit]
    serializer = MessageSerializer(instance=queryset, many=True)
    data = serializer.data
    return data


@database_sync_to_async
def create_db_message(user_id: int, chat_id: str, text: str) -> dict:
    msg = Message.objects.create(sender_id=user_id, chat_id=chat_id, text=text)
    request = HttpRequest()
    serializer = MessageSerializer(instance=msg, many=False, context={"request": request})
    data = serializer.data
    request.close()
    return data


@database_sync_to_async
def set_read_message(msg_id: str):
    msg = Message.objects.filter(id=msg_id).first()
    if not msg:
        return

    msg.is_read = True
    msg.save()
    request = HttpRequest()
    serializer = MessageSerializer(instance=msg, many=False, context={"request": request})
    data = serializer.data
    request.close()
    return data
