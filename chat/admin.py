from django.contrib import admin

from chat.models import Chat, Message, MessageAttachment


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "dealer")
    search_fields = ("id", "dealer__email", "dealer__username")


class MessageAttachmentInline(admin.StackedInline):
    model = MessageAttachment
    extra = 0


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    autocomplete_fields = ("chat",)
    search_fields = ("id", "chat_id", "sender__username", "sender__email")
    list_filter = ('sender__status', "is_read", "created_at")
    inlines = (MessageAttachmentInline,)
