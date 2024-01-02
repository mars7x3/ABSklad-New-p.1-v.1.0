from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from account.models import MyUser
from chat.models import Chat, Message, MessageAttachment
from chat.utils import get_dealer_name, ws_send_message


class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = ("id", "file")
        extra_kwargs = {"id": {"read_only": True}}


class SenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ("id", "name", "image")


class MessageSerializer(serializers.ModelSerializer):
    sender = SenderSerializer(many=False, read_only=True)
    chat_id = serializers.PrimaryKeyRelatedField(
        queryset=Chat.objects.all(),
        required=True,
        source="chat"
    )
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    files = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False, required=True),
        required=True,
        write_only=True
    )
    is_dealer_message = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Message
        fields = ("id", "chat_id", "sender", "text", "is_read", "attachments", "created_at", "files",
                  "is_dealer_message")
        read_only_fields = ("id", "is_read")

    def get_is_dealer_message(self, instance) -> bool:
        return instance.sender.status == 'dealer'

    def validate(self, attrs):
        user = self.context["request"].user
        chat = attrs["chat_id"]

        if user.is_dealer and chat.dealer != user:
            raise serializers.ValidationError({"detail": "У вас нет доступа"})

        if user.is_manager:
            try:
                manager_profile = user.manager_profile
            except ObjectDoesNotExist:
                raise serializers.ValidationError({"detail": "У вас нет доступа"})

            if not Chat.objects.filter(dealer__dealer_profile__city_id=manager_profile.city).exists():
                raise serializers.ValidationError({"detail": "У вас нет доступа"})

        attrs['sender'] = user
        return attrs

    def create(self, validated_data):
        files = validated_data.pop("files", None)
        message = super().create(validated_data)
        if files:
            MessageAttachment.objects.bulk_create(
                [MessageAttachment(message=message, file=file) for file in files]
            )
        ws_send_message(message.chat, self.to_representation(message))
        return message


class ChatSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField(read_only=True)
    last_message = serializers.SerializerMethodField(read_only=True)
    new_messages_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Chat
        fields = ('id', 'name', 'image', 'last_message', 'new_messages_count')

    @property
    def user(self):
        request = self.context.get("request")
        if request:
            return request.user
        return self.context.get('user')

    def get_name(self, instance):
        if self.user == instance.dealer:
            return "Manager"

        return get_dealer_name(instance)

    def get_image(self, instance):
        if self.user == instance.dealer:
            return

        if instance.dealer.image:
            return instance.dealer.image.url

    def get_last_message(self, instance):
        last_message = instance.messages.order_by("-created_at").first()
        if last_message:
            return MessageSerializer(instance=last_message, many=False).data

    def get_new_messages_count(self, instance):
        if self.user == instance.dealer:
            return instance.messages.exclude(sender=self.user, is_read=True).count()
        return instance.messages.filter(sender=instance.dealer, is_read=False).count()
