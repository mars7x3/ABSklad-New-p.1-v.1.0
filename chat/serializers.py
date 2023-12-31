from rest_framework import serializers


from chat.models import Chat, Message, MessageAttachment
from chat.utils import get_dealer_name, get_dealer_profile, ws_send_message


class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = ("id", "file")
        extra_kwargs = {"id": {"read_only": True}}


class MessageSerializer(serializers.ModelSerializer):
    chat_id = serializers.SerializerMethodField(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    files = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False, required=True),
        required=True,
        write_only=True
    )

    class Meta:
        model = Message
        fields = ("id", "chat", "chat_id", "sender", "text", "is_read", "attachments", "created_at", "files")
        extra_kwargs = {"chat": {"write_only": True}}
        read_only_fields = ("id", "sender", "is_read")

    def get_chat_id(self, instance):
        return str(getattr(instance, 'chat_id'))

    def validate(self, attrs):
        attrs['sender'] = self.context["request"].user
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
        return self.context['request'].user

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
        messages = instance.messages
        if self.user == instance.dealer:
            last_message = messages.exclude(sender=self.user).order_by('-created_at').first()
        else:
            last_message = messages.filter(sender=instance.dealer).order_by('-created_at').first()

        if last_message:
            return MessageSerializer(instance=last_message, many=False).data

    def get_new_messages_count(self, instance):
        if self.user == instance.dealer:
            return instance.messages.exclude(sender=self.user, is_read=True).count()
        return instance.messages.filter(sender=instance.dealer, is_read=False).count()
