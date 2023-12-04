from django.urls import path

from chat.views import MessageCreateAPIView


urlpatterns = [
    path('message/', MessageCreateAPIView.as_view(), name='chat-create-message'),
]
