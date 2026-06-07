"""
WSGI config — SaaS Gestión de Canchas

Usado por gunicorn en producción y por Django en desarrollo.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
