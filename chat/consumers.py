import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from chat.async_queries import (
    get_chat_messages, create_db_message, set_read_message, get_chats_by_city,
    get_chats_by_dealer, is_dealer_message, get_chat_receivers_by_chat, get_manager_city_id
)
from chat.validators import validate_user_active, validate_is_manager, validate_is_dealer
from chat.utils import get_limit_and_offset


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
        if self.room:
            await self.validate_user()
            await self.channel_layer.group_add(self.room, self.channel_name)
            await self.accept()
        else:
            await self.close(code=4004)

    async def disconnect(self, code):
        if self.room:
            await self.channel_layer.group_discard(self.room, self.channel_name)


class AsyncCommandConsumer(AsyncBaseChatConsumer):
    ERRORS = {
        "chat_id_required": _("`chat_id` is required!"),
        "msg_id_required": _("`msg_id` is required!"),
        "empty_message": _("Empty message cannot be send!"),
        "default_message": _("Something went wrong!"),
        "command_required": _("`command` is required!")
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

    async def validate_user(self):
        for validator in self.user_validators or []:
            if validator(self._user) is False:
                await self.close(code=4002)
                break

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
        limit, offset = get_limit_and_offset(req_data, max_page_size=20)
        chats = await get_chats_by_dealer(
            current_user=self._user,
            dealer_id=self._user.id,
            limit=limit,
            offset=offset
        )
        await self.send_success_message(message_type, data=chats)

    async def get_chat_messages_command(self, message_type, req_data):
        chat_id = req_data.get('chat_id')
        if not chat_id:
            await self.send_error_message(reason_key="chat_id_required")
            return

        limit, offset = get_limit_and_offset(req_data, max_page_size=20)
        messages = await get_chat_messages(chat_id, limit=limit, offset=offset)
        await self.send_success_message(message_type, data=messages)

    async def new_message_command(self, message_type, req_data):
        chat_id = req_data.get('chat_id')
        if not chat_id:
            await self.send_error_message(reason_key="chat_id_required")
            return

        text = req_data.get('text')
        if not text:
            await self.send_error_message(reason_key="empty_message")
            return

        data = await create_db_message(self._user.id, chat_id, text)
        receivers = await get_chat_receivers_by_chat(chat_id)
        if not receivers:
            await self.send_success_message(message_type, data=data)
            return

        for receiver in receivers or []:
            await self.send_success_message(
                receiver=receiver,
                message_type="new_message",
                data={"status": data}
            )

    async def read_message_command(self, message_type, req_data):
        msg_id = req_data.get('msg_id')
        if not msg_id:
            await self.send_error_message(reason_key="msg_id_required")
            return

        msg_data = await set_read_message(msg_id)
        if not msg_data:
            await self.send_error_message()
            return

        receivers = await get_chat_receivers_by_chat(msg_data['chat_id'])
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

    async def get_chats_command(self, message_type, req_data):
        city_id = await get_manager_city_id(self._user)
        if not city_id:
            await self.send_error_message(reason=_("Not found city id"))
            return

        limit, offset = get_limit_and_offset(req_data, max_page_size=20)
        chats = await get_chats_by_city(
            self._user,
            city_id=city_id,
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


class DealerConsumer(AsyncCommandConsumer):
    user_validators = (validate_user_active, validate_is_dealer)
