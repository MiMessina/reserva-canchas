from django.urls import path

from apps.agent.views import BotConversationDeleteView, BotConversationsView, BotLogView, ChatView

urlpatterns = [
    # Chat demo con IA (JWT requerido)
    path("agent/chat/", ChatView.as_view(), name="agent-chat"),
    # Bot WhatsApp — registro de mensajes (AllowAny, sin JWT)
    path("bot/log/", BotLogView.as_view(), name="bot-log"),
    # Bot WhatsApp — visor de conversaciones agrupadas (JWT requerido)
    path("bot/conversations/", BotConversationsView.as_view(), name="bot-conversations"),
    # Bot WhatsApp — borrar conversación (soft-delete, JWT requerido)
    path("bot/conversations/<str:phone>/", BotConversationDeleteView.as_view(), name="bot-conversation-delete"),
]
