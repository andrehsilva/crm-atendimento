# Ísis em UM serviço só (Easypanel): o backend FastAPI também entrega o painel React compilado.
# O Easypanel cuida do domínio e do HTTPS. Porta do container: 8000.
# (A opção com dois serviços — backend + Caddy — continua em docker-compose.yml.)

# 1) Painel React compilado
FROM node:24-alpine AS painel
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2) Backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app
COPY backend/scripts ./scripts
COPY supabase /app/supabase
COPY --from=painel /web/dist /app/frontend/dist

RUN useradd --system --uid 10001 --home /app isis && chown -R isis /app
USER isis

ENV PATH="/app/backend/.venv/bin:$PATH" \
    ENV=prod \
    PAINEL_DIST=/app/frontend/dist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=8).status == 200 else 1)"

# UM processo só (--workers 1): o envio de lembretes e o tempo real do painel rodam dentro dele (D37).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", \
     "--proxy-headers", "--forwarded-allow-ips", "*", "--timeout-graceful-shutdown", "10"]
