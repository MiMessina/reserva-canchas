"""
Service layer — app agent.

seed_demo_conversations: siembra conversaciones de demo en un esquema de tenant.
Idempotente — si ya hay datos [DEMO], no inserta nada.
"""

from datetime import timedelta

from django.utils import timezone
from django_tenants.utils import schema_context

from apps.agent.models import BOT_DEMO_MARKER, BotConversationLog
from apps.agent.management.commands.seed_bot_demo import DEMO_CONVERSATIONS


def seed_demo_conversations(schema_name: str) -> int:
    """
    Siembra conversaciones de demo en el esquema indicado si no existen.

    Idempotente: si ya hay registros con el marcador [DEMO], retorna 0 sin tocar nada.

    Args:
        schema_name: nombre del esquema PostgreSQL del tenant (ej: "demo").

    Returns:
        Cantidad de mensajes insertados (0 si ya existían).
    """
    with schema_context(schema_name):
        if BotConversationLog.objects.filter(
            message__startswith=BOT_DEMO_MARKER
        ).exists():
            return 0

        now = timezone.now()
        total = 0

        for conv in DEMO_CONVERSATIONS:
            base_time = now - timedelta(minutes=conv["minutes_ago"])

            for i, (direction, message) in enumerate(conv["messages"]):
                msg_time = base_time + timedelta(seconds=i * 30)
                is_last = i == len(conv["messages"]) - 1

                log = BotConversationLog.objects.create(
                    phone=conv["phone"],
                    player_name=conv["player_name"],
                    direction=direction,
                    message=f"{BOT_DEMO_MARKER} {message}",
                    booking_id=conv["booking_id"] if direction == "outbound" and is_last else None,
                )
                # auto_now_add impide pasar created_at en create();
                # update() escribe directo en SQL sin pasar por el modelo.
                BotConversationLog.objects.filter(pk=log.pk).update(created_at=msg_time)
                total += 1

        return total
