from rest_framework import serializers


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
