"""Motor de agenda: o único lugar que marca, remarca e cancela consultas.

Usado pela API do painel (recepção) e, na Etapa 4, pelas ferramentas da Ísis.
Toda função recebe `clinic_id` e só enxerga dados daquela clínica (RN-MT-03).
"""

from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

import psycopg
from psycopg import errors
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.agenda import regras as R
from app.agenda.erros import AgendaError
from app.core.telefone import TelefoneInvalido, normalizar_telefone
from app.eventos import avisar
from app.painel import avisos, crm

Ator = Literal["isis", "recepcao", "paciente"]
ATIVOS = ("agendada", "confirmada")


# ---------------------------------------------------------------------------
# Leitura de cadastros
# ---------------------------------------------------------------------------
def _cur(conn: psycopg.Connection):
    return conn.cursor(row_factory=dict_row)


def carregar_clinica(conn, clinic_id: UUID) -> dict:
    c = _cur(conn).execute("select * from clinics where id = %s", (clinic_id,)).fetchone()
    if not c:
        raise AgendaError("CLINICA_NAO_ENCONTRADA", "Clínica não encontrada.")
    if c["status"] != "ativa":
        raise AgendaError("CLINICA_SUSPENSA", "Esta clínica está suspensa.")
    c["tz"] = ZoneInfo(c["timezone"])
    c["regras"] = R.RegrasClinica.de_settings(c["settings"])
    # O banco devolve datas no fuso da sessão (UTC por padrão no Supabase).
    # Trabalhamos sempre no fuso da clínica para não misturar horários.
    conn.execute("select set_config('TimeZone', %s, false)", (c["timezone"],))
    return c


def _servico(conn, clinic_id, service_id) -> dict:
    s = _cur(conn).execute("select * from services where clinic_id = %s and id = %s", (clinic_id, service_id)).fetchone()
    if not s:
        raise AgendaError("PROCEDIMENTO_NAO_ENCONTRADO", "Procedimento não encontrado.")
    if not s["active"]:
        raise AgendaError("PROCEDIMENTO_INATIVO", f"O procedimento {s['name']} não está disponível no momento.")
    return s


def _profissionais_do_servico(conn, clinic_id, service_id, professional_id=None) -> list[dict]:
    sql = """
        select p.* from professionals p
        join professional_services ps on ps.professional_id = p.id and ps.service_id = %s
        where p.clinic_id = %s and p.active
    """
    params: list = [service_id, clinic_id]
    if professional_id:
        sql += " and p.id = %s"
        params.append(professional_id)
    return _cur(conn).execute(sql + " order by p.name", params).fetchall()


def _horario(conn, clinic_id) -> tuple[dict[int, R.Faixa], list[R.Faixa]]:
    cur = _cur(conn)
    horas = {
        r["weekday"]: R.Faixa(r["weekday"], r["start_time"], r["end_time"])
        for r in cur.execute("select * from clinic_hours where clinic_id = %s and enabled", (clinic_id,))
    }
    pausas = [
        R.Faixa(r["weekday"], r["start_time"], r["end_time"])
        for r in cur.execute("select * from clinic_breaks where clinic_id = %s", (clinic_id,))
    ]
    return horas, pausas


def _excecoes(conn, clinic_id, professional_id) -> list[R.Faixa]:
    rows = _cur(conn).execute(
        "select * from professional_hours where clinic_id = %s and professional_id = %s",
        (clinic_id, professional_id),
    )
    return [R.Faixa(r["weekday"], r["start_time"], r["end_time"]) for r in rows]


def _ocupados(conn, clinic_id, professional_id, ini: datetime, fim: datetime, ignorar: UUID | None = None) -> list[R.Intervalo]:
    """Consultas ativas + bloqueios (do profissional ou da clínica toda) no período."""
    consultas = _cur(conn).execute(
        """select starts_at, ends_at from appointments
           where clinic_id = %s and professional_id = %s and status = any(%s)
             and starts_at < %s and ends_at > %s and (%s::uuid is null or id <> %s::uuid)""",
        (clinic_id, professional_id, list(ATIVOS), fim, ini, ignorar, ignorar),
    ).fetchall()
    return [(r["starts_at"], r["ends_at"]) for r in consultas] + _bloqueios(conn, clinic_id, professional_id, ini, fim)


def _bloqueios(conn, clinic_id, professional_id, ini, fim) -> list[R.Intervalo]:
    rows = _cur(conn).execute(
        """select starts_at, ends_at from schedule_blocks
           where clinic_id = %s and (professional_id is null or professional_id = %s)
             and starts_at < %s and ends_at > %s""",
        (clinic_id, professional_id, fim, ini),
    ).fetchall()
    return [(r["starts_at"], r["ends_at"]) for r in rows]


def _telefone(valor: str) -> str:
    try:
        return normalizar_telefone(valor)
    except TelefoneInvalido as e:
        raise AgendaError("TELEFONE_INVALIDO", str(e)) from e


def buscar_paciente(conn, clinic_id, telefone: str) -> dict | None:
    return _cur(conn).execute(
        "select * from patients where clinic_id = %s and phone = %s", (clinic_id, _telefone(telefone))
    ).fetchone()


def obter_ou_criar_paciente(conn, clinic_id, telefone: str, nome: str | None, origem: str = "manual") -> dict:
    tel = _telefone(telefone)
    nome = (nome or "").strip() or None
    p = buscar_paciente(conn, clinic_id, tel)
    if p is None:
        p = _cur(conn).execute(
            "insert into patients (clinic_id, phone, name, origin) values (%s, %s, %s, %s) returning *",
            (clinic_id, tel, nome, origem),
        ).fetchone()
    elif nome and not p["name"]:
        p = _cur(conn).execute("update patients set name = %s where id = %s returning *", (nome, p["id"])).fetchone()
    return p


# ---------------------------------------------------------------------------
# Horários livres
# ---------------------------------------------------------------------------
def horarios_livres(
    conn,
    clinic_id: UUID,
    service_id: UUID,
    data_inicio: date,
    data_fim: date,
    professional_id: UUID | None = None,
    telefone: str | None = None,
    agora: datetime | None = None,
    limite: int = 50,
) -> list[dict]:
    """Horários em que o procedimento pode ser marcado, já respeitando TODAS as regras de horário."""
    clinica = carregar_clinica(conn, clinic_id)
    tz, regras = clinica["tz"], clinica["regras"]
    servico = _servico(conn, clinic_id, service_id)
    profs = _profissionais_do_servico(conn, clinic_id, service_id, professional_id)
    if professional_id and not profs:
        raise AgendaError("PROFISSIONAL_NAO_FAZ", "Este profissional não realiza esse procedimento.")

    agora = agora or datetime.now(tz)
    cedo, tarde = R.limites_de_tempo(agora, regras)
    duracao = timedelta(minutes=servico["duration_min"])
    passo = timedelta(minutes=regras.passo_slot_min)
    horas, pausas = _horario(conn, clinic_id)

    preferido = None
    if telefone:
        p = buscar_paciente(conn, clinic_id, telefone)
        preferido = p and p["preferred_professional_id"]

    ini_periodo = datetime.combine(data_inicio, datetime.min.time(), tzinfo=tz)
    fim_periodo = datetime.combine(data_fim + timedelta(days=1), datetime.min.time(), tzinfo=tz)

    slots = []
    for prof in profs:
        excecoes = _excecoes(conn, clinic_id, prof["id"])
        ocupados = _ocupados(conn, clinic_id, prof["id"], ini_periodo, fim_periodo)
        dia = data_inicio
        while dia <= data_fim:
            janelas = R.subtrair(R.janelas_do_dia(dia, tz, horas, pausas, excecoes), ocupados)
            for inicio in R.fatiar(janelas, duracao, passo):
                if cedo <= inicio <= tarde:
                    slots.append(
                        {
                            "professional_id": prof["id"],
                            "profissional": prof["name"],
                            "service_id": servico["id"],
                            "procedimento": servico["name"],
                            "starts_at": inicio,
                            "ends_at": inicio + duracao,
                            "preferido": prof["id"] == preferido,
                        }
                    )
            dia += timedelta(days=1)

    slots.sort(key=lambda s: (s["starts_at"], not s["preferido"], s["profissional"]))
    return slots[:limite]


# ---------------------------------------------------------------------------
# Marcar / remarcar / cancelar / status
# ---------------------------------------------------------------------------
def _validar_horario(conn, clinica, prof_id, inicio: datetime, fim: datetime, agora: datetime):
    regras, tz = clinica["regras"], clinica["tz"]
    cedo, tarde = R.limites_de_tempo(agora, regras)
    if inicio < cedo:
        raise AgendaError(
            "ANTECEDENCIA",
            f"É preciso marcar com pelo menos {regras.antecedencia_min_horas:g} hora(s) de antecedência.",
        )
    if inicio > tarde:
        raise AgendaError("HORIZONTE", f"A agenda está aberta só para os próximos {regras.horizonte_dias} dias.")

    horas, pausas = _horario(conn, clinica["id"])
    dia = inicio.astimezone(tz).date()
    janelas = R.janelas_do_dia(dia, tz, horas, pausas, _excecoes(conn, clinica["id"], prof_id))
    janelas = R.subtrair(janelas, _bloqueios(conn, clinica["id"], prof_id, inicio, fim))
    if not R.cabe(inicio, fim, janelas):
        raise AgendaError("FORA_DO_HORARIO", "Esse horário está fora do expediente, em pausa ou bloqueado.")


def _registrar(conn, clinic_id, appointment_id, ator: str, acao: str, antes=None, depois=None, ator_id=None):
    conn.execute(
        """insert into appointment_events (clinic_id, appointment_id, actor_type, actor_id, action, before, after)
           values (%s, %s, %s, %s, %s, %s, %s)""",
        (clinic_id, appointment_id, ator, ator_id, acao, Jsonb(antes) if antes else None, Jsonb(depois) if depois else None),
    )
    avisar(conn, clinic_id, "agenda", appointment_id)


def _foto(c: dict) -> dict:
    return {"status": c["status"], "starts_at": c["starts_at"].isoformat(), "professional_id": str(c["professional_id"])}


def _como_aware(dt: datetime, tz: ZoneInfo) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=tz)


def marcar(
    conn,
    clinic_id: UUID,
    *,
    telefone: str,
    nome: str | None,
    professional_id: UUID,
    service_id: UUID,
    inicio: datetime,
    ator: Ator,
    origem: str = "manual",
    agora: datetime | None = None,
    _remarcando: UUID | None = None,
) -> dict:
    clinica = carregar_clinica(conn, clinic_id)
    tz = clinica["tz"]
    agora = agora or datetime.now(tz)
    inicio = _como_aware(inicio, tz)

    servico = _servico(conn, clinic_id, service_id)
    if ator == "isis" and not servico["bookable_by_ai"]:
        raise AgendaError("SO_HUMANO", f"{servico['name']} é marcado só pela recepção.")
    if not _profissionais_do_servico(conn, clinic_id, service_id, professional_id):
        raise AgendaError("PROFISSIONAL_NAO_FAZ", "Este profissional não realiza esse procedimento.")

    fim = inicio + timedelta(minutes=servico["duration_min"])
    _validar_horario(conn, clinica, professional_id, inicio, fim, agora)

    with conn.transaction():  # savepoint: se algo falhar, nada desta marcação fica gravado
        paciente = obter_ou_criar_paciente(conn, clinic_id, telefone, nome, origem)
        if not paciente["name"]:
            raise AgendaError("NOME_OBRIGATORIO", "Preciso do nome completo do paciente para marcar.")

        ativas = conn.execute(
            """select count(*) from appointments
               where clinic_id = %s and patient_id = %s and status = any(%s) and starts_at > %s
                 and (%s::uuid is null or id <> %s::uuid)""",
            (clinic_id, paciente["id"], list(ATIVOS), agora, _remarcando, _remarcando),
        ).fetchone()[0]
        limite = clinica["regras"].limite_consultas_futuras
        if ativas >= limite:
            raise AgendaError(
                "LIMITE_CONSULTAS", f"O paciente já tem {ativas} consulta(s) marcada(s); o limite é {limite}."
            )

        # C17 (Etapa 8): pedidos simultâneos para o mesmo dentista entram na fila, um de cada vez.
        # Sem isso, o banco às vezes detecta um impasse (deadlock) em vez de responder "horário ocupado".
        conn.execute("select pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"agenda:{professional_id}",))
        try:
            with conn.transaction():
                consulta = _cur(conn).execute(
                    """insert into appointments
                         (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at, source, rescheduled_from_id)
                       values (%s, %s, %s, %s, %s, %s, %s, %s) returning *""",
                    (
                        clinic_id, paciente["id"], professional_id, service_id, inicio, fim,
                        "paciente_botao" if ator == "paciente" else ator, _remarcando,
                    ),
                ).fetchone()
        except (errors.ExclusionViolation, errors.DeadlockDetected) as e:
            raise AgendaError("HORARIO_OCUPADO", "Esse horário acabou de ser ocupado. Escolha outro.") from e

        _registrar(conn, clinic_id, consulta["id"], ator, "marcada", depois=_foto(consulta))
        detalhe = detalhar(conn, clinic_id, consulta["id"])
        if not _remarcando:  # na remarcação, quem avisa é remarcar()
            crm.registrar(conn, clinic_id, paciente["id"], "consulta_agendada", ator, "agendado")
            avisos.enfileirar(conn, clinica, detalhe, "confirmacao", agora=agora)
    return detalhe


def _consulta_do_paciente(conn, clinic_id, appointment_id, telefone: str | None, ator: Ator) -> dict:
    c = _cur(conn).execute(
        """select a.*, p.phone from appointments a join patients p on p.id = a.patient_id
           where a.clinic_id = %s and a.id = %s for update of a""",
        (clinic_id, appointment_id),
    ).fetchone()
    if not c:
        raise AgendaError("CONSULTA_NAO_ENCONTRADA", "Consulta não encontrada.")
    # RN-AG-06: paciente/Ísis só mexem na consulta do próprio telefone. Recepção pode tudo.
    if ator != "recepcao" and (not telefone or _telefone(telefone) != c["phone"]):
        raise AgendaError("NAO_E_SUA", "Essa consulta não está no seu telefone.")
    return c


def _aviso_politica(clinica, inicio: datetime, agora: datetime) -> bool:
    return inicio - agora < timedelta(hours=clinica["regras"].aviso_cancelamento_horas)


def cancelar(conn, clinic_id: UUID, *, appointment_id: UUID, telefone: str | None, ator: Ator,
             motivo: str | None = None, agora: datetime | None = None) -> dict:
    clinica = carregar_clinica(conn, clinic_id)
    agora = agora or datetime.now(clinica["tz"])
    c = _consulta_do_paciente(conn, clinic_id, appointment_id, telefone, ator)
    if c["status"] not in ATIVOS:
        raise AgendaError("STATUS_INVALIDO", f"Essa consulta já está {c['status']}.")
    novo = _cur(conn).execute(
        "update appointments set status = 'cancelada', cancel_reason = %s where id = %s returning *",
        (motivo, appointment_id),
    ).fetchone()
    _registrar(conn, clinic_id, appointment_id, ator, "cancelada", _foto(c), _foto(novo))
    detalhe = detalhar(conn, clinic_id, appointment_id)
    crm.registrar(conn, clinic_id, c["patient_id"], "consulta_cancelada", ator,
                  crm.etapa_apos_cancelar(conn, clinic_id, c["patient_id"], agora))
    avisos.enfileirar(conn, clinica, detalhe, "cancelamento", agora=agora)
    # RN-AG-07: cancela, mas avisa a política e sinaliza a recepção
    return {"consulta": detalhe, "aviso_politica": _aviso_politica(clinica, c["starts_at"], agora)}


def remarcar(conn, clinic_id: UUID, *, appointment_id: UUID, telefone: str | None, ator: Ator,
             novo_inicio: datetime, professional_id: UUID | None = None, agora: datetime | None = None) -> dict:
    """RN-AG-09: cancela a antiga e cria a nova numa transação; se a nova falhar, a antiga continua."""
    clinica = carregar_clinica(conn, clinic_id)
    agora = agora or datetime.now(clinica["tz"])
    antiga = _consulta_do_paciente(conn, clinic_id, appointment_id, telefone, ator)
    if antiga["status"] not in ATIVOS:
        raise AgendaError("STATUS_INVALIDO", f"Essa consulta já está {antiga['status']}.")

    with conn.transaction():
        conn.execute(
            "update appointments set status = 'cancelada', cancel_reason = 'remarcada' where id = %s", (appointment_id,)
        )
        nova = marcar(
            conn, clinic_id,
            telefone=antiga["phone"], nome=None,
            professional_id=professional_id or antiga["professional_id"],
            service_id=antiga["service_id"], inicio=novo_inicio, ator=ator, agora=agora,
            _remarcando=appointment_id,
        )
        _registrar(conn, clinic_id, appointment_id, ator, "remarcada", _foto(antiga), {"nova_consulta": str(nova["id"])})
        crm.registrar(conn, clinic_id, antiga["patient_id"], "consulta_remarcada", ator, "agendado")
        avisos.enfileirar(conn, clinica, nova, "remarcacao", anterior=antiga, agora=agora)
    return {"consulta": nova, "anterior_id": appointment_id, "aviso_politica": _aviso_politica(clinica, antiga["starts_at"], agora)}


TRANSICOES = {
    "confirmada": ("agendada",),
    "realizada": ATIVOS,
    "faltou": ATIVOS,
}


def mudar_status(conn, clinic_id: UUID, *, appointment_id: UUID, novo: str, ator: Ator, telefone: str | None = None) -> dict:
    if novo not in TRANSICOES:
        raise AgendaError("DADOS_INVALIDOS", f"Status inválido: {novo}")
    if novo in ("realizada", "faltou") and ator != "recepcao":
        raise AgendaError("SO_HUMANO", "Só a recepção marca presença ou falta.")
    carregar_clinica(conn, clinic_id)
    c = _consulta_do_paciente(conn, clinic_id, appointment_id, telefone, ator)
    if c["status"] not in TRANSICOES[novo]:
        raise AgendaError("STATUS_INVALIDO", f"Não dá para mudar de {c['status']} para {novo}.")
    novo_c = _cur(conn).execute("update appointments set status = %s where id = %s returning *", (novo, appointment_id)).fetchone()
    if novo == "realizada":  # RN-AG-15: vira o dentista de referência
        conn.execute(
            "update patients set preferred_professional_id = %s where id = %s and preferred_professional_id is null",
            (c["professional_id"], c["patient_id"]),
        )
    _registrar(conn, clinic_id, appointment_id, ator, novo, _foto(c), _foto(novo_c))
    etapa = {"confirmada": "confirmado"}.get(novo)
    crm.registrar(conn, clinic_id, c["patient_id"], f"consulta_{novo}", ator, etapa)
    return detalhar(conn, clinic_id, appointment_id)


# ---------------------------------------------------------------------------
# Consultas (listagens)
# ---------------------------------------------------------------------------
_SELECT = """
    select a.id, a.status, a.source, a.starts_at, a.ends_at, a.cancel_reason, a.rescheduled_from_id,
           a.patient_id, p.name as paciente, p.phone as telefone,
           a.professional_id, pr.name as profissional, pr.color as cor,
           a.service_id, s.name as procedimento
    from appointments a
    join patients p on p.id = a.patient_id
    join professionals pr on pr.id = a.professional_id
    join services s on s.id = a.service_id
    where a.clinic_id = %s
"""


def detalhar(conn, clinic_id, appointment_id) -> dict:
    c = _cur(conn).execute(_SELECT + " and a.id = %s", (clinic_id, appointment_id)).fetchone()
    if not c:
        raise AgendaError("CONSULTA_NAO_ENCONTRADA", "Consulta não encontrada.")
    return c


def listar(conn, clinic_id, inicio: datetime, fim: datetime, professional_id: UUID | None = None,
           incluir_canceladas: bool = False) -> list[dict]:
    carregar_clinica(conn, clinic_id)
    sql = _SELECT + " and a.starts_at < %s and a.ends_at > %s"
    params: list = [clinic_id, fim, inicio]
    if professional_id:
        sql += " and a.professional_id = %s"
        params.append(professional_id)
    if not incluir_canceladas:
        sql += " and a.status <> 'cancelada'"
    return _cur(conn).execute(sql + " order by a.starts_at", params).fetchall()


def consultas_do_paciente(conn, clinic_id, telefone: str, agora: datetime | None = None) -> list[dict]:
    clinica = carregar_clinica(conn, clinic_id)
    agora = agora or datetime.now(clinica["tz"])
    return _cur(conn).execute(
        _SELECT + " and p.phone = %s and a.status = any(%s) and a.starts_at > %s order by a.starts_at",
        (clinic_id, _telefone(telefone), list(ATIVOS), agora),
    ).fetchall()
