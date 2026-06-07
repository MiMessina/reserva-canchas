# docker/frontend.Dockerfile
# Frontend — React + Vite + TypeScript + Tailwind
#
# Imagen base: node:20-alpine (minima y liviana).
# En desarrollo (docker compose up) levanta el dev server de Vite en 0.0.0.0:5173.
# El hot reload funciona gracias al volumen montado en docker-compose.yml.
#
# Para producción (post-Sprint 0 / Cliente Cero):
#   - Hacer build: RUN npm run build
#   - Servir /app/dist con Nginx (ver docker/nginx/).

FROM node:20-alpine

# Sin buffering en stdout/stderr para logs en tiempo real
ENV NODE_ENV=development

WORKDIR /app

# Instalar dependencias primero (capa cacheada si package.json no cambia)
COPY frontend/package.json frontend/package-lock.json* /app/

# --legacy-peer-deps por si hay conflictos menores de versiones entre deps del equipo
# En un repo limpio no hace falta, pero protege al equipo en el arrange inicial.
RUN npm install --legacy-peer-deps

# Copiar el resto del código fuente del frontend
COPY frontend/ /app/

# Puerto del dev server de Vite
# vite.config.ts ya tiene server.host = true (escucha en 0.0.0.0)
EXPOSE 5173

# Arranca el dev server; el volumen montado en compose permite hot reload
CMD ["npm", "run", "dev"]
