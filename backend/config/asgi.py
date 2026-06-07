"""
ASGI config — SaaS Gestión de Canchas

Preparado para futura integración de WebSockets o Channels (post-MVP).
En el MVP se usa solo el stack WSGI/gunicorn.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
