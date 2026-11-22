"""Campanhas (Etapa 14A — D69–D72). Ver: toda a equipe. Criar, disparar e cancelar: só o admin da clínica."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth.acesso import acesso, exigir_admin_clinica
from app.core import relogio
from app.db import get_conn
from app.mensagens import campanhas as C

router = APIRouter(prefix="/api/clinics/{clinic_id}/campanhas", tags=["campanhas"], dependencies=[Depends(acesso)])

PUBLICO = "^(todos|ativos12m|com_consulta)$"


class Previa(BaseModel):
    publico: str = Field(pattern=PUBLICO)


class NovaCampanha(BaseModel):
    titulo: str = Field(min_length=1, max_length=80)
    texto: str = Field(min_length=1, max_length=1000)
    publico: str = Field(pattern=PUBLICO)
    enviar_em: datetime


@router.get("", summary="Campanhas, modelos prontos e públicos")
def listar(clinic_id: UUID, conn=Depends(get_conn)):
    return {"campanhas": C.listar(conn, clinic_id), "modelos": C.MODELOS, "publicos": C.PUBLICOS}


@router.post("/previa", summary="Quantas pessoas recebem e quanto tempo leva")
def previa(clinic_id: UUID, body: Previa, conn=Depends(get_conn)):
    return C.previa(conn, clinic_id, body.publico)


@router.post("", status_code=201, summary="Criar campanha (já entra na fila para a data escolhida)")
def criar(clinic_id: UUID, body: NovaCampanha, request: Request, conn=Depends(get_conn)):
    u = exigir_admin_clinica(request, clinic_id)
    return C.criar(conn, clinic_id, titulo=body.titulo, texto=body.texto, publico=body.publico,
                   enviar_em=body.enviar_em, autor=u.id, agora=relogio.agora())


@router.post("/{campanha_id}/cancelar", summary="Cancelar (tira da fila o que ainda não saiu)")
def cancelar(clinic_id: UUID, campanha_id: UUID, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    return {"canceladas": C.cancelar(conn, clinic_id, campanha_id)}
