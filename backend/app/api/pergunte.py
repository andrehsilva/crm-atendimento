"""Etapa 30 (D117–D120): "Pergunte à assistente" — chat interno da equipe, só consulta."""

from collections.abc import Iterator
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agenda import servico
from app.agenda.erros import AgendaError
from app.auth.acesso import acesso
from app.consulta_equipe import agente
from app.db import get_conn, pool

router = APIRouter(prefix="/api/clinics/{clinic_id}", tags=["pergunte"], dependencies=[Depends(acesso)])


class Fala(BaseModel):
    autor: Literal["equipe", "assistente"]
    texto: str = Field(max_length=4000)


class Pergunta(BaseModel):
    mensagens: list[Fala] = Field(min_length=1, max_length=40)


def conexao_leitura() -> Iterator:
    """Conexão separada e limpa para os SELECTs da IA: a transação inteira fica só-leitura."""
    with pool().connection() as c:
        yield c


@router.post("/pergunte", summary="Pergunta da equipe à assistente (só leitura, só esta clínica)")
def perguntar(clinic_id: UUID, corpo: Pergunta, conn=Depends(get_conn), leitura=Depends(conexao_leitura)) -> dict:
    clinica = servico.carregar_clinica(conn, clinic_id)
    if not clinica["pergunte_liberado"]:  # D121
        raise AgendaError("SEM_ACESSO", "O \"Perguntar à assistente\" não está liberado para esta clínica.")
    if corpo.mensagens[-1].autor != "equipe":
        return {"resposta": "Escreva sua pergunta."}
    return {"resposta": agente.responder(conn, leitura, clinica, [m.model_dump() for m in corpo.mensagens])}
