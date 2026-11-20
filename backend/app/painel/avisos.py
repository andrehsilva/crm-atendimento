"""Mensagens automáticas da agenda (RN-MS-01, D18): entram na fila de saída.

Nesta etapa só ficam registradas ("na fila"). O envio pelo WhatsApp entra nas Etapas 5/6.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.eventos import avisar

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

MODELOS = {
    "confirmacao": (
        "Olá, {nome}! Sua consulta na {clinica} está marcada ✅\n\n"
        "📅 {quando}\n🦷 {procedimento} com {profissional}\n📍 {endereco}\n\n"
        "Precisa remarcar ou cancelar? É só me chamar por aqui."
    ),
    "remarcacao": (
        "Olá, {nome}! Sua consulta na {clinica} foi remarcada 🔄\n\n"
        "Antes: {antes}\nAgora: 📅 {quando}\n🦷 {procedimento} com {profissional}"
    ),
    "cancelamento": (
        "Olá, {nome}. Sua consulta de {quando} com {profissional} na {clinica} foi cancelada.\n\n"
        "Quando quiser marcar uma nova data, é só me chamar. 💚"
    ),
}


def quando(dt: datetime, tz: ZoneInfo) -> str:
    local = dt.astimezone(tz)
    return f"{DIAS[local.weekday()]}, {local:%d/%m} às {local:%H:%M}"


def primeiro_nome(nome: str | None) -> str:
    return (nome or "").split(" ")[0] or "tudo bem"


def enfileirar(conn, clinica: dict, consulta: dict, tipo: str, anterior: dict | None = None) -> None:
    tz = clinica["tz"]
    texto = MODELOS[tipo].format(
        nome=primeiro_nome(consulta["paciente"]),
        clinica=clinica["name"],
        quando=quando(consulta["starts_at"], tz),
        antes=quando(anterior["starts_at"], tz) if anterior else "",
        procedimento=consulta["procedimento"],
        profissional=consulta["profissional"],
        endereco=clinica.get("address") or "",
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
    avisar(conn, clinica["id"], "mensagens", consulta["id"])
