from rest_framework import serializers

from account.models import MyUser
from chat.models import Chat, Message, MessageAttachment
from chat.utils import get_dealer_name, ws_send_message, build_file_url


class MessageAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MessageAttachment
        fields = ("id", "file")
        read_only_fields = ("id",)

    @staticmethod
    def get_file(instance):
        return build_file_url(instance.file.url)


class SenderSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MyUser
        fields = ("id", "name", "image")
        read_only_fields = ("id", "name")

    def get_image(self, instance):
        if instance.image:
            return build_file_url(instance.image.url)


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
        chat = attrs.get("chat")
        if chat and user.is_dealer and chat.dealer != user:
            raise serializers.ValidationError({"detail": "У вас нет доступа"})

        if user.is_manager:
            if not Chat.objects.filter(dealer__dealer_profile__managers=user.id).exists():
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

    def to_representation(self, instance):
        represent = super().to_representation(instance)
        represent["chat_id"] = str(represent["chat_id"])
        return represent


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

    @staticmethod
    def get_last_message(instance):
        last_message = instance.messages.order_by("-created_at").first()
        if last_message:
            return MessageSerializer(instance=last_message, many=False).data

    def get_new_messages_count(self, instance):
        if self.user.is_manager:
            return instance.messages.filter(sender=instance.dealer, is_read=False).count()
        return instance.messages.exclude(sender=self.user, is_read=True).count()
