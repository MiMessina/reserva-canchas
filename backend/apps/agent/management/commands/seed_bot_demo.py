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

from django.core.management.base import BaseCommand, CommandError
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
    # --- Conversaciones adicionales (T10-05) ---
    {
        "phone": "5491144445555@c.us",
        "player_name": "Diego Fernández",
        "messages": [
            ("inbound",  "Buenas! cuánto sale reservar una cancha de fútbol?"),
            ("outbound", "¡Hola, Diego! 👋\n\nLos precios actuales son:\n\n⚽ *Fútbol 5* — $15.000 / hora\n⚽ *Fútbol 7* — $20.000 / hora\n🎾 *Pádel* — $6.000 / 90 min\n\nLos turnos están disponibles de lunes a domingo de 8:00 a 23:00.\n\n¿Querés reservar alguno?"),
            ("inbound",  "Y hay descuento para socios?"),
            ("outbound", "Sí, los socios del complejo tienen un *10% de descuento* en todos los turnos.\n\nSi sos socio, indicámelo al reservar y el cajero aplica el descuento al confirmar la seña. 🙌\n\n¿Te anoto un turno?"),
            ("inbound",  "No por ahora, gracias"),
            ("outbound", "¡Perfecto! Cuando quieras reservar, escribime. ¡Hasta pronto! 👋"),
        ],
        "booking_id": None,
        "minutes_ago": 130,
    },
    {
        "phone": "5491133334444@c.us",
        "player_name": "Camila Torres",
        "messages": [
            ("inbound",  "Hola quiero reservar fútbol 7 para el jueves a las 21hs"),
            ("outbound", "¡Hola, Camila! 👋 El turno de *Fútbol 7 — Jueves 21:00* está disponible. 🎉\n\n¿A qué nombre reservamos?"),
            ("inbound",  "Camila Torres"),
            ("outbound", "📋 *Resumen de tu reserva:*\n\n⚽ Fútbol 7\n📅 Jueves\n🕐 21:00 – 22:00\n💰 $20.000\n👤 Camila Torres\n\n¿Confirmás? (Sí / No)"),
            ("inbound",  "Sí. Cuánto tengo que transferir de seña?"),
            ("outbound", "La seña mínima es el *50% del turno*: $10.000.\n\nPodés transferir más si querés abonar el total por adelantado. 💳\n\nDatos de pago:\nCBU: 0000003100012345678901\nAlias: CANCHERO.DEMO\nTitular: Complejo Demo\n\n✅ Tu reserva ya quedó registrada. El cajero la confirmará cuando reciba la transferencia."),
            ("inbound",  "Listo, ya transferí"),
            ("outbound", "¡Genial! En breve el cajero lo verifica y te confirma. ⚽\n\nCualquier duda, escribime. ¡Hasta el jueves!"),
        ],
        "booking_id": None,
        "minutes_ago": 200,
    },
    {
        "phone": "5491122223333@c.us",
        "player_name": "Nicolás Suárez",
        "messages": [
            ("inbound",  "Hola, quiero reservar la cancha B de fútbol 5 para hoy a las 19hs"),
            ("outbound", "¡Hola, Nicolás! Lamentablemente ese turno ya está ocupado 😅\n\n📍 *Cancha B — Fútbol 5 — Hoy 19:00* → ❌ No disponible\n\nPero tenemos libres:\n• *Cancha A* — 19:00 ✅\n• *Cancha B* — 20:00 ✅\n• *Cancha B* — 21:00 ✅\n\n¿Te queda bien alguno de esos?"),
            ("inbound",  "dale cancha A a las 19"),
            ("outbound", "Perfecto! *Cancha A — Hoy 19:00* 🎯\n\n¿A qué nombre hacemos la reserva?"),
            ("inbound",  "Nico"),
            ("outbound", "📋 *Resumen de tu reserva:*\n\n🏟️ Cancha A — Fútbol 5\n📅 Hoy\n🕐 19:00 – 20:00\n💰 $15.000\n👤 Nico\n\n¿Confirmás? (Sí / No)"),
            ("inbound",  "sí"),
            ("outbound", "✅ ¡Reserva confirmada!\n\nTe esperamos hoy a las 19:00 en Cancha A. ⚽\n\n💳 Transferí la seña a:\nCBU: 0000003100012345678901\nAlias: CANCHERO.DEMO"),
        ],
        "booking_id": None,
        "minutes_ago": 270,
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

            from apps.agent.services import seed_demo_conversations
            total = seed_demo_conversations(tenant_slug)

            if total == 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Ya existen conversaciones de demo en '{tenant_slug}'. "
                        "Usá --clear para limpiarlas antes de reinsertar."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {total} mensajes insertados en {len(DEMO_CONVERSATIONS)} conversaciones "
                        f"de prueba (tenant: {tenant_slug}).\n"
                        f"   Para limpiarlos: botón 🗑️ en el visor, o --clear en este comando."
                    )
                )

        except Exception as exc:
            raise CommandError(f"Error al insertar datos de demo: {exc}") from exc
