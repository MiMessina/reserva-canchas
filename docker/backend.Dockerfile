# docker/backend.Dockerfile
# Backend — Django + django-tenants + DRF
#
# Imagen base: python:3.12-slim (minima, sin dev tools innecesarios).
# El entrypoint.sh ya existente en backend/ se encarga de:
#   1. Esperar a PostgreSQL (psycopg2).
#   2. migrate_schemas --shared + migrate_schemas.
#   3. Crear el tenant demo (idempotente).
#   4. Levantar runserver (DEBUG=True) o gunicorn (DEBUG=False).

FROM python:3.12-slim

# Evitar preguntas interactivas de apt
ENV DEBIAN_FRONTEND=noninteractive \
    # Python no escribe .pyc en el filesystem del contenedor
    PYTHONDONTWRITEBYTECODE=1 \
    # Sin buffering en stdout/stderr → los logs aparecen en tiempo real en docker compose logs
    PYTHONUNBUFFERED=1

# Dependencias del sistema mínimas:
#   - libpq-dev: headers de PostgreSQL necesarios para psycopg2
#   - gcc: compilador para algunos paquetes Python con extensiones C
#   (psycopg2-binary en requirements no las necesita, pero se incluyen
#    por si se cambia a psycopg2 sin binary más adelante)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias Python primero (capa cacheada si requirements.txt no cambia)
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copiar el código fuente del backend
COPY backend/ /app/

# Garantizar que entrypoint.sh sea ejecutable
RUN chmod +x /app/entrypoint.sh

# Puerto del servidor Django / gunicorn
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
