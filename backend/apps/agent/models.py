"""
models.py — apps.agent

BotConversationLog: registro de mensajes intercambiados entre el bot WhatsApp
y los jugadores. Vive en el esquema de cada tenant (TENANT_APPS).

Reglas aplicadas:
  - Hereda TimeStampedSoftDeleteModel (ADR-011): is_active, created_at, updated_at.
  - Soft-delete obligatorio; prohibido DELETE físico (RULES.md §4).
  - Fechas en UTC (USE_TZ=True).
"""

from django.db import models

from apps.common.models import TimeStampedSoftDeleteModel

# Prefijo que identifica mensajes insertados por seed_bot_demo (datos sintéticos).
# Fuente única: views.py y seed_bot_demo.py lo importan desde aquí.
BOT_DEMO_MARKER = "[DEMO]"


class BotConversationLog(TimeStampedSoftDeleteModel):
    """
    Registro de un mensaje individual en la conversación entre el bot y un jugador.

    Cada fila representa un mensaje (entrante o saliente). El agrupado por
    conversación se resuelve en el selector/view usando el campo `phone`.
    """

    DIRECTION_INBOUND = "inbound"
    DIRECTION_OUTBOUND = "outbound"
    DIRECTION_CHOICES = [
        (DIRECTION_INBOUND, "Entrante (jugador → bot)"),
        (DIRECTION_OUTBOUND, "Saliente (bot → jugador)"),
    ]

    phone = models.CharField(
        max_length=50,
        verbose_name="Teléfono WhatsApp",
        help_text="Número del jugador en formato WhatsApp, ej: '5491112345678@c.us'.",
    )
    player_name = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Nombre del jugador",
        help_text="Nombre que el jugador proporcionó durante la conversación.",
    )
    direction = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        verbose_name="Dirección",
        help_text="'inbound' = mensaje del jugador al bot; 'outbound' = respuesta del bot.",
    )
    message = models.TextField(
        verbose_name="Mensaje",
        help_text="Texto completo del mensaje.",
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bot_logs",
        verbose_name="Reserva relacionada",
        help_text="Reserva creada o referenciada durante esta conversación (opcional).",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Registro de conversación bot"
        verbose_name_plural = "Registros de conversación bot"

    def __str__(self):
        return f"[{self.direction}] {self.phone} — {self.created_at:%Y-%m-%d %H:%M}"
