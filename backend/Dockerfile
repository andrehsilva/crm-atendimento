# Backend da Ísis para produção (Etapa 8B, D37). Construído a partir da RAIZ do projeto:
#   docker compose build backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv

WORKDIR /app/backend

# Dependências primeiro (camada reaproveitada enquanto o uv.lock não muda)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app
COPY backend/scripts ./scripts
COPY supabase /app/supabase

# Não roda como root
RUN useradd --system --uid 10001 --home /app isis && chown -R isis /app
USER isis

ENV PATH="/app/backend/.venv/bin:$PATH" \
    ENV=prod

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=8).status == 200 else 1)"

# UM processo só (--workers 1): o envio de lembretes e o tempo real do painel rodam dentro dele (D37).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", \
     "--proxy-headers", "--forwarded-allow-ips", "*", "--timeout-graceful-shutdown", "10"]
