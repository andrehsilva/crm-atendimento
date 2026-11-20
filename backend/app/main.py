"""Ponto de entrada do backend. Rode com: uv run uvicorn app.main:app --reload"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agenda.erros import AgendaError
from app.api import agenda, health, painel
from app.config import get_settings
from app.db import fechar_pool
from app.eventos import distribuidor

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.database_url:
        distribuidor.iniciar(settings.database_url)  # tempo real: escuta avisos do banco
    yield
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
app.include_router(agenda.router)
app.include_router(painel.router)
