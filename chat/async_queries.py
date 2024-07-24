from urllib.parse import urljoin

from django.conf import settings
from django.db import connection
from channels.db import database_sync_to_async

from account.models import MyUser
from general_service.utils import dictfetchall
from .constants import CITY_CHATS_SQL, CITY_SEARCH_CHATS_SQL, DEALER_CHAT_SQL, MANAGER_CHATS_SQL, \
    MANAGER_CHATS_SEARCH_SQL
from .models import Message, Chat
from .serializers import MessageSerializer
from .utils import get_manager_profile, collect_chat_receivers, build_chats_data


FILES_BASE_URL = urljoin(settings.SERVER_URL, settings.MEDIA_ROOT)


@database_sync_to_async
def get_chats_for_dealer(dealer):
    with connection.cursor() as cursor:
        cursor.execute(DEALER_CHAT_SQL, [dealer.status, FILES_BASE_URL, dealer.id])
        chats = dictfetchall(cursor)
    return build_chats_data(chats)


@database_sync_to_async
def get_manager_city_id(user):
    profile = get_manager_profile(user)
    if profile:
        return getattr(profile, 'city_id', None)


@database_sync_to_async
def get_chats_by_city(current_user, city_id: int, limit: int, offset: int, search: str = None):
    params = [current_user.status, FILES_BASE_URL, city_id]
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
def get_chats_for_manager(current_user, limit: int, offset: int, search: str = None):
    params = [current_user.status, current_user.id]
    sql = MANAGER_CHATS_SQL
    if search:
        sql = MANAGER_CHATS_SEARCH_SQL
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
def get_chat_by_id(chat_id):
    return Chat.objects.filter(id=chat_id).first()


@database_sync_to_async
def get_chat_receivers(chat: Chat):
    return collect_chat_receivers(chat)


@database_sync_to_async
def get_user_firebase_tokens(username) -> list[str] | None:
    user = MyUser.objects.filter(username=username).first()
    if user:
        return list(user.fb_tokens.all().values_list('token', flat=True))


@database_sync_to_async
def get_chat_messages(chat_id: str, limit, offset, search: str = None):
    base_queryset = Message.objects.filter(chat_id=chat_id).select_related("sender").order_by('-created_at')
    if search:
        base_queryset = base_queryset.filter(dealer__name__icontains=search)
    return MessageSerializer(instance=list(base_queryset[offset:offset + limit]), many=True).data


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
