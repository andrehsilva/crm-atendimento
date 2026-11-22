"""Sino de notificações (Etapa 19, D81–D83). Toda a equipe da clínica vê; cada pessoa tem a sua leitura."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app import notificacoes as N
from app.auth.acesso import acesso, usuario_da_requisicao
from app.db import get_conn

router = APIRouter(prefix="/api/clinics/{clinic_id}/notificacoes", tags=["notificações"], dependencies=[Depends(acesso)])


@router.get("", summary="Notificações: situações abertas + acontecimentos dos últimos 7 dias")
def listar(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    return N.listar(conn, clinic_id, usuario_da_requisicao(request).id)


class Lidas(BaseModel):
    chaves: list[str] | None = Field(None, max_length=200)  # vazio/None = todas


@router.post("/lidas", summary="Marcar como lidas (uma, várias ou todas)")
def marcar(clinic_id: UUID, body: Lidas, request: Request, conn=Depends(get_conn)):
    uid = usuario_da_requisicao(request).id
    N.marcar_lidas(conn, clinic_id, uid, body.chaves or None)
    return N.listar(conn, clinic_id, uid)
