"""
seed_bot_demo — Inserta conversaciones de prueba del bot WhatsApp en el tenant activo.

Uso:
    docker compose exec backend python manage.py seed_bot_demo
    docker compose exec backend python manage.py seed_bot_demo --tenant demo
    docker compose exec backend python manage.py seed_bot_demo --clear

Opciones:
    --tenant SLUG   Nombre del esquema del tenant (default: demo)
    --clear         Elimina los registros de prueba existentes antes de insertar

Los datos insertados son indistinguibles de los mensajes reales del bot.
Para limpiarlos: botón de papelera en el visor, o --clear en este comando.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.agent.models import BOT_DEMO_MARKER, BotConversationLog

# ---------------------------------------------------------------------------
# Datos de demo
# ---------------------------------------------------------------------------

DEMO_CONVERSATIONS = [
    {
        "phone": "5491123456789@c.us",
        "player_name": "Lucas Rodríguez",
        "messages": [
            ("inbound",  "Hola, quiero reservar una cancha de fútbol 5 para mañana"),
            ("outbound", "¡Hola, Lucas! 👋 Soy el bot de *CANCHERO!*.\n\nTenemos disponibilidad para mañana en Fútbol 5:\n\n1. *Cancha A* — 4 turnos libres\n2. *Cancha B* — 6 turnos libres\n\n¿Cuál preferís?"),
            ("inbound",  "La cancha A, a las 20hs"),
            ("outbound", "Perfecto, turno a las *20:00* 🎯\n\n¿A qué nombre hacemos la reserva?"),
            ("inbound",  "Lucas"),
            ("outbound", "📋 *Resumen de tu reserva:*\n\n🏟️ Cancha A — Fútbol 5\n📅 Mañana\n🕐 20:00 – 21:00\n💰 $15.000\n👤 Lucas\n\n¿Confirmás? (Sí / No)\n\n⚠️ El pago no es reembolsable si no asistís."),
            ("inbound",  "Sí"),
            ("outbound", "✅ ¡Reserva confirmada!\n\nTe esperamos mañana a las 20:00 en Cancha A.\n\n💳 Para confirmar tu lugar, transferí la seña a:\nCBU: 0000003100012345678901\nAlias: CANCHERO.DEMO\n\nEl cajero confirmará tu reserva cuando reciba la transferencia."),
        ],
        "booking_id": None,
        "minutes_ago": 15,
    },
    {
        "phone": "5491187654321@c.us",
        "player_name": "Valentina Gómez",
        "messages": [
            ("inbound",  "Buenas, quiero cancelar mi reserva"),
            ("outbound", "¡Hola! Encontré tu reserva:\n\n📍 *Cancha B — Fútbol 5*\n📅 Hoy\n🕐 18:00 – 19:00\n\n⚠️ ¿Confirmás la cancelación? (Sí / No)\nEl pago no es reembolsable."),
            ("inbound",  "Sí, cancelar"),
            ("outbound", "✅ Tu reserva fue cancelada.\n\nSi querés hacer una nueva reserva, escribime cuando quieras. ¡Hasta la próxima! 👋"),
        ],
        "booking_id": None,
        "minutes_ago": 42,
    },
    {
        "phone": "5491156781234@c.us",
        "player_name": "Martín Pereyra",
        "messages": [
            ("inbound",  "Hola hay pádel disponible el sábado?"),
            ("outbound", "¡Hola! Sí, tenemos disponibilidad para Pádel el sábado:\n\n🎾 *Cancha Pádel 1*\n• 10:00 – 11:30\n• 12:00 – 13:30\n• 16:00 – 17:30\n\n🎾 *Cancha Pádel 2*\n• 09:00 – 10:30\n• 14:00 – 15:30\n\n¿Qué horario te queda mejor?"),
            ("inbound",  "El de las 10 en la 1"),
            ("outbound", "Anotado para las *10:00* 🎯\n\n¿A qué nombre hacemos la reserva?"),
            ("inbound",  "Martín"),
            ("outbound", "📋 *Resumen de tu reserva:*\n\n🎾 Cancha Pádel 1\n📅 Sábado\n🕐 10:00 – 11:30\n💰 $6.000\n👤 Martín\n\n¿Confirmás? (Sí / No)"),
            ("inbound",  "Confirmo"),
            ("outbound", "✅ ¡Reserva confirmada para el sábado!\n\n💳 Transferí la seña a:\nCBU: 0000003100012345678901\nAlias: CANCHERO.DEMO\n\nEl cajero confirmará cuando reciba el pago. ¡Hasta el sábado! 🎾"),
        ],
        "booking_id": None,
        "minutes_ago": 90,
    },
]

SEED_MARKER = BOT_DEMO_MARKER


class Command(BaseCommand):
    help = "Inserta conversaciones de prueba del bot WhatsApp en el tenant activo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            default="demo",
            help="Nombre del esquema del tenant donde insertar los datos (default: demo).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Elimina los registros de prueba anteriores antes de insertar.",
        )

    def handle(self, *args, **options):
        tenant_slug = options["tenant"]
        do_clear = options["clear"]

        try:
            with schema_context(tenant_slug):
                if do_clear:
                    # Borrado físico intencional: son datos sintéticos, no reales.
                    deleted, _ = BotConversationLog.objects.filter(
                        message__startswith=SEED_MARKER
                    ).delete()
                    self.stdout.write(
                        self.style.WARNING(f"Eliminados {deleted} registros de demo.")
                    )
                    return

                now = timezone.now()
                total = 0

                for conv in DEMO_CONVERSATIONS:
                    base_time = now - timedelta(minutes=conv["minutes_ago"])
                    phone = conv["phone"]
                    player_name = conv["player_name"]
                    booking_id = conv["booking_id"]

                    for i, (direction, message) in enumerate(conv["messages"]):
                        msg_time = base_time + timedelta(seconds=i * 30)
                        is_last = i == len(conv["messages"]) - 1

                        log = BotConversationLog.objects.create(
                            phone=phone,
                            player_name=player_name,
                            direction=direction,
                            message=f"{SEED_MARKER} {message}",
                            booking_id=booking_id if direction == "outbound" and is_last else None,
                        )
                        # auto_now_add impide pasar created_at en create();
                        # update() escribe directo en SQL sin pasar por el modelo.
                        BotConversationLog.objects.filter(pk=log.pk).update(created_at=msg_time)
                        total += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {total} mensajes insertados en {len(DEMO_CONVERSATIONS)} conversaciones "
                        f"de prueba (tenant: {tenant_slug}).\n"
                        f"   Para limpiarlos: botón 🗑️ en el visor, o --clear en este comando."
                    )
                )

        except Exception as exc:
            raise CommandError(f"Error al insertar datos de demo: {exc}") from exc
