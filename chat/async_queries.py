from django.db import connection
from channels.db import database_sync_to_async

from general_service.utils import dictfetchall
from .constants import CITY_CHATS_SQL, CITY_SEARCH_CHATS_SQL, DEALER_CHAT_SQL
from .models import Message, Chat
from .serializers import MessageSerializer
from .utils import get_manager_profile, get_chat_receivers, build_chats_data


@database_sync_to_async
def get_chats_for_dealer(dealer):
    with connection.cursor() as cursor:
        cursor.execute(DEALER_CHAT_SQL, [dealer.status, dealer.id])
        chats = dictfetchall(cursor)
    return build_chats_data(chats)


@database_sync_to_async
def get_manager_city_id(user):
    profile = get_manager_profile(user)
    if profile:
        return getattr(profile, 'city_id', None)


@database_sync_to_async
def get_chats_by_city(current_user, city_id: int, limit: int, offset: int, search: str = None):
    params = [current_user.status, city_id]
    sql = CITY_CHATS_SQL
    if search:
        sql = CITY_SEARCH_CHATS_SQL
        params.append(f'%{search}%')

    params += [limit, offset]

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        chats = dictfetchall(cursor)

    return build_chats_data(chats)


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
