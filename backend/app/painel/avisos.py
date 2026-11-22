"""Mensagens automáticas da agenda (RN-MS-01, D18): entram na fila de saída.

O envio pelo WhatsApp é feito por app/mensagens/envio.py (Etapa 6). Ao marcar ou remarcar,
também fica agendado o lembrete do dia útil anterior (RN-MS-02).
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app import segmentos
from app.eventos import avisar

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

MODELOS = {
    "confirmacao": (
        "Olá, {nome}! {Sua} {atendimento} na {clinica} está marcad{o} ✅\n\n"
        "📅 {quando}\n{linha}\n📍 {endereco}\n\n"
        "Precisa remarcar ou cancelar? É só me chamar por aqui."
    ),
    "remarcacao": (
        "Olá, {nome}! {Sua} {atendimento} na {clinica} foi remarcad{o} 🔄\n\n"
        "Antes: {antes}\nAgora: 📅 {quando}\n{linha}"
    ),
    "cancelamento": (
        "Olá, {nome}. {Sua} {atendimento} de {quando} com {profissional} na {clinica} foi cancelad{o}.\n\n"
        "Quando quiser marcar uma nova data, é só me chamar. 💚"
    ),
}


def palavras(clinica: dict, consulta: dict) -> dict:
    """Palavras da clínica para as mensagens automáticas (Etapa 9): "Sua consulta" / "Seu atendimento" / "Sua sessão".
    Lembrete discreto (D41): a linha do serviço não cita o procedimento."""
    cfg = clinica.get("settings") or {}
    t = segmentos.termos(cfg)
    if segmentos.lembrete_discreto(cfg):
        linha = f"👤 com {consulta['profissional']}"
    else:
        linha = f"{segmentos.segmento_de(cfg).emoji} {consulta['procedimento']} com {consulta['profissional']}"
    return {"atendimento": t["atendimento"], "Sua": segmentos.cap(t["sua"]), "da_sua": t["da_sua"], "o": t["o"],
            "linha": linha}


def enfileirar_serie(conn, clinica: dict, consultas: list[dict], agora: datetime | None = None) -> None:
    """21B (RN-TR-07): série marcada de uma vez → UMA confirmação com todas as datas (não 4 mensagens seguidas).
    Cada sessão continua com o seu lembrete no dia anterior."""
    if not consultas:
        return
    from app.mensagens.lembretes import agendar_lembrete  # import aqui para evitar import circular

    tz = clinica["tz"]
    c0 = consultas[0]
    t = segmentos.termos(clinica.get("settings") or {})
    suas = "Suas" if t["genero"] == "f" else "Seus"
    datas = "\n".join(f"📅 {quando(c['starts_at'], tz)}" for c in consultas)
    texto = (f"Olá, {primeiro_nome(c0['paciente'])}! {suas} {len(consultas)} {t['atendimentos']} na {clinica['name']} "
             f"estão marcad{t['o']}s ✅\n\n{datas}\n{palavras(clinica, c0)['linha']}\n📍 {clinica.get('address') or ''}\n\n"
             "Precisa remarcar ou cancelar alguma? É só me chamar por aqui.")
    conn.execute(
        "insert into outbound_messages (clinic_id, patient_id, appointment_id, kind, body) values (%s, %s, %s, 'confirmacao', %s)",
        (clinica["id"], c0["patient_id"], c0["id"], texto))
    for c in consultas:
        agendar_lembrete(conn, clinica, c, agora or datetime.now(UTC))
    avisar(conn, clinica["id"], "mensagens", c0["id"])


def quando(dt: datetime, tz: ZoneInfo) -> str:
    local = dt.astimezone(tz)
    return f"{DIAS[local.weekday()]}, {local:%d/%m} às {local:%H:%M}"


def primeiro_nome(nome: str | None) -> str:
    return (nome or "").split(" ")[0] or "tudo bem"


def enfileirar(conn, clinica: dict, consulta: dict, tipo: str, anterior: dict | None = None,
               agora: datetime | None = None) -> None:
    tz = clinica["tz"]
    texto = MODELOS[tipo].format(
        nome=primeiro_nome(consulta["paciente"]),
        clinica=clinica["name"],
        quando=quando(consulta["starts_at"], tz),
        antes=quando(anterior["starts_at"], tz) if anterior else "",
        procedimento=consulta["procedimento"],
        profissional=consulta["profissional"],
        endereco=clinica.get("address") or "",
        **palavras(clinica, consulta),
    )
    # Uma consulta alterada antes do envio não deve gerar aviso velho (RN-MS-07)
    conn.execute(
        """update outbound_messages set status = 'cancelada'
           where clinic_id = %s and appointment_id = any(%s) and status = 'agendada' and kind = 'lembrete'""",
        (clinica["id"], [consulta["id"]] + ([anterior["id"]] if anterior else [])),
    )
    conn.execute(
        """insert into outbound_messages (clinic_id, patient_id, appointment_id, kind, body)
           values (%s, %s, %s, %s, %s)""",
        (clinica["id"], consulta["patient_id"], consulta["id"], tipo, texto),
    )
    if tipo in ("confirmacao", "remarcacao"):
        from app.mensagens.lembretes import agendar_lembrete  # import aqui para evitar import circular

        agendar_lembrete(conn, clinica, consulta, agora or datetime.now(UTC))
    avisar(conn, clinica["id"], "mensagens", consulta["id"])
