"""Configurações da clínica (spec 07-A, Etapa 7C): Perfil, Horários, Procedimentos, Profissionais, Assistente e Usuários.

Ver: qualquer usuário da clínica. Mudar: só o administrador da clínica (ou o super admin).
Regra da spec 07: mudanças valem para NOVAS ações; consultas já marcadas não são alteradas.
"""

from datetime import datetime, time
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from psycopg import errors
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, field_validator, model_validator

from app.admin import servico as adm
from app.agenda import servico
from app.agenda.erros import AgendaError
from app.auth.acesso import acesso, exigir_admin_clinica, usuario_da_requisicao
from app.auth.usuarios import criar_ou_ligar
from app.core.telefone import TelefoneInvalido, normalizar_telefone
from app.db import get_conn
from app.eventos import avisar
from app import aparencia, segmentos

router = APIRouter(prefix="/api/clinics/{clinic_id}/config", tags=["configurações"], dependencies=[Depends(acesso)])

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
COR = r"^#[0-9a-fA-F]{6}$"


def _cur(conn):
    return conn.cursor(row_factory=dict_row)


def _admin(request: Request, clinic_id: UUID, conn) -> dict:
    exigir_admin_clinica(request, clinic_id)
    return servico.carregar_clinica(conn, clinic_id)


def c_settings(conn, clinic_id: UUID) -> dict:
    return conn.execute("select settings from clinics where id = %s", (clinic_id,)).fetchone()[0] or {}


def _settings(conn, clinic_id: UUID, novos: dict) -> None:
    conn.execute("update clinics set settings = coalesce(settings, '{}'::jsonb) || %s, updated_at = now() where id = %s",
                 (Jsonb(novos), clinic_id))


# ---------------------------------------------------------------------------
# Perfil
# ---------------------------------------------------------------------------
class Termos(BaseModel):
    """Palavras do negócio (D39). Vazio = usa o padrão do segmento."""
    profissional: str | None = Field(None, max_length=40)
    profissionais: str | None = Field(None, max_length=40)
    cliente: str | None = Field(None, max_length=40)
    clientes: str | None = Field(None, max_length=40)
    atendimento: str | None = Field(None, max_length=40)
    atendimentos: str | None = Field(None, max_length=40)
    genero: str | None = Field(None, pattern="^(f|m)$")


class Perfil(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    endereco: str | None = Field(None, max_length=300)
    telefone_urgencia: str | None = Field(None, max_length=30)
    sobre: str | None = Field(None, max_length=1500)
    segmento: str | None = Field(None, pattern="^(" + "|".join(segmentos.SEGMENTOS) + ")$")
    termos: Termos | None = None
    lembrete_discreto: bool | None = None


@router.get("/perfil", summary="Perfil da clínica")
def ver_perfil(clinic_id: UUID, conn=Depends(get_conn)):
    c = servico.carregar_clinica(conn, clinic_id)
    cfg = c["settings"] or {}
    seg = segmentos.segmento_de(cfg)
    return {"nome": c["name"], "telefone": c["phone"], "endereco": c["address"], "slug": c["slug"],
            "telefone_urgencia": cfg.get("telefone_urgencia"), "sobre": cfg.get("sobre_clinica"),
            "segmento": seg.codigo, "termos_proprios": cfg.get("termos") or {}, "termos": segmentos.termos(cfg),
            "termos_do_segmento": seg.termos, "lembrete_discreto": segmentos.lembrete_discreto(cfg)}


@router.put("/perfil", summary="Salvar perfil")
def salvar_perfil(clinic_id: UUID, body: Perfil, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    urg = None
    if body.telefone_urgencia and body.telefone_urgencia.strip():
        try:
            urg = normalizar_telefone(body.telefone_urgencia)
        except TelefoneInvalido as e:
            raise AgendaError("TELEFONE_INVALIDO", f"Telefone de urgência: {e}") from e
    conn.execute("update clinics set name = %s, address = %s, updated_at = now() where id = %s",
                 (body.nome.strip(), (body.endereco or "").strip() or None, clinic_id))
    novos: dict = {"telefone_urgencia": urg, "sobre_clinica": (body.sobre or "").strip() or None}
    if body.segmento:
        novos["segmento"] = body.segmento
    if body.termos is not None:  # só guarda o que difere do padrão do segmento
        padrao = segmentos.SEGMENTOS[body.segmento or segmentos.segmento_de(c_settings(conn, clinic_id)).codigo].termos
        novos["termos"] = {k: v.strip() for k, v in body.termos.model_dump().items()
                           if v and v.strip() and v.strip() != padrao.get(k)}
    if body.lembrete_discreto is not None:
        novos["lembrete_discreto"] = body.lembrete_discreto
    _settings(conn, clinic_id, novos)
    return ver_perfil(clinic_id, conn)


# ---------------------------------------------------------------------------
# Aparência: cor principal e logo (Etapa 9B, D40)
# ---------------------------------------------------------------------------
class Aparencia(BaseModel):
    cor: str | None = Field(None, description="#RRGGBB; vazio volta para a cor padrão da Ísis")


def _aparencia(conn, clinic_id: UUID) -> dict:
    return {"cor": aparencia.cor_da_clinica(c_settings(conn, clinic_id)),
            "cor_padrao": aparencia.COR_PADRAO, "logo_versao": aparencia.versao_da_logo(conn, clinic_id)}


@router.get("/aparencia", summary="Cor e logo da clínica")
def ver_aparencia(clinic_id: UUID, conn=Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    return _aparencia(conn, clinic_id)


@router.put("/aparencia", summary="Salvar a cor principal")
def salvar_aparencia(clinic_id: UUID, body: Aparencia, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    _settings(conn, clinic_id, {"cor": aparencia.validar_cor(body.cor) if body.cor else None})
    return _aparencia(conn, clinic_id)


@router.put("/logo", summary="Enviar a logo (o corpo é a própria imagem: PNG, JPG ou WebP até 512 KB)")
async def enviar_logo(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    dados, mime = await aparencia.ler_imagem(request)
    servico.carregar_clinica(conn, clinic_id)
    conn.execute(
        """insert into clinic_logos (clinic_id, mime, data) values (%s, %s, %s)
           on conflict (clinic_id) do update set mime = excluded.mime, data = excluded.data, updated_at = now()""",
        (clinic_id, mime, dados))
    return _aparencia(conn, clinic_id)


@router.delete("/logo", summary="Remover a logo")
def remover_logo(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    conn.execute("delete from clinic_logos where clinic_id = %s", (clinic_id,))
    return _aparencia(conn, clinic_id)


# ---------------------------------------------------------------------------
# Horários de funcionamento (+ pausas)
# ---------------------------------------------------------------------------
class Pausa(BaseModel):
    inicio: time
    fim: time


class Dia(BaseModel):
    ativo: bool
    inicio: time = time(8)
    fim: time = time(18)
    pausas: list[Pausa] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def _coerente(self):
        if self.ativo:
            if self.fim <= self.inicio:
                raise ValueError("O fim do expediente precisa ser depois do início.")
            for p in self.pausas:
                if not (self.inicio <= p.inicio < p.fim <= self.fim):
                    raise ValueError("Cada pausa precisa estar dentro do expediente e terminar depois de começar.")
        return self


@router.get("/horarios", summary="Horário de cada dia da semana")
def ver_horarios(clinic_id: UUID, conn=Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    horas = {r["weekday"]: r for r in _cur(conn).execute(
        "select weekday, enabled, start_time, end_time from clinic_hours where clinic_id = %s", (clinic_id,))}
    pausas: dict[int, list] = {}
    for r in _cur(conn).execute(
            "select weekday, start_time, end_time from clinic_breaks where clinic_id = %s order by start_time", (clinic_id,)):
        pausas.setdefault(r["weekday"], []).append({"inicio": r["start_time"], "fim": r["end_time"]})
    excecoes = [r[0] for r in conn.execute(
        """select distinct p.name from professional_hours ph join professionals p on p.id = ph.professional_id
           where ph.clinic_id = %s and p.active order by 1""", (clinic_id,))]
    return {
        "dias": [{"weekday": d, "nome": DIAS[d], "ativo": bool(horas.get(d, {}).get("enabled")),
                  "inicio": horas.get(d, {}).get("start_time") or time(8), "fim": horas.get(d, {}).get("end_time") or time(18),
                  "pausas": pausas.get(d, [])} for d in range(7)],
        "profissionais_com_horario_proprio": excecoes,
    }


def _afetadas(conn, clinica: dict, weekday: int, dia: Dia) -> list[dict]:
    """Consultas futuras nesse dia da semana que ficariam fora do novo horário (spec 07: avisar antes)."""
    tz = clinica["tz"]
    afetadas = []
    for c in _cur(conn).execute(
        """select a.id, a.starts_at, a.ends_at, p.name as paciente, pr.name as profissional
           from appointments a join patients p on p.id = a.patient_id join professionals pr on pr.id = a.professional_id
           where a.clinic_id = %s and a.status in ('agendada', 'confirmada') and a.starts_at > now()
           order by a.starts_at""", (clinica["id"],)):
        ini, fim = c["starts_at"].astimezone(tz), c["ends_at"].astimezone(tz)
        if ini.weekday() != weekday:
            continue
        fora = not dia.ativo or ini.time() < dia.inicio or fim.time() > dia.fim or any(
            ini.time() < p.fim and fim.time() > p.inicio for p in dia.pausas)
        if fora:
            afetadas.append({"id": c["id"], "quando": ini, "paciente": c["paciente"], "profissional": c["profissional"]})
    return afetadas


@router.post("/horarios/{weekday}/impacto", summary="Quais consultas marcadas ficam fora do novo horário")
def impacto_horario(clinic_id: UUID, weekday: int, body: Dia, conn=Depends(get_conn)):
    if not 0 <= weekday <= 6:
        raise AgendaError("DADOS_INVALIDOS", "Dia inválido.")
    return {"afetadas": _afetadas(conn, servico.carregar_clinica(conn, clinic_id), weekday, body)}


@router.put("/horarios/{weekday}", summary="Salvar o horário de um dia")
def salvar_horario(clinic_id: UUID, weekday: int, body: Dia, request: Request, conn=Depends(get_conn)):
    clinica = _admin(request, clinic_id, conn)
    if not 0 <= weekday <= 6:
        raise AgendaError("DADOS_INVALIDOS", "Dia inválido.")
    conn.execute(
        """insert into clinic_hours (clinic_id, weekday, enabled, start_time, end_time) values (%s, %s, %s, %s, %s)
           on conflict (clinic_id, weekday) do update
             set enabled = excluded.enabled, start_time = excluded.start_time, end_time = excluded.end_time""",
        (clinic_id, weekday, body.ativo, body.inicio, body.fim),
    )
    conn.execute("delete from clinic_breaks where clinic_id = %s and weekday = %s", (clinic_id, weekday))
    for p in body.pausas if body.ativo else []:
        conn.execute("insert into clinic_breaks (clinic_id, weekday, start_time, end_time) values (%s, %s, %s, %s)",
                     (clinic_id, weekday, p.inicio, p.fim))
    avisar(conn, clinic_id, "agenda")
    return {"ok": True, "afetadas": _afetadas(conn, clinica, weekday, body)}


# ---------------------------------------------------------------------------
# Procedimentos
# ---------------------------------------------------------------------------
class Procedimento(BaseModel):
    nome: str = Field(min_length=2, max_length=80)
    descricao: str | None = Field(None, max_length=300)
    duracao_min: int = Field(60, ge=5, le=480)
    preco_centavos: int | None = Field(None, ge=0, le=10_000_000)
    ativo: bool = True
    ia_pode_marcar: bool = True
    profissionais: list[UUID] = Field(default_factory=list)


def _ids_validos(conn, clinic_id: UUID, tabela: str, ids: list[UUID]) -> None:
    if not ids:
        return
    n = conn.execute(f"select count(*) from {tabela} where clinic_id = %s and id = any(%s)", (clinic_id, ids)).fetchone()[0]  # noqa: S608 — tabela fixa
    if n != len(set(ids)):
        raise AgendaError("DADOS_INVALIDOS", "Algum item escolhido não pertence a esta clínica.")


@router.get("/procedimentos", summary="Procedimentos (inclusive os desligados)")
def ver_procedimentos(clinic_id: UUID, conn=Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    return _cur(conn).execute(
        """select s.id, s.name as nome, s.description as descricao, s.duration_min as duracao_min,
                  s.price_cents as preco_centavos, s.active as ativo, s.bookable_by_ai as ia_pode_marcar,
                  coalesce(array_agg(ps.professional_id) filter (where ps.professional_id is not null), '{}') as profissionais,
                  (select count(*) from appointments a where a.service_id = s.id and a.status in ('agendada', 'confirmada')
                     and a.starts_at > now()) as consultas_futuras
           from services s left join professional_services ps on ps.service_id = s.id
           where s.clinic_id = %s group by s.id order by s.active desc, s.name""", (clinic_id,),
    ).fetchall()


def _gravar_procedimento(conn, clinic_id: UUID, sid: UUID | None, body: Procedimento) -> UUID:
    _ids_validos(conn, clinic_id, "professionals", body.profissionais)
    valores = (body.nome.strip(), (body.descricao or "").strip() or None, body.duracao_min, body.preco_centavos,
               body.ativo, body.ia_pode_marcar)
    try:
        with conn.transaction():
            if sid is None:
                sid = conn.execute(
                    """insert into services (clinic_id, name, description, duration_min, price_cents, active, bookable_by_ai)
                       values (%s, %s, %s, %s, %s, %s, %s) returning id""", (clinic_id, *valores)).fetchone()[0]
            elif not conn.execute(
                    """update services set name = %s, description = %s, duration_min = %s, price_cents = %s, active = %s,
                         bookable_by_ai = %s, updated_at = now() where clinic_id = %s and id = %s returning id""",
                    (*valores, clinic_id, sid)).fetchone():
                raise AgendaError("PROCEDIMENTO_NAO_ENCONTRADO", "Procedimento não encontrado.")
    except errors.UniqueViolation as e:
        raise AgendaError("DADOS_INVALIDOS", "Já existe um procedimento com esse nome.") from e
    conn.execute("delete from professional_services where clinic_id = %s and service_id = %s", (clinic_id, sid))
    for pid in set(body.profissionais):
        conn.execute("insert into professional_services (clinic_id, professional_id, service_id) values (%s, %s, %s)",
                     (clinic_id, pid, sid))
    avisar(conn, clinic_id, "agenda")
    return sid


@router.post("/procedimentos", status_code=201, summary="Novo procedimento")
def novo_procedimento(clinic_id: UUID, body: Procedimento, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    return {"id": _gravar_procedimento(conn, clinic_id, None, body)}


@router.put("/procedimentos/{service_id}", summary="Editar procedimento")
def editar_procedimento(clinic_id: UUID, service_id: UUID, body: Procedimento, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    return {"id": _gravar_procedimento(conn, clinic_id, service_id, body)}


@router.delete("/procedimentos/{service_id}", summary="Excluir (se já foi usado, só desliga)")
def excluir_procedimento(clinic_id: UUID, service_id: UUID, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    usado = conn.execute("select 1 from appointments where clinic_id = %s and service_id = %s limit 1", (clinic_id, service_id)).fetchone()
    if usado:  # o histórico de consultas precisa do procedimento: só desliga
        conn.execute("update services set active = false where clinic_id = %s and id = %s", (clinic_id, service_id))
        resultado = "desligado"
    else:
        conn.execute("delete from services where clinic_id = %s and id = %s", (clinic_id, service_id))
        resultado = "excluido"
    avisar(conn, clinic_id, "agenda")
    return {"resultado": resultado}


# ---------------------------------------------------------------------------
# Profissionais (+ férias/folgas)
# ---------------------------------------------------------------------------
class Profissional(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    especialidade: str | None = Field(None, max_length=120)
    cor: str = Field("#B85C74", pattern=COR)
    ativo: bool = True
    procedimentos: list[UUID] = Field(default_factory=list)


class Folga(BaseModel):
    inicio: datetime
    fim: datetime
    motivo: str | None = Field(None, max_length=120)

    @model_validator(mode="after")
    def _ordem(self):
        if self.fim <= self.inicio:
            raise ValueError("O fim precisa ser depois do início.")
        return self


@router.get("/profissionais", summary="Profissionais (inclusive inativos) com folgas futuras")
def ver_profissionais(clinic_id: UUID, conn=Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    profs = _cur(conn).execute(
        """select p.id, p.name as nome, p.specialty as especialidade, p.color as cor, p.active as ativo,
                  coalesce(array_agg(ps.service_id) filter (where ps.service_id is not null), '{}') as procedimentos,
                  exists(select 1 from professional_hours ph where ph.professional_id = p.id) as horario_proprio
           from professionals p left join professional_services ps on ps.professional_id = p.id
           where p.clinic_id = %s group by p.id order by p.active desc, p.name""", (clinic_id,)).fetchall()
    folgas = _cur(conn).execute(
        """select id, professional_id, starts_at as inicio, ends_at as fim, reason as motivo from schedule_blocks
           where clinic_id = %s and ends_at > now() order by starts_at""", (clinic_id,)).fetchall()
    for p in profs:
        p["folgas"] = [f for f in folgas if f["professional_id"] == p["id"]]
    return {"profissionais": profs, "folgas_da_clinica": [f for f in folgas if f["professional_id"] is None]}


def _gravar_profissional(conn, clinic_id: UUID, pid: UUID | None, body: Profissional) -> UUID:
    _ids_validos(conn, clinic_id, "services", body.procedimentos)
    valores = (body.nome.strip(), (body.especialidade or "").strip() or None, body.cor, body.ativo)
    if pid is None:
        pid = conn.execute("insert into professionals (clinic_id, name, specialty, color, active) values (%s, %s, %s, %s, %s) returning id",
                           (clinic_id, *valores)).fetchone()[0]
    elif not conn.execute(
            """update professionals set name = %s, specialty = %s, color = %s, active = %s, updated_at = now()
               where clinic_id = %s and id = %s returning id""", (*valores, clinic_id, pid)).fetchone():
        raise AgendaError("PROFISSIONAL_NAO_ENCONTRADO", "Profissional não encontrado.")
    conn.execute("delete from professional_services where clinic_id = %s and professional_id = %s", (clinic_id, pid))
    for sid in set(body.procedimentos):
        conn.execute("insert into professional_services (clinic_id, professional_id, service_id) values (%s, %s, %s)",
                     (clinic_id, pid, sid))
    avisar(conn, clinic_id, "agenda")
    return pid


@router.post("/profissionais", status_code=201, summary="Novo profissional")
def novo_profissional(clinic_id: UUID, body: Profissional, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    return {"id": _gravar_profissional(conn, clinic_id, None, body)}


@router.put("/profissionais/{professional_id}", summary="Editar profissional (desativar = some da agenda nova)")
def editar_profissional(clinic_id: UUID, professional_id: UUID, body: Profissional, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    return {"id": _gravar_profissional(conn, clinic_id, professional_id, body)}


@router.post("/profissionais/{professional_id}/folgas", status_code=201, summary="Férias/folga do profissional")
def nova_folga(clinic_id: UUID, professional_id: UUID, body: Folga, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    if not conn.execute("select 1 from professionals where clinic_id = %s and id = %s", (clinic_id, professional_id)).fetchone():
        raise AgendaError("PROFISSIONAL_NAO_ENCONTRADO", "Profissional não encontrado.")
    afetadas = conn.execute(
        """select count(*) from appointments where clinic_id = %s and professional_id = %s and status in ('agendada', 'confirmada')
           and starts_at < %s and ends_at > %s""", (clinic_id, professional_id, body.fim, body.inicio)).fetchone()[0]
    fid = conn.execute(
        "insert into schedule_blocks (clinic_id, professional_id, starts_at, ends_at, reason) values (%s, %s, %s, %s, %s) returning id",
        (clinic_id, professional_id, body.inicio, body.fim, (body.motivo or "").strip() or "Folga")).fetchone()[0]
    avisar(conn, clinic_id, "agenda")
    return {"id": fid, "consultas_no_periodo": afetadas}


@router.delete("/folgas/{block_id}", summary="Remover férias/folga")
def remover_folga(clinic_id: UUID, block_id: UUID, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    conn.execute("delete from schedule_blocks where clinic_id = %s and id = %s", (clinic_id, block_id))
    avisar(conn, clinic_id, "agenda")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Assistente (nome, tom e regras "Config" da agenda)
# ---------------------------------------------------------------------------
class Assistente(BaseModel):
    nome_assistente: str = Field(min_length=1, max_length=40)
    tratamento: str = Field(pattern="^(você|senhor\\(a\\))$")
    mostrar_precos: bool = False
    antecedencia_min_horas: float = Field(ge=0, le=168)
    horizonte_dias: int = Field(ge=1, le=365)
    aviso_cancelamento_horas: float = Field(ge=0, le=168)
    limite_consultas_futuras: int = Field(ge=1, le=10)
    lembrete_hora: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    @field_validator("nome_assistente")
    @classmethod
    def _limpo(cls, v: str) -> str:
        return v.strip()


@router.get("/assistente", summary="Nome, tom e regras da assistente")
def ver_assistente(clinic_id: UUID, conn=Depends(get_conn)):
    c = servico.carregar_clinica(conn, clinic_id)
    cfg, r = c["settings"] or {}, c["regras"]
    return {"nome_assistente": cfg.get("nome_assistente", "Ísis"), "tratamento": cfg.get("tratamento", "você"),
            "mostrar_precos": bool(cfg.get("mostrar_precos", False)),
            "antecedencia_min_horas": r.antecedencia_min_horas, "horizonte_dias": r.horizonte_dias,
            "aviso_cancelamento_horas": r.aviso_cancelamento_horas, "limite_consultas_futuras": r.limite_consultas_futuras,
            "lembrete_hora": r.lembrete_hora}


@router.put("/assistente", summary="Salvar nome, tom e regras")
def salvar_assistente(clinic_id: UUID, body: Assistente, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    _settings(conn, clinic_id, body.model_dump())
    return ver_assistente(clinic_id, conn)


# ---------------------------------------------------------------------------
# Usuários da clínica (o admin da clínica cuida da própria equipe)
# ---------------------------------------------------------------------------
class NovoUsuario(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    nome: str | None = Field(None, max_length=120)
    papel: str = Field(pattern="^(clinic_admin|reception)$")


class EdicaoUsuario(BaseModel):
    ativo: bool | None = None
    papel: str | None = Field(None, pattern="^(clinic_admin|reception)$")


@router.get("/usuarios", summary="Equipe da clínica")
def ver_usuarios(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    return adm.usuarios_da_clinica(conn, clinic_id)


@router.post("/usuarios", status_code=201, summary="Novo usuário com senha provisória")
def novo_usuario(clinic_id: UUID, body: NovoUsuario, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    uid, senha = criar_ou_ligar(conn, body.email, body.nome, clinic_id=clinic_id, papel=body.papel)
    return {"id": uid, "email": body.email.strip().lower(), "senha_provisoria": senha}


@router.patch("/usuarios/{user_id}", summary="Ativar/desativar ou mudar papel")
def editar_usuario(clinic_id: UUID, user_id: UUID, body: EdicaoUsuario, request: Request, conn=Depends(get_conn)):
    _admin(request, clinic_id, conn)
    if user_id == usuario_da_requisicao(request).id and (body.ativo is False or body.papel == "reception"):
        raise AgendaError("DADOS_INVALIDOS", "Você não pode desativar nem rebaixar o seu próprio acesso.")
    if not conn.execute(
            """update clinic_users set active = coalesce(%s, active), role = coalesce(%s, role)
               where clinic_id = %s and user_id = %s returning user_id""",
            (body.ativo, body.papel, clinic_id, user_id)).fetchone():
        raise AgendaError("DADOS_INVALIDOS", "Usuário não encontrado nesta clínica.")
    return {"ok": True}
