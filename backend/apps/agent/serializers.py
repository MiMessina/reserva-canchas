from rest_framework import serializers

from apps.agent.models import BotConversationLog


# ---------------------------------------------------------------------------
# Serializers originales del chat demo (NO borrar — ChatView los usa)
# ---------------------------------------------------------------------------


class ChatMessageSerializer(serializers.Serializer):
    """
    Serializer para el request del chat demo.

    messages: historial completo de la conversación en formato Claude API.
    Cada mensaje tiene role ('user' | 'assistant') y content (string o lista).
    El frontend mantiene y envía el historial completo en cada request (stateless).
    """

    messages = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="Historial completo de mensajes. Último mensaje debe ser del usuario.",
    )

    def validate_messages(self, value):
        for msg in value:
            if "role" not in msg or "content" not in msg:
                raise serializers.ValidationError(
                    "Cada mensaje debe tener 'role' y 'content'."
                )
            if msg["role"] not in ("user", "assistant"):
                raise serializers.ValidationError(
                    "El role debe ser 'user' o 'assistant'."
                )
        return value


# ---------------------------------------------------------------------------
# Serializers del visor de conversaciones bot (T5-02)
# ---------------------------------------------------------------------------


class BotLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para POST /api/bot/log/

    Valida y crea un BotConversationLog. El campo `booking_id` permite
    asociar el mensaje a una reserva existente (opcional).
    """

    booking_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID de la reserva relacionada (opcional).",
    )

    class Meta:
        model = BotConversationLog
        fields = ["id", "phone", "player_name", "direction", "message", "booking_id", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_direction(self, value):
        valid = {BotConversationLog.DIRECTION_INBOUND, BotConversationLog.DIRECTION_OUTBOUND}
        if value not in valid:
            raise serializers.ValidationError(
                f"El campo direction debe ser 'inbound' o 'outbound'. Recibido: '{value}'."
            )
        return value


class BotLogMessageSerializer(serializers.ModelSerializer):
    """
    Serializer para un mensaje individual dentro de una conversación agrupada.
    Usado en la respuesta de GET /api/bot/conversations/
    """

    booking_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = BotConversationLog
        fields = ["id", "direction", "message", "created_at", "booking_id"]


class BotConversationSerializer(serializers.Serializer):
    """
    Serializer de solo lectura para una conversación agrupada por phone.
    Usado en la respuesta de GET /api/bot/conversations/
    """

    phone = serializers.CharField()
    player_name = serializers.CharField()
    last_message_at = serializers.DateTimeField()
    messages = BotLogMessageSerializer(many=True)
