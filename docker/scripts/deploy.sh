#!/usr/bin/env bash
# docker/scripts/deploy.sh — Deploy de produccion (CANCHERO!)
#
# Ejecutar desde la raiz del repositorio en el servidor:
#   bash docker/scripts/deploy.sh
#
# Que hace:
#   1. git pull origin master
#   2. Verifica que .env.prod exista (no arranca sin el archivo de configuracion)
#   3. Rebuild y restart de los contenedores (--build fuerza rebuild de imagenes)
#   4. Espera a que el backend este healthy y muestra los logs de arranque
#
# Pre-requisitos:
#   - Docker instalado y el usuario en el grupo docker.
#   - .env.prod completo en la raiz del repositorio.
#   - El repositorio ya esta clonado (usar server_setup.sh para el primer setup).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo ""
echo "=========================================="
echo " CANCHERO! — Deploy de produccion"
echo "=========================================="
echo ""

# ---------------------------------------------------------------------------
# 1. git pull
# ---------------------------------------------------------------------------
echo "[deploy] Actualizando codigo desde origin/master..."
git pull origin master
echo "[deploy] Codigo actualizado."
echo ""

# ---------------------------------------------------------------------------
# 2. Verificar .env.prod
# ---------------------------------------------------------------------------
if [ ! -f ".env.prod" ]; then
  echo "[deploy] ERROR: no existe .env.prod en la raiz del repositorio."
  echo "         Copialo y completalo antes de deployar:"
  echo "           cp .env.prod.example .env.prod"
  echo "           nano .env.prod  # completar los valores reales"
  exit 1
fi

echo "[deploy] .env.prod encontrado."

# Verificar que las variables criticas no sean placeholders sin completar
if grep -q "<.*>" .env.prod; then
  echo "[deploy] ADVERTENCIA: .env.prod contiene placeholders sin reemplazar (<...>)."
  echo "         Completar todas las variables antes de continuar."
  echo "         Placeholders encontrados:"
  grep "<.*>" .env.prod | sed 's/^/   /'
  echo ""
  read -r -p "[deploy] ¿Continuar de todos modos? (s/N): " confirm
  if [[ ! "$confirm" =~ ^[sS]$ ]]; then
    echo "[deploy] Deploy cancelado."
    exit 1
  fi
fi

echo ""

# ---------------------------------------------------------------------------
# 3. Build y restart de contenedores
# ---------------------------------------------------------------------------
echo "[deploy] Levantando servicios con rebuild..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

echo ""
echo "[deploy] Contenedores levantados. Esperando a que el backend este listo..."

# Esperar hasta 120s a que el backend responda en /api/health/
# (el entrypoint.sh puede tardar en migrar y crear el tenant demo)
TIMEOUT=120
ELAPSED=0
BACKEND_HOST="localhost"

until curl -sf "http://${BACKEND_HOST}/api/health/" > /dev/null 2>&1 || [ "$ELAPSED" -ge "$TIMEOUT" ]; do
  sleep 3
  ELAPSED=$((ELAPSED + 3))
  echo "[deploy] Esperando healthcheck... (${ELAPSED}s/${TIMEOUT}s)"
done

echo ""

if curl -sf "http://${BACKEND_HOST}/api/health/" > /dev/null 2>&1; then
  echo "[deploy] Healthcheck OK — backend respondiendo en /api/health/"
else
  echo "[deploy] ADVERTENCIA: el backend no respondio en ${TIMEOUT}s."
  echo "         Revisando logs del backend:"
fi

# ---------------------------------------------------------------------------
# 4. Mostrar ultimas lineas de logs del backend (migraciones + arranque)
# ---------------------------------------------------------------------------
echo ""
echo "[deploy] Ultimas 50 lineas de log del backend:"
echo "--------------------------------------------------"
docker compose -f docker-compose.prod.yml logs --tail=50 backend

echo ""
echo "=========================================="
echo " Deploy completado"
echo "=========================================="
echo ""
echo " Estado de los contenedores:"
docker compose -f docker-compose.prod.yml ps
echo ""
echo " Comandos utiles:"
echo "   Ver logs en tiempo real:  docker compose -f docker-compose.prod.yml logs -f"
echo "   Entrar al backend:        docker compose -f docker-compose.prod.yml exec backend bash"
echo "   Reiniciar un servicio:    docker compose -f docker-compose.prod.yml restart <servicio>"
echo ""
