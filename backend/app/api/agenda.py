"""API da agenda (painel da recepção e testes pela página /docs).

⚠️ Etapa 2: ainda SEM login. Só rode em localhost. Autenticação entra na Etapa 7.
"""

from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

from app.core import cache
from app.agenda import servico
from app.agenda.erros import AgendaError
from app.auth.acesso import acesso, usuario_da_requisicao
from app.db import get_conn

router = APIRouter(prefix="/api", tags=["agenda"], dependencies=[Depends(acesso)])  # login obrigatório (7A)

Conn = psycopg.Connection


@router.get("/clinics", summary="Clínicas que o usuário logado pode ver (super admin: todas)")
def listar_clinicas(request: Request, conn: Conn = Depends(get_conn)):
    u = usuario_da_requisicao(request)
    return cache.memo(f"clinicas:{u.id}", 30, lambda: conn.cursor(row_factory=dict_row).execute(
        """select id, name, phone, slug, timezone, status, apresentacao from clinics
           where %s or id = any(%s) order by apresentacao desc, name""",
        (u.super_admin, list(u.clinicas)),
    ).fetchall())


@router.get("/clinics/{clinic_id}/cadastros", summary="Profissionais e procedimentos da clínica")
def cadastros(clinic_id: UUID, conn: Conn = Depends(get_conn)):
    return cache.memo(f"cadastros:{clinic_id}", 30, lambda: _cadastros(conn, clinic_id))


def _cadastros(conn, clinic_id: UUID) -> dict:
    servico.carregar_clinica(conn, clinic_id)
    cur = conn.cursor(row_factory=dict_row)
    profs = cur.execute(
        """select p.id, p.name, p.specialty, p.color,
                  coalesce(array_agg(ps.service_id) filter (where ps.service_id is not null), '{}') as service_ids
           from professionals p left join professional_services ps on ps.professional_id = p.id
           where p.clinic_id = %s and p.active group by p.id order by p.name""",
        (clinic_id,),
    ).fetchall()
    servs = cur.execute(
        """select id, name, description, duration_min, price_cents, bookable_by_ai
           from services where clinic_id = %s and active order by name""",
        (clinic_id,),
    ).fetchall()
    return {"profissionais": profs, "procedimentos": servs}


@router.get("/clinics/{clinic_id}/availability", summary="Horários livres para um procedimento")
def disponibilidade(
    clinic_id: UUID,
    service_id: UUID,
    de: date = Query(default_factory=date.today, description="Data inicial (AAAA-MM-DD)"),
    ate: date | None = Query(None, description="Data final; padrão = de + 6 dias"),
    professional_id: UUID | None = None,
    telefone: str | None = Query(None, description="Se informado, marca o dentista de referência do paciente"),
    limite: int = Query(50, ge=1, le=500),
    conn: Conn = Depends(get_conn),
):
    ate = ate or de + timedelta(days=6)
    if (ate - de).days > 62:
        raise AgendaError("DADOS_INVALIDOS", "Período máximo de consulta: 62 dias.")
    return servico.horarios_livres(conn, clinic_id, service_id, de, ate, professional_id, telefone, limite=limite)


@router.get("/clinics/{clinic_id}/appointments", summary="Consultas no período (agenda)")
def consultas(
    clinic_id: UUID,
    de: datetime,
    ate: datetime,
    professional_id: UUID | None = None,
    incluir_canceladas: bool = False,
    conn: Conn = Depends(get_conn),
):
    return servico.listar(conn, clinic_id, de, ate, professional_id, incluir_canceladas)


@router.get("/clinics/{clinic_id}/patients/{telefone}/appointments", summary="Próximas consultas de um paciente")
def consultas_paciente(clinic_id: UUID, telefone: str, conn: Conn = Depends(get_conn)):
    return servico.consultas_do_paciente(conn, clinic_id, telefone)


class NovaConsulta(BaseModel):
    telefone: str = Field(examples=["(11) 98765-4321"])
    nome: str | None = Field(None, examples=["Maria da Silva"])
    professional_id: UUID
    service_id: UUID
    inicio: datetime = Field(description="Ex.: 2026-11-24T09:00 (sem fuso = fuso da clínica)")


@router.post("/clinics/{clinic_id}/appointments", status_code=201, summary="Marcar consulta (recepção)")
def marcar(clinic_id: UUID, body: NovaConsulta, conn: Conn = Depends(get_conn)):
    return servico.marcar(
        conn, clinic_id, telefone=body.telefone, nome=body.nome, professional_id=body.professional_id,
        service_id=body.service_id, inicio=body.inicio, ator="recepcao",
    )


class NovaSerie(NovaConsulta):
    sessoes: int = Field(ge=2, le=20)
    intervalo_dias: int = Field(7, ge=1, le=60)


@router.post("/clinics/{clinic_id}/appointments/serie", status_code=201, summary="Marcar série de sessões (21B, recepção)")
def marcar_serie(clinic_id: UUID, body: NovaSerie, conn: Conn = Depends(get_conn)):
    """RN-TR-07: marca o que couber; devolve também as datas que não couberam, com o motivo."""
    return servico.marcar_serie(
        conn, clinic_id, telefone=body.telefone, nome=body.nome, professional_id=body.professional_id,
        service_id=body.service_id, inicio=body.inicio, sessoes=body.sessoes, intervalo_dias=body.intervalo_dias,
    )


class Remarcacao(BaseModel):
    novo_inicio: datetime
    professional_id: UUID | None = None
    avisar_paciente: bool = True  # D109: arrastar na agenda pode remarcar sem mandar mensagem


@router.post("/clinics/{clinic_id}/appointments/{appointment_id}/reschedule", summary="Remarcar (recepção)")
def remarcar(clinic_id: UUID, appointment_id: UUID, body: Remarcacao, conn: Conn = Depends(get_conn)):
    return servico.remarcar(
        conn, clinic_id, appointment_id=appointment_id, telefone=None, ator="recepcao",
        novo_inicio=body.novo_inicio, professional_id=body.professional_id, avisar_paciente=body.avisar_paciente,
    )


class Cancelamento(BaseModel):
    motivo: str | None = None


@router.post("/clinics/{clinic_id}/appointments/{appointment_id}/cancel", summary="Cancelar (recepção)")
def cancelar(clinic_id: UUID, appointment_id: UUID, body: Cancelamento, conn: Conn = Depends(get_conn)):
    return servico.cancelar(conn, clinic_id, appointment_id=appointment_id, telefone=None, ator="recepcao", motivo=body.motivo)


class MudancaStatus(BaseModel):
    status: Literal["confirmada", "realizada", "faltou"]


@router.post("/clinics/{clinic_id}/appointments/{appointment_id}/status", summary="Confirmar / presença / falta (recepção)")
def status(clinic_id: UUID, appointment_id: UUID, body: MudancaStatus, conn: Conn = Depends(get_conn)):
    return servico.mudar_status(conn, clinic_id, appointment_id=appointment_id, novo=body.status, ator="recepcao")


# ---------------------------------------------------------------------------
# Simulação do paciente: mesmas regras que a Ísis vai usar (telefone precisa bater)
# ---------------------------------------------------------------------------
class AcaoPaciente(BaseModel):
    telefone: str


@router.post("/clinics/{clinic_id}/simular-paciente/{appointment_id}/cancel", summary="Paciente cancela (exige o telefone dono da consulta)")
def paciente_cancela(clinic_id: UUID, appointment_id: UUID, body: AcaoPaciente, conn: Conn = Depends(get_conn)):
    return servico.cancelar(conn, clinic_id, appointment_id=appointment_id, telefone=body.telefone, ator="paciente")
