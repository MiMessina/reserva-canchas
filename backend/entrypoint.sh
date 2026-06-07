#!/bin/bash
# entrypoint.sh — Script de arranque del backend en Docker
#
# Ejecuta en orden:
#   1. Espera a que PostgreSQL esté listo.
#   2. migrate_schemas --shared (esquema public: Tenant, Domain).
#   3. migrate_schemas (todos los tenants existentes).
#   4. Crea el tenant de prueba 'demo' si no existe (idempotente).
#   5. Arranca gunicorn (producción) o runserver (desarrollo).
#
# Variables de entorno esperadas:
#   POSTGRES_HOST, POSTGRES_PORT, DJANGO_DEBUG
#   DEMO_ADMIN_EMAIL    — email del admin del tenant demo (default: admin@demo.localhost)
#   DEMO_ADMIN_PASSWORD — password del admin del tenant demo (SIN default; DEBE estar en .env)

set -e

echo "[entrypoint] Esperando a PostgreSQL en ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
until python -c "
import os, psycopg2, sys
try:
    psycopg2.connect(
        dbname=os.environ.get('POSTGRES_DB', 'canchas_db'),
        user=os.environ.get('POSTGRES_USER', 'canchas_user'),
        password=os.environ.get('POSTGRES_PASSWORD', 'canchas_pass'),
        host=os.environ.get('POSTGRES_HOST', 'db'),
        port=os.environ.get('POSTGRES_PORT', '5432'),
    )
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
  echo "[entrypoint] PostgreSQL no disponible aún, reintentando en 2s..."
  sleep 2
done
echo "[entrypoint] PostgreSQL listo."

echo "[entrypoint] Ejecutando migrate_schemas --shared (esquema public)..."
python manage.py migrate_schemas --shared --noinput

echo "[entrypoint] Ejecutando migrate_schemas (todos los tenants)..."
python manage.py migrate_schemas --noinput

echo "[entrypoint] Inicializando tenant 'demo' si no existe..."

# DEMO_ADMIN_PASSWORD es obligatoria; si no está definida el script falla de forma explícita
# para evitar crear el tenant demo con una contraseña vacía o hardcodeada.
if [ -z "${DEMO_ADMIN_PASSWORD}" ]; then
  echo "[entrypoint] ERROR: la variable DEMO_ADMIN_PASSWORD no está definida."
  echo "             Definila en tu .env antes de levantar el entorno."
  exit 1
fi

python manage.py init_tenant \
  --schema demo \
  --name "Complejo Demo" \
  --domain demo.localhost \
  --admin-email "${DEMO_ADMIN_EMAIL:-admin@demo.localhost}" \
  --admin-password "${DEMO_ADMIN_PASSWORD}"
# init_tenant es idempotente: si el tenant ya existe sale con código 0.
# Si falla por otro motivo (ej: DB inaccesible) el set -e detiene el script.

echo "[entrypoint] Configuración completada."

# Arrancar el servidor
if [ "${DJANGO_DEBUG:-True}" = "True" ]; then
  echo "[entrypoint] Modo desarrollo: runserver en 0.0.0.0:8000"
  exec python manage.py runserver 0.0.0.0:8000
else
  echo "[entrypoint] Modo producción: gunicorn"
  exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
fi
