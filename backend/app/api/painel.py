"""API do painel da clínica: dashboard, CRM, clientes, mensagens, chat de teste e tempo real.

⚠️ Ainda SEM login (Etapa 7). Só rode em localhost.
"""

import asyncio
import json
from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from app.agenda import servico
from app.agenda.erros import AgendaError
from app.config import get_settings
from app.db import get_conn
from app.eventos import avisar, distribuidor
from app.painel import chat, crm

router = APIRouter(prefix="/api", tags=["painel"])
Conn = psycopg.Connection


def _cur(conn):
    return conn.cursor(row_factory=dict_row)


# ---------------------------------------------------------------------------
# Clínica
# ---------------------------------------------------------------------------
@router.get("/clinics/{clinic_id}", summary="Dados da clínica")
def clinica(clinic_id: UUID, conn: Conn = Depends(get_conn)):
    c = servico.carregar_clinica(conn, clinic_id)
    horario = _cur(conn).execute(
        "select weekday, start_time, end_time from clinic_hours where clinic_id = %s and enabled order by weekday",
        (clinic_id,),
    ).fetchall()
    pausas = _cur(conn).execute(
        "select weekday, start_time, end_time from clinic_breaks where clinic_id = %s", (clinic_id,)
    ).fetchall()
    return {
        "id": c["id"], "name": c["name"], "phone": c["phone"], "slug": c["slug"], "timezone": c["timezone"],
        "address": c["address"], "horario": horario, "pausas": pausas,
    }


# ---------------------------------------------------------------------------
# Dashboard (Q19, 1ª versão)
# ---------------------------------------------------------------------------
@router.get("/clinics/{clinic_id}/dashboard", summary="Resumo do dia")
def dashboard(clinic_id: UUID, conn: Conn = Depends(get_conn)):
    c = servico.carregar_clinica(conn, clinic_id)
    hoje = datetime.now(c["tz"]).date()
    ini = datetime.combine(hoje, datetime.min.time(), tzinfo=c["tz"])
    consultas = servico.listar(conn, clinic_id, ini, ini + timedelta(days=1))
    parado_horas = 24
    r = conn.execute(
        """select
             (select count(*) from conversations where clinic_id = %(c)s and status = 'humano'),
             (select count(*) from patients where clinic_id = %(c)s and crm_stage in ('novo_contato')
                and last_activity_at < now() - make_interval(hours => %(h)s)),
             (select count(*) from outbound_messages where clinic_id = %(c)s and status = 'agendada')""",
        {"c": clinic_id, "h": parado_horas},
    ).fetchone()
    aniversariantes = _cur(conn).execute(
        """select id, name, phone from patients where clinic_id = %s and birth_date is not null
           and extract(month from birth_date) = %s and extract(day from birth_date) = %s order by name""",
        (clinic_id, hoje.month, hoje.day),
    ).fetchall()
    return {
        "hoje": hoje,
        "consultas_hoje": consultas,
        "confirmadas": sum(1 for x in consultas if x["status"] in ("confirmada", "realizada")),
        "pendentes": sum(1 for x in consultas if x["status"] == "agendada"),
        "precisando_humano": r[0],
        "leads_parados": r[1],
        "mensagens_na_fila": r[2],
        "aniversariantes": aniversariantes,
    }


# ---------------------------------------------------------------------------
# CRM (kanban)
# ---------------------------------------------------------------------------
@router.get("/clinics/{clinic_id}/kanban", summary="Cards do CRM por coluna")
def kanban(clinic_id: UUID, conn: Conn = Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    cards = _cur(conn).execute(
        """select p.id, p.name, p.phone, p.crm_stage, p.stage_changed_at, p.last_event, p.last_activity_at, p.created_at,
                  coalesce(bool_or(cv.status = 'humano'), false) as atendimento_manual,
                  (select count(*) from appointments a where a.patient_id = p.id and a.status = 'realizada') > 0 as recorrente,
                  prox.id as consulta_id, prox.starts_at as proxima_consulta, prox.procedimento
           from patients p
           left join conversations cv on cv.patient_id = p.id
           left join lateral (
             select a.id, a.starts_at, s.name as procedimento from appointments a join services s on s.id = a.service_id
             where a.patient_id = p.id and a.status in ('agendada', 'confirmada') and a.starts_at > now()
             order by a.starts_at limit 1
           ) prox on true
           where p.clinic_id = %s
           group by p.id, prox.id, prox.starts_at, prox.procedimento
           order by p.last_activity_at desc""",
        (clinic_id,),
    ).fetchall()
    return {"colunas": list(crm.ETAPAS), "cards": cards}


class MudancaEtapa(BaseModel):
    etapa: Literal["novo_contato", "agendado", "confirmado", "cancelado"]


@router.post("/clinics/{clinic_id}/patients/{patient_id}/stage", summary="Mover card (sem mexer em consulta)")
def mover_card(clinic_id: UUID, patient_id: UUID, body: MudancaEtapa, conn: Conn = Depends(get_conn)):
    """RN-PN-05: só para movimentos simples. Agendar/confirmar/cancelar passam pelas rotas de consulta."""
    servico.carregar_clinica(conn, clinic_id)
    if not conn.execute("select 1 from patients where clinic_id = %s and id = %s", (clinic_id, patient_id)).fetchone():
        raise AgendaError("DADOS_INVALIDOS", "Paciente não encontrado.")
    crm.registrar(conn, clinic_id, patient_id, "movido_manualmente", "recepcao", body.etapa)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Leads / Clientes
# ---------------------------------------------------------------------------
@router.get("/clinics/{clinic_id}/patients", summary="Pacientes e contatos")
def pacientes(clinic_id: UUID, busca: str | None = None, conn: Conn = Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    sql = """select p.id, p.name, p.phone, p.birth_date, p.notes, p.origin, p.crm_stage, p.created_at,
                    pr.name as dentista_referencia,
                    (select max(starts_at) from appointments a where a.patient_id = p.id and a.status = 'realizada') as ultima_consulta,
                    (select min(starts_at) from appointments a where a.patient_id = p.id
                       and a.status in ('agendada','confirmada') and a.starts_at > now()) as proxima_consulta
             from patients p left join professionals pr on pr.id = p.preferred_professional_id
             where p.clinic_id = %s"""
    params: list = [clinic_id]
    if busca:
        sql += " and (p.name ilike %s or p.phone like %s)"
        params += [f"%{busca}%", f"%{''.join(ch for ch in busca if ch.isdigit()) or busca}%"]
    return _cur(conn).execute(sql + " order by p.name nulls last limit 500", params).fetchall()


class EdicaoPaciente(BaseModel):
    name: str | None = Field(None, max_length=200)
    birth_date: date | None = None
    notes: str | None = Field(None, max_length=2000)


@router.patch("/clinics/{clinic_id}/patients/{patient_id}", summary="Editar paciente")
def editar_paciente(clinic_id: UUID, patient_id: UUID, body: EdicaoPaciente, conn: Conn = Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    campos = body.model_dump(exclude_unset=True)
    if not campos:
        raise AgendaError("DADOS_INVALIDOS", "Nada para alterar.")
    sets = ", ".join(f"{k} = %s" for k in campos)  # chaves vêm do modelo, não do usuário
    p = _cur(conn).execute(
        f"update patients set {sets} where clinic_id = %s and id = %s returning id, name, phone, birth_date, notes",
        [*campos.values(), clinic_id, patient_id],
    ).fetchone()
    if not p:
        raise AgendaError("DADOS_INVALIDOS", "Paciente não encontrado.")
    avisar(conn, clinic_id, "crm", patient_id)
    return p


# ---------------------------------------------------------------------------
# Mensagens enviadas (fila de saída)
# ---------------------------------------------------------------------------
@router.get("/clinics/{clinic_id}/outbound", summary="Mensagens automáticas (fila e enviadas)")
def mensagens(clinic_id: UUID, tipo: str | None = None, status: str | None = None, limite: int = 100,
              conn: Conn = Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    sql = """select o.id, o.kind, o.channel, o.body, o.status, o.scheduled_for, o.sent_at, o.created_at, o.error,
                    p.name as paciente, p.phone as telefone, o.appointment_id
             from outbound_messages o join patients p on p.id = o.patient_id where o.clinic_id = %s"""
    params: list = [clinic_id]
    if tipo:
        sql += " and o.kind = %s"
        params.append(tipo)
    if status:
        sql += " and o.status = %s"
        params.append(status)
    return _cur(conn).execute(sql + " order by o.created_at desc limit %s", [*params, min(limite, 500)]).fetchall()


# ---------------------------------------------------------------------------
# Tempo real (SSE)
# ---------------------------------------------------------------------------
@router.get("/clinics/{clinic_id}/events", summary="Eventos em tempo real (Server-Sent Events)")
async def eventos(clinic_id: UUID, request: Request):
    chave = str(clinic_id)
    fila = distribuidor.inscrever(chave)

    async def fluxo():
        try:
            yield "retry: 3000\n\n"
            while not await request.is_disconnected():
                try:
                    ev = await asyncio.wait_for(fila.get(), timeout=15)
                    yield f"data: {json.dumps(ev)}\n\n"
                except TimeoutError:
                    yield ": ping\n\n"  # mantém a conexão viva
        finally:
            distribuidor.desinscrever(chave, fila)

    return StreamingResponse(fluxo(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------------
# Conversas e atendimento humano (RN-AT-06)
# ---------------------------------------------------------------------------
@router.get("/clinics/{clinic_id}/patients/{patient_id}/conversation", summary="Conversa do paciente (histórico)")
def conversa_do_paciente(clinic_id: UUID, patient_id: UUID, conn: Conn = Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    c = _cur(conn).execute(
        """select id, channel, status, last_message_at from conversations
           where clinic_id = %s and patient_id = %s order by last_message_at desc limit 1""",
        (clinic_id, patient_id),
    ).fetchone()
    if not c:
        return {"conversa": None, "mensagens": []}
    return {"conversa": c, "mensagens": chat.historico(conn, c["id"], limite=200)}


def _mudar_atendimento(conn, clinic_id: UUID, conversa_id: UUID, status: str, evento: str) -> dict:
    c = _cur(conn).execute(
        "update conversations set status = %s where clinic_id = %s and id = %s returning id, patient_id, status",
        (status, clinic_id, conversa_id),
    ).fetchone()
    if not c:
        raise AgendaError("DADOS_INVALIDOS", "Conversa não encontrada.")
    crm.registrar(conn, clinic_id, c["patient_id"], evento, "recepcao")
    avisar(conn, clinic_id, "conversa", conversa_id)
    return c


@router.post("/clinics/{clinic_id}/conversations/{conversa_id}/takeover", summary="Equipe assume (Ísis pausa)")
def assumir(clinic_id: UUID, conversa_id: UUID, conn: Conn = Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    return _mudar_atendimento(conn, clinic_id, conversa_id, "humano", "atendimento_manual")


@router.post("/clinics/{clinic_id}/conversations/{conversa_id}/release", summary="Devolver para a Ísis")
def devolver(clinic_id: UUID, conversa_id: UUID, conn: Conn = Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    return _mudar_atendimento(conn, clinic_id, conversa_id, "ativa", "devolvido_para_isis")


class RespostaEquipe(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


@router.post("/clinics/{clinic_id}/conversations/{conversa_id}/reply", summary="Equipe responde ao paciente")
def responder_paciente(clinic_id: UUID, conversa_id: UUID, body: RespostaEquipe, conn: Conn = Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    c = _cur(conn).execute(
        "select id, patient_id, status from conversations where clinic_id = %s and id = %s", (clinic_id, conversa_id)
    ).fetchone()
    if not c:
        raise AgendaError("DADOS_INVALIDOS", "Conversa não encontrada.")
    if c["status"] != "humano":  # responder manualmente pausa a Ísis, para as duas não falarem juntas
        conn.execute("update conversations set status = 'humano' where id = %s", (conversa_id,))
    m = _cur(conn).execute(
        """insert into messages (clinic_id, conversation_id, direction, author, content)
           values (%s, %s, 'out', 'recepcao', %s) returning id, direction, author, content, created_at""",
        (clinic_id, conversa_id, body.texto.strip()),
    ).fetchone()
    conn.execute("update conversations set last_message_at = now() where id = %s", (conversa_id,))
    crm.registrar(conn, clinic_id, c["patient_id"], "recepcao_respondeu", "recepcao")
    avisar(conn, clinic_id, "conversa", conversa_id)
    return m


@router.get("/web/{slug}/history", summary="Chat de teste: histórico (o paciente vê respostas da equipe)")
def chat_historico(slug: str, telefone: str, conn: Conn = Depends(get_conn)):
    clin = chat.clinica_por_slug(conn, slug)
    p = servico.buscar_paciente(conn, clin["id"], telefone)
    if not p:
        return []
    c = conn.execute("select id from conversations where clinic_id = %s and patient_id = %s and channel = 'web'",
                     (clin["id"], p["id"])).fetchone()
    return chat.historico(conn, c[0]) if c else []


# ---------------------------------------------------------------------------
# Chat web de teste (D15)
# ---------------------------------------------------------------------------
class InicioChat(BaseModel):
    telefone: str = Field(max_length=30)
    nome: str | None = Field(None, max_length=200)


class MensagemChat(BaseModel):
    telefone: str = Field(max_length=30)
    texto: str = Field(min_length=1, max_length=2000)


@router.post("/web/{slug}/session", summary="Chat de teste: entrar com o telefone")
def chat_inicio(slug: str, body: InicioChat, conn: Conn = Depends(get_conn)):
    return chat.iniciar(conn, slug, body.telefone, body.nome)


@router.post("/web/{slug}/messages", summary="Chat de teste: enviar mensagem")
def chat_mensagem(slug: str, body: MensagemChat, conn: Conn = Depends(get_conn)):
    return chat.receber(conn, slug, body.telefone, body.texto)


# ---------------------------------------------------------------------------
# Desenvolvimento
# ---------------------------------------------------------------------------
@router.post("/dev/reset-demo", summary="Recria a clínica demo (só com ENV=dev)")
def reset_demo(conn: Conn = Depends(get_conn)):
    if get_settings().env != "dev":
        raise AgendaError("SO_HUMANO", "Disponível só em desenvolvimento.")
    from app.demo import criar_demo

    clinic_id = criar_demo(conn, reset=True)
    return {"clinic_id": clinic_id}
