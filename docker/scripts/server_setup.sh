#!/usr/bin/env bash
# docker/scripts/server_setup.sh — Setup inicial del servidor Ubuntu 22.04 ARM64
# SaaS Gestion de Canchas (CANCHERO!)
#
# Ejecutar en el servidor como usuario ubuntu (con sudo) la primera vez:
#   curl -fsSL https://raw.githubusercontent.com/TU_ORG/TU_REPO/master/docker/scripts/server_setup.sh | bash
# o subir el script y correrlo:
#   bash docker/scripts/server_setup.sh
#
# Que hace:
#   1. apt update + upgrade
#   2. Instala Docker Engine (metodo oficial apt, no snap)
#   3. Instala Docker Compose plugin v2
#   4. Agrega al usuario ubuntu al grupo docker
#   5. Instala git
#   6. Clona el repositorio
#   7. Instrucciones finales
#
# Probado en: Ubuntu 22.04 LTS ARM64 (Oracle Cloud Ampere A1)
# NO ejecutar como root directo; el script usa sudo donde necesario.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuracion — ajustar antes de ejecutar
# ---------------------------------------------------------------------------
REPO_URL="https://github.com/MiMessina/reserva_canchas.git"
REPO_DIR="/home/ubuntu/reserva_canchas"
DEPLOY_USER="ubuntu"

echo ""
echo "=========================================="
echo " CANCHERO! — Setup del servidor"
echo " Ubuntu 22.04 ARM64 (Oracle Cloud)"
echo "=========================================="
echo ""

# ---------------------------------------------------------------------------
# 1. Actualizar el sistema
# ---------------------------------------------------------------------------
echo "[setup] Actualizando paquetes del sistema..."
sudo apt-get update -y
sudo apt-get upgrade -y
echo "[setup] Sistema actualizado."
echo ""

# ---------------------------------------------------------------------------
# 2. Instalar dependencias previas a Docker
# ---------------------------------------------------------------------------
echo "[setup] Instalando dependencias previas..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    htop \
    ufw
echo "[setup] Dependencias instaladas."
echo ""

# ---------------------------------------------------------------------------
# 3. Instalar Docker Engine (metodo oficial Docker apt repository)
#    NO usar snap: docker.io de snap puede tener versiones desactualizadas
#    y problemas de permisos en ARM64.
# ---------------------------------------------------------------------------
echo "[setup] Agregando repositorio oficial de Docker..."

# Crear directorio para keyrings
sudo install -m 0755 -d /etc/apt/keyrings

# Descargar y agregar la clave GPG oficial de Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Agregar el repositorio de Docker al sources.list
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y

echo "[setup] Instalando Docker Engine y Docker Compose plugin v2..."
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

echo "[setup] Docker instalado."
docker --version
docker compose version
echo ""

# ---------------------------------------------------------------------------
# 4. Agregar usuario ubuntu al grupo docker
#    (evita tener que usar sudo en cada comando docker)
# ---------------------------------------------------------------------------
echo "[setup] Agregando usuario '${DEPLOY_USER}' al grupo docker..."
sudo usermod -aG docker "${DEPLOY_USER}"
echo "[setup] Usuario agregado. NOTA: el cambio aplica en la proxima sesion SSH."
echo "        Para aplicarlo en la sesion actual: newgrp docker"
echo ""

# ---------------------------------------------------------------------------
# 5. Habilitar y arrancar Docker al inicio del sistema
# ---------------------------------------------------------------------------
echo "[setup] Habilitando Docker al inicio del sistema..."
sudo systemctl enable docker
sudo systemctl start docker
echo "[setup] Docker habilitado."
echo ""

# ---------------------------------------------------------------------------
# 6. Configurar firewall basico (UFW)
#    Solo abrir SSH (22) y HTTP (80). HTTPS (443) comentado: no hay SSL por ahora.
# ---------------------------------------------------------------------------
echo "[setup] Configurando firewall (UFW)..."
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
# sudo ufw allow 443/tcp  # Activar cuando se configure SSL
sudo ufw --force enable
sudo ufw status
echo "[setup] Firewall configurado."
echo ""

# ---------------------------------------------------------------------------
# 7. Clonar el repositorio
# ---------------------------------------------------------------------------
if [ -d "$REPO_DIR" ]; then
  echo "[setup] El directorio $REPO_DIR ya existe. Saltando clonado."
  echo "        Para actualizar el codigo: cd $REPO_DIR && git pull origin master"
else
  echo "[setup] Clonando repositorio en $REPO_DIR..."
  git clone "$REPO_URL" "$REPO_DIR"
  echo "[setup] Repositorio clonado."
fi

echo ""

# ---------------------------------------------------------------------------
# 8. Instrucciones finales
# ---------------------------------------------------------------------------
echo "=========================================="
echo " Setup completado."
echo "=========================================="
echo ""
echo " PROXIMOS PASOS:"
echo ""
echo " 1. Si es la primera sesion, abrir una nueva sesion SSH o ejecutar:"
echo "      newgrp docker"
echo "    (para que el usuario ubuntu reconozca el grupo docker)"
echo ""
echo " 2. Ir al directorio del repositorio:"
echo "      cd $REPO_DIR"
echo ""
echo " 3. Crear y completar el archivo de configuracion de produccion:"
echo "      cp .env.prod.example .env.prod"
echo "      nano .env.prod"
echo "    Reemplazar TODOS los <placeholder> con valores reales."
echo "    En especial: SERVER_IP, DJANGO_SECRET_KEY, POSTGRES_PASSWORD,"
echo "    DEMO_ADMIN_PASSWORD, PLATFORM_ADMIN_PASSWORD."
echo ""
echo " 4. Ejecutar el deploy:"
echo "      bash docker/scripts/deploy.sh"
echo ""
echo " 5. Verificar que todo funciona:"
echo "      curl http://\$(curl -s ifconfig.me)/api/health/"
echo ""
echo " URLs de acceso (reemplazar SERVER_IP por la IP publica del servidor):"
echo "   Landing:         http://SERVER_IP"
echo "   Tenant demo:     http://demo.SERVER_IP.nip.io"
echo "   Platform admin:  http://platform.SERVER_IP.nip.io"
echo "   Swagger API:     http://demo.SERVER_IP.nip.io/api/docs/"
echo ""
