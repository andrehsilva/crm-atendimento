"""Ponto de entrada do backend. Rode com: uv run uvicorn app.main:app --reload"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agenda.erros import AgendaError
from app.api import agenda, auth, health, painel, webhooks
from app.config import get_settings
from app.db import fechar_pool
from app.eventos import distribuidor
from app.mensagens.agendador import agendador

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.database_url:
        distribuidor.iniciar(settings.database_url)  # tempo real: escuta avisos do banco
        if settings.mensagens_automaticas and settings.waha_api_url:
            agendador.iniciar()  # lembretes, avisos e aniversários (Etapa 6)
    yield
    agendador.parar()
    distribuidor.parar()
    fechar_pool()


app = FastAPI(title="Ísis API", version="0.3.0", lifespan=lifespan)

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
