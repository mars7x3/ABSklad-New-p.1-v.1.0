from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models


class BaseModel(models.Model):
    objects = models.Manager()

    id = models.UUIDField(default=uuid4, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class Chat(BaseModel):
    dealer = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='chats')


class Message(BaseModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='messages')
    text = models.TextField(blank=True, null=True)
    is_read = models.BooleanField(default=False)


class MessageAttachment(BaseModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='chat/%Y-%m/')
