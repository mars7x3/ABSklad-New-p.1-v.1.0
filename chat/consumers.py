import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from account.models import MyUser
from account.utils import send_push_notification as mobile_notification
from chat.async_queries import (
    get_chat_messages, create_db_message, set_read_message,
    get_chats_for_dealer, is_dealer_message, get_chat_receivers, get_chats_for_manager, get_chat_by_id
)
from chat.models import Chat
from chat.validators import validate_user_active, validate_is_manager, validate_is_dealer
from chat.utils import get_limit_and_offset, is_room_active


class AsyncBaseChatConsumer(AsyncWebsocketConsumer):
    @cached_property
    def _user(self):
        return self.scope['user']

    @cached_property
    def room(self):
        if not self._user.is_anonymous:
            return slugify(self._user.username)

    async def validate_user(self):
        pass

    async def connect(self):
        if not self.room:
            await self.close(code=4004)
            return

        is_valid_user = await self.validate_user()
        if not is_valid_user:
            await self.close(code=4004)
        else:
            await self.channel_layer.group_add(self.room, self.channel_name)
            await self.accept()

    async def disconnect(self, code):
        if self.room:
            await self.channel_layer.group_discard(self.room, self.channel_name)

    async def is_room_active(self, room: str) -> bool:
        return await is_room_active(self.channel_layer, room)


class AsyncCommandConsumer(AsyncBaseChatConsumer):
    ERRORS = {
        "chat_id_required": _("`chat_id` is required!"),
        "msg_id_required": _("`msg_id` is required!"),
        "empty_message": _("Empty message cannot be send!"),
        "default_message": _("Something went wrong!"),
        "command_required": _("`command` is required!"),
        "chat_not_found": _("not found chat!")
    }

    user_validators = ()
    BASE_COMMANDS = {
        'chats': 'get_chats_command',  # command: chats, 'page', 'page_size', 'search': default None
        'chat_messages': 'get_chat_messages_command',  # command: chat_messages, 'chat_id', 'page', 'page_size'
        'send_message': 'new_message_command',  # command: send_message, 'chat_id', 'text'
        'read_message': 'read_message_command',  # command: read_message, 'msg_id', 'chat_id'
    }

    @cached_property
    def commands(self):
        return self.BASE_COMMANDS

    async def validate_user(self) -> bool:
        valid = False
        for validator in self.user_validators or []:
            valid = await validator(self._user)
            if valid is False:
                break
        return valid

    async def receive(self, text_data=None, bytes_data=None):
        try:
            req_data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error_message(reason="support only json!")
            return

        input_command = req_data.get('command')

        if not input_command:
            await self.send_error_message(reason_key="command_required")
            return

        command = self.commands.get(input_command)
        if not command:
            await self.send_error_message(reason=f'command `{input_command}` does not support!')
            return

        await getattr(self, command)(input_command, req_data)

    async def send_message(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def send_success_message(self, message_type: str, data, receiver: str = None):
        if receiver:
            await self.channel_layer.group_send(
                receiver,
                {'type': 'send_message', 'data': {"message_type": message_type, "results": data}}
            )
            return

        await self.channel_layer.group_send(
            self.room,
            {'type': 'send_message', 'data': {"message_type": message_type, "results": data}}
        )

    async def send_error_message(self, reason_key=None, reason=None):
        if reason_key:
            reason = self.ERRORS[reason_key]
        elif not reason:
            reason = self.ERRORS["default_message"]

        await self.channel_layer.group_send(
            self.room,
            {'type': 'send_message', 'data': {"message_type": "error", "reason": force_str(reason)}}
        )

    async def get_chats_command(self, message_type, req_data):
        chats = await get_chats_for_dealer(self._user)
        await self.send_success_message(message_type, data=chats)

    async def get_chat_messages_command(self, message_type, req_data):
        chat_id = req_data.get('chat_id')
        if not chat_id:
            await self.send_error_message(reason_key="chat_id_required")
            return

        limit, offset = get_limit_and_offset(req_data, max_page_size=20)
        messages = await get_chat_messages(chat_id, limit=limit, offset=offset)
        await self.send_success_message(message_type, data=messages)

    async def send_msg_to_chat_receivers(self, chat: Chat, msg_data, message_type):
        receivers = await get_chat_receivers(chat)
        if not receivers:
            await self.send_success_message(message_type, data=msg_data)
            return

        processed_receivers = set()
        for receiver in receivers or []:
            if not receiver or receiver in processed_receivers:
                continue

            await self.send_success_message(
                receiver=receiver,
                message_type="new_message",
                data=msg_data
            )
            processed_receivers.add(receiver)

    async def new_message_command(self, message_type, req_data):
        chat_id = req_data.get('chat_id')
        if not chat_id:
            await self.send_error_message(reason_key="chat_id_required")
            return

        chat = await get_chat_by_id(chat_id)
        if not chat:
            await self.send_error_message(reason_key="chat_not_found")
            return

        text = req_data.get('text')
        if not text:
            await self.send_error_message(reason_key="empty_message")
            return

        data = await create_db_message(self._user.id, chat_id, text)
        await self.send_msg_to_chat_receivers(chat, msg_data=data, message_type=message_type)

    async def read_message_command(self, message_type, req_data):
        msg_id = req_data.get('msg_id')
        if not msg_id:
            await self.send_error_message(reason_key="msg_id_required")
            return

        msg_data = await set_read_message(msg_id)
        if not msg_data:
            await self.send_error_message()
            return

        chat = await get_chat_by_id(msg_data['chat_id'])
        receivers = await get_chat_receivers(chat)
        if not receivers:
            await self.send_success_message(message_type, data=msg_data)
            return

        for receiver in receivers:
            await self.send_success_message(
                receiver=receiver,
                message_type=message_type,
                data=msg_data
            )


class ManagerConsumer(AsyncCommandConsumer):
    user_validators = (validate_user_active, validate_is_manager)

    # async def send_success_message(self, message_type: str, data, receiver: str = None):
    #     if message_type != "new_message":
    #         await super().send_success_message(message_type, data, receiver=receiver)
    #         return
    #
    #     if receiver and not await self.is_room_active(receiver):
    #
    #         user = MyUser.objects.filter(username=receiver).first()
    #         if not user:
    #             await super().send_success_message(message_type, data, receiver=receiver)
    #             return
    #
    #         fb_tokens = list(user.fb_tokens.all().values_list('token', flat=True))
    #
    #         if fb_tokens:
    #             mobile_notification(
    #                 text=data["text"],
    #                 title=data["sender"]["name"],
    #                 tokens=fb_tokens,
    #                 link_id=data["chat_id"],
    #                 status="chat",
    #             )
    #         return
    #
    #     await super().send_success_message(message_type, data, receiver=receiver)

    async def get_chats_command(self, message_type, req_data):
        limit, offset = get_limit_and_offset(req_data, max_page_size=20)
        chats = await get_chats_for_manager(
            self._user,
            limit=limit,
            offset=offset,
            search=req_data.get('search')
        )
        await self.send_success_message(message_type, data=chats)

    async def read_message_command(self, message_type, req_data):
        msg_id = req_data.get('msg_id')
        if not msg_id:
            await self.send_error_message(reason_key="msg_id_required")
            return

        check_message = await is_dealer_message(msg_id)
        if not check_message:
            await self.send_error_message(reason=_("Dealer only can set read this message"))
            return

        return await super().read_message_command(message_type, req_data)

    # TODO: add checking manager on send message because any users can send message to any chats


class DealerConsumer(AsyncCommandConsumer):
    user_validators = (validate_user_active, validate_is_dealer)
