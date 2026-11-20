# Painel (React) + Caddy: serve as telas, faz o HTTPS automático e repassa /api, /webhooks e /health ao backend.
# Construído a partir da RAIZ do projeto: docker compose build web
FROM node:24-alpine AS build
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM caddy:2.10-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /web/dist /srv
