#!/bin/bash
# entrypoint.sh — Script de arranque del backend en Docker
#
# Ejecuta en orden:
#   1. Espera a que PostgreSQL este listo.
#   2. migrate_schemas --shared (esquema public: Tenant, Domain).
#   3. migrate_schemas (todos los tenants).
#   4. Crea el tenant de prueba 'demo' si no existe (idempotente).
#   5. Crea el superuser del Panel de System Admin si no existe (idempotente).
#   6. (Solo produccion) collectstatic — vuelca archivos estaticos al volumen compartido con Nginx.
#   7. Arranca gunicorn (produccion) o runserver (desarrollo).
#
# Variables de entorno esperadas:
#   POSTGRES_HOST, POSTGRES_PORT, DJANGO_DEBUG
#   DEMO_ADMIN_EMAIL        - email del admin del tenant demo (default: admin@demo.localhost)
#   DEMO_ADMIN_PASSWORD     - password del admin del tenant demo (SIN default; DEBE estar en .env)
#   DEMO_TENANT_DOMAIN      - dominio del tenant demo (default: demo.localhost; en prod: demo.IP.nip.io)
#   PLATFORM_ADMIN_EMAIL    - email del superuser del Panel de System Admin (default: admin@platform.localhost)
#   PLATFORM_ADMIN_PASSWORD - password del superuser del Panel de System Admin (SIN default; DEBE estar en .env)

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
  echo "[entrypoint] PostgreSQL no disponible aun, reintentando en 2s..."
  sleep 2
done
echo "[entrypoint] PostgreSQL listo."

echo "[entrypoint] Ejecutando migrate_schemas --shared (esquema public)..."
python manage.py migrate_schemas --shared --noinput

echo "[entrypoint] Ejecutando migrate_schemas (todos los tenants)..."
python manage.py migrate_schemas --noinput

echo "[entrypoint] Inicializando tenant 'demo' si no existe..."

# DEMO_ADMIN_PASSWORD es obligatoria; si no esta definida el script falla de forma explicita
# para evitar crear el tenant demo con una contrasena vacia o hardcodeada.
if [ -z "${DEMO_ADMIN_PASSWORD}" ]; then
  echo "[entrypoint] ERROR: la variable DEMO_ADMIN_PASSWORD no esta definida."
  echo "             Definila en tu .env antes de levantar el entorno."
  exit 1
fi

python manage.py init_tenant \
  --schema demo \
  --name "Complejo Demo" \
  --domain "${DEMO_TENANT_DOMAIN:-demo.localhost}" \
  --admin-email "${DEMO_ADMIN_EMAIL:-admin@demo.localhost}" \
  --admin-password "${DEMO_ADMIN_PASSWORD}"
# init_tenant es idempotente: si el tenant ya existe sale con codigo 0.
# DEMO_TENANT_DOMAIN: en desarrollo es "demo.localhost" (default).
# En produccion debe ser el subdominio real, ej: "demo.146.190.12.34.nip.io".

echo "[entrypoint] Inicializando superuser del Panel de System Admin..."

# PLATFORM_ADMIN_PASSWORD es obligatoria; si no esta definida el script falla.
if [ -z "${PLATFORM_ADMIN_PASSWORD}" ]; then
  echo "[entrypoint] ERROR: la variable PLATFORM_ADMIN_PASSWORD no esta definida."
  echo "             Definila en tu .env antes de levantar el entorno."
  exit 1
fi

python manage.py init_platform_admin \
  --email "${PLATFORM_ADMIN_EMAIL:-admin@platform.localhost}" \
  --password "${PLATFORM_ADMIN_PASSWORD}"
# init_platform_admin es idempotente: si el superuser ya existe actualiza la contrasena.

echo "[entrypoint] Sincronizando índice de emails para login centralizado..."
python manage.py sync_email_index

echo "[entrypoint] Configuracion completada."

# Arrancar el servidor
if [ "${DJANGO_DEBUG:-True}" = "True" ]; then
  echo "[entrypoint] Modo desarrollo: runserver en 0.0.0.0:8000"
  exec python manage.py runserver 0.0.0.0:8000
else
  echo "[entrypoint] Modo produccion: collectstatic + gunicorn"
  # collectstatic reune los archivos estaticos (admin, swagger) en STATIC_ROOT.
  # El volumen static_files los comparte con el contenedor Nginx.
  python manage.py collectstatic --noinput
  exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
fi
