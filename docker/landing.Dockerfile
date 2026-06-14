# docker/landing.Dockerfile
# Landing page — HTML estático servido por Nginx Alpine
#
# Sin build step: copia el index.html directamente.
# Nginx escucha en el puerto 80 dentro del contenedor;
# docker-compose lo mapea al 3000 del host.

FROM nginx:alpine

COPY landing/ /usr/share/nginx/html

EXPOSE 80
