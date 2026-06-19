"""
Selectors (queries de lectura) — app tenants.

Regla: las queries de lectura van aquí, nunca inline en views ni serializers.
"""

from django.db import connection


def get_bot_mode() -> str:
    """
    Devuelve el bot_mode del tenant activo en el request actual.

    Retorna 'mock' o 'production'. django-tenants garantiza que
    connection.tenant está seteado por el middleware antes de cada request,
    por lo que el valor se lee sin restart y cambia por tenant.
    """
    return connection.tenant.bot_mode
