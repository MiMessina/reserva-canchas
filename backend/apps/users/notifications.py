"""
notifications.py — Notificaciones por email del módulo users.

Funciones exportadas:
  notify_password_reset(user, reset_url) — envía el link para resetear contraseña.

Reglas:
  - Fire-and-forget: un error de email nunca interrumpe el flujo de negocio.
  - Si el usuario no tiene email, el envío se omite silenciosamente.
  - Envío sincrónico (no Celery — post-MVP).
"""

import logging

from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def notify_password_reset(user, reset_url: str) -> None:
    """
    Envía el email con el link de restablecimiento de contraseña.

    Fire-and-forget: cualquier excepción se loguea pero no se propaga.

    Parámetros:
      user      — instancia del modelo User (debe tener .email y .get_full_name()).
      reset_url — URL completa con uid y token para el frontend.
    """
    try:
        email = user.email
        if not email:
            logger.debug(
                "notify_password_reset: user_id=%s sin email — se omite.",
                user.pk,
            )
            return

        nombre = user.get_full_name() or user.email
        asunto = "Restablecer contraseña — CANCHERO!"
        cuerpo = (
            f"Hola {nombre},\n\n"
            f"Recibimos una solicitud para restablecer tu contraseña.\n\n"
            f"Hacé clic en el siguiente link para crear una nueva contraseña:\n"
            f"{reset_url}\n\n"
            f"Este link expira en 1 hora. Si no solicitaste el cambio, ignorá este mensaje.\n\n"
            f"El equipo de CANCHERO!"
        )

        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=None,  # usa DEFAULT_FROM_EMAIL de settings
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info(
            "notify_password_reset: email enviado a=%s user_id=%s",
            email,
            user.pk,
        )

    except Exception:
        logger.exception(
            "notify_password_reset: error enviando email user_id=%s",
            user.pk,
        )
