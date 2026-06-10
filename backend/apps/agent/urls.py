from django.urls import path

from apps.agent.views import ChatView

urlpatterns = [
    path("agent/chat/", ChatView.as_view(), name="agent-chat"),
]
