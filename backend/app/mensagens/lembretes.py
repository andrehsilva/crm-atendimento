"""Lembretes de consulta e aniversários: quando criar, e como entender a resposta do paciente.

- RN-MS-02/03: lembrete no dia útil anterior, às 09:00; se esse horário já passou, não cria.
- RN-MS-04: "1" confirma a consulta SEM passar pela IA. "2" e "3" seguem para a Ísis, que vê o lembrete no histórico.
- RN-DP-01/03/04: aniversário 1× por ano, 29/02 → 28/02, "PARAR"/"SAIR" desliga os disparos.
"""

from datetime import date, datetime, timedelta

from psycopg.rows import dict_row

from app.agenda.erros import AgendaError
from app.eventos import avisar
from app.mensagens import regras as R
from app.painel.avisos import primeiro_nome, quando

MODELO_LEMBRETE = (
    "Olá, {nome}! Passando para lembrar da sua consulta na {clinica} 😊\n\n"
    "📅 {quando}\n🦷 {procedimento} com {profissional}\n\n"
    "Responda com o número:\n1 - Confirmar\n2 - Remarcar\n3 - Cancelar"
)
MODELO_ANIVERSARIO = (
    "Feliz aniversário, {nome}! 🎉 Toda a equipe da {clinica} deseja um novo ano cheio de saúde e muitos sorrisos. 💚"
)
LIMITE_TEXTO_ANIVERSARIO = 1000  # RN-DP-02
JANELA_RESPOSTA = timedelta(hours=72)


# ---------------------------------------------------------------------------
# Quando enviar o lembrete
# ---------------------------------------------------------------------------
def _dias_abertos(conn, clinic_id) -> set[int]:
    return {r[0] for r in conn.execute(
        "select weekday from clinic_hours where clinic_id = %s and enabled", (clinic_id,)).fetchall()}


def _feriados(conn, clinica: dict, de: date, ate: date) -> set[date]:
    """Dias em que a clínica toda está bloqueada por pelo menos 8 h (feriado, recesso)."""
    tz = clinica["tz"]
    dias: set[date] = set()
    for ini, fim in conn.execute(
        """select starts_at, ends_at from schedule_blocks
           where clinic_id = %s and professional_id is null and ends_at - starts_at >= interval '8 hours'
             and starts_at < %s and ends_at > %s""",
        (clinica["id"], datetime.combine(ate + timedelta(days=1), datetime.min.time(), tz),
         datetime.combine(de, datetime.min.time(), tz)),
    ).fetchall():
        d, ultimo = ini.astimezone(tz).date(), (fim.astimezone(tz) - timedelta(seconds=1)).date()
        while d <= ultimo:
            dias.add(d)
            d += timedelta(days=1)
    return dias


def horario_do_lembrete(conn, clinica: dict, inicio_consulta: datetime, agora: datetime) -> datetime | None:
    regras, tz = clinica["regras"], clinica["tz"]
    dia_c = inicio_consulta.astimezone(tz).date()
    dia = R.dia_do_lembrete(dia_c, _dias_abertos(conn, clinica["id"]),
                            _feriados(conn, clinica, dia_c - timedelta(days=30), dia_c), regras.lembrete_dias_uteis)
    momento = datetime.combine(dia, R.hora(regras.lembrete_hora), tzinfo=tz)
    if momento <= agora or momento >= inicio_consulta:  # RN-MS-03: já passou → a confirmação já cobre
        return None
    return momento


def agendar_lembrete(conn, clinica: dict, consulta: dict, agora: datetime) -> datetime | None:
    momento = horario_do_lembrete(conn, clinica, consulta["starts_at"], agora)
    if momento is None:
        return None
    texto = MODELO_LEMBRETE.format(
        nome=primeiro_nome(consulta["paciente"]), clinica=clinica["name"], quando=quando(consulta["starts_at"], clinica["tz"]),
        procedimento=consulta["procedimento"], profissional=consulta["profissional"],
    )
    conn.execute(
        """insert into outbound_messages (clinic_id, patient_id, appointment_id, kind, body, scheduled_for)
           values (%s, %s, %s, 'lembrete', %s, %s)""",
        (clinica["id"], consulta["patient_id"], consulta["id"], texto, momento),
    )
    return momento


# ---------------------------------------------------------------------------
# Resposta do paciente ("1", "PARAR"...) — sem IA
# ---------------------------------------------------------------------------
def _lembrete_respondido(conn, clinic_id, conversa_id, agora: datetime) -> dict | None:
    """O lembrete só vale se for a ÚLTIMA mensagem que enviamos nesta conversa (senão o "1" pode ser outra coisa)."""
    ultima = conn.execute(
        """select external_id from messages where conversation_id = %s and direction = 'out' and author <> 'sistema'
           order by created_at desc limit 1""",
        (conversa_id,),
    ).fetchone()
    if not ultima or not ultima[0]:
        return None
    return conn.cursor(row_factory=dict_row).execute(
        """select id, appointment_id, sent_at from outbound_messages
           where clinic_id = %s and kind = 'lembrete' and external_id = %s and sent_at > %s""",
        (clinic_id, ultima[0], agora - JANELA_RESPOSTA),
    ).fetchone()


def tratar_resposta(conn, clinica: dict, paciente: dict, conversa: dict, texto: str, agora: datetime) -> str | None:
    """Se a mensagem é resposta direta (confirmar lembrete ou PARAR), resolve aqui e devolve o texto de resposta.
    Devolve None quando a Ísis deve cuidar (inclusive "2 - Remarcar" e "3 - Cancelar")."""
    nome = primeiro_nome(paciente.get("name"))
    if R.pediu_para_sair(texto):
        conn.execute("update patients set optout_disparos = true where id = %s", (paciente["id"],))
        return (f"Tudo bem, {nome}. Você não vai mais receber mensagens de felicitação da {clinica['name']}. "
                "Os lembretes das suas consultas continuam chegando normalmente.")

    if R.resposta_ao_lembrete(texto) != "confirmar":
        return None
    lembrete = _lembrete_respondido(conn, clinica["id"], conversa["id"], agora)
    if not lembrete or not lembrete["appointment_id"]:
        return None
    from app.agenda import servico  # import aqui: servico também importa este módulo (via avisos)

    try:
        c = servico.detalhar(conn, clinica["id"], lembrete["appointment_id"])
        if c["status"] == "agendada":
            c = servico.mudar_status(conn, clinica["id"], appointment_id=c["id"], novo="confirmada",
                                     ator="paciente", telefone=paciente["phone"])
        elif c["status"] != "confirmada":
            return None  # cancelada/realizada: a Ísis explica
    except AgendaError:
        return None
    avisar(conn, clinica["id"], "agenda", c["id"])
    return f"Obrigada, {nome}! Sua consulta de {quando(c['starts_at'], clinica['tz'])} está confirmada ✅ Até lá!"


# ---------------------------------------------------------------------------
# Aniversário
# ---------------------------------------------------------------------------
def texto_aniversario(settings: dict | None) -> str:
    return ((settings or {}).get("aniversario_texto") or MODELO_ANIVERSARIO)[:LIMITE_TEXTO_ANIVERSARIO]


def montar_aniversario(texto: str, nome: str | None, clinica: str) -> str:
    """RN-DP-02: variáveis {nome} (primeiro nome) e {clinica}. Usa replace para não quebrar com outras chaves."""
    return texto.replace("{nome}", primeiro_nome(nome)).replace("{clinica}", clinica)


def gerar_aniversarios(conn, agora: datetime) -> int:
    """Coloca na fila a mensagem de aniversário de hoje (1× por ano por paciente, graças ao dedupe_key)."""
    from app.agenda.servico import carregar_clinica

    total = 0
    ids = [r[0] for r in conn.execute(
        "select id from clinics where status = 'ativa' and coalesce((settings->>'aniversario_ativo')::boolean, false)"
    ).fetchall()]
    for cid in ids:
        clinica = carregar_clinica(conn, cid)
        regras, local = clinica["regras"], agora.astimezone(clinica["tz"])
        if local.time() < R.hora(regras.aniversario_hora):
            continue
        hoje = local.date()
        datas = [hoje.month * 100 + hoje.day]
        if R.faz_aniversario(date(2000, 2, 29), hoje) and hoje.day == 28:
            datas.append(229)
        texto = texto_aniversario(clinica["settings"])
        for pid, nome in conn.execute(
            """select id, name from patients where clinic_id = %s and birth_date is not null and not optout_disparos
                 and (extract(month from birth_date) * 100 + extract(day from birth_date))::int = any(%s)""",
            (cid, datas),
        ).fetchall():
            r = conn.execute(
                """insert into outbound_messages (clinic_id, patient_id, kind, body, scheduled_for, dedupe_key)
                   values (%s, %s, 'aniversario', %s, %s, %s)
                   on conflict (clinic_id, kind, dedupe_key) where dedupe_key is not null do nothing returning id""",
                (cid, pid, montar_aniversario(texto, nome, clinica["name"]), agora, f"{pid}:{hoje.year}"),
            ).fetchone()
            if r:
                total += 1
        if total:
            avisar(conn, cid, "mensagens")
    return total
