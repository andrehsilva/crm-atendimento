"""Ponto de entrada do backend. Rode com: uv run uvicorn app.main:app --reload"""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agenda.erros import AgendaError
from app.api import admin, agenda, auth, campanhas, canais, configuracoes, health, notificacoes, observacoes, painel, pergunte, relatorios, site, tratamentos, webhooks
from app.canais.conexao import atualizar_webhooks
from app.config import get_settings
from app.core.producao import problemas
from app.db import fechar_pool
from app.eventos import distribuidor
from app.mensagens.agendador import agendador

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if erros := problemas(settings):  # Etapa 8B: em produção, configuração ruim = não sobe
        raise RuntimeError("Configuração de produção incompleta:\n- " + "\n- ".join(erros))
    if settings.database_url:
        distribuidor.iniciar(settings.database_url)  # tempo real: escuta avisos do banco
        if settings.mensagens_automaticas and settings.waha_api_url:
            agendador.iniciar()  # lembretes, avisos e aniversários (Etapa 6)
        # D86: clínicas já ligadas passam a avisar entregue/lida (sem travar a subida)
        threading.Thread(target=atualizar_webhooks, name="atualizar-webhooks", daemon=True).start()
    yield
    agendador.parar()
    distribuidor.parar()
    fechar_pool()


app = FastAPI(
    title="Ísis API", version="0.8.0", lifespan=lifespan,
    # Em produção a documentação interativa da API fica desligada (não expõe o mapa das rotas)
    docs_url=None if settings.producao else "/docs",
    redoc_url=None if settings.producao else "/redoc",
    openapi_url=None if settings.producao else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AgendaError)
async def erro_de_agenda(_: Request, e: AgendaError) -> JSONResponse:
    """Erros de regra viram resposta clara: {"codigo": "HORARIO_OCUPADO", "mensagem": "..."}."""
    return JSONResponse(status_code=e.status_http, content={"codigo": e.codigo, "mensagem": e.mensagem})


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(agenda.router)
app.include_router(painel.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
app.include_router(configuracoes.router)
app.include_router(observacoes.router)
app.include_router(site.publico)
app.include_router(site.painel)
app.include_router(campanhas.router)
app.include_router(relatorios.router)
app.include_router(canais.router)
app.include_router(notificacoes.router)
app.include_router(tratamentos.router)
app.include_router(pergunte.router)
