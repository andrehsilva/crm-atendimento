"""Conversa paciente ↔ Ísis, para qualquer canal (web de teste e WhatsApp).

Quem responde é a Ísis (IA). Com a conversa em atendimento humano, ela fica quieta (RN-AT-06).
"""

from uuid import UUID

from psycopg.rows import dict_row

from app.agenda.erros import AgendaError
from app.agenda.servico import carregar_clinica, obter_ou_criar_paciente
from app.agent import isis
from app.core import relogio
from app.eventos import avisar
from app.mensagens import lembretes
from app.painel import crm


def clinica_por_slug(conn, slug: str) -> dict:
    row = conn.execute("select id from clinics where slug = %s", (slug,)).fetchone()
    if not row:
        raise AgendaError("CLINICA_NAO_ENCONTRADA", "Clínica não encontrada.")
    return carregar_clinica(conn, row[0])


def _conversa(conn, clinic_id: UUID, patient_id: UUID, canal: str) -> dict:
    cur = conn.cursor(row_factory=dict_row)
    c = cur.execute(
        "select * from conversations where clinic_id = %s and patient_id = %s and channel = %s",
        (clinic_id, patient_id, canal),
    ).fetchone()
    if c is None:
        c = cur.execute(
            "insert into conversations (clinic_id, patient_id, channel) values (%s, %s, %s) returning *",
            (clinic_id, patient_id, canal),
        ).fetchone()
    return c


def iniciar(conn, slug: str, telefone: str, nome: str | None) -> dict:
    clinica = clinica_por_slug(conn, slug)
    paciente = obter_ou_criar_paciente(conn, clinica["id"], telefone, nome, origem="web")
    conversa = _conversa(conn, clinica["id"], paciente["id"], "web")
    return {"clinica": clinica["name"], "paciente": paciente, "conversa_id": conversa["id"], "historico": historico(conn, conversa["id"])}


def historico(conn, conversa_id: UUID, limite: int = 100) -> list[dict]:
    return conn.cursor(row_factory=dict_row).execute(
        """select id, direction, author, content, created_at from messages
           where conversation_id = %s order by created_at desc limit %s""",
        (conversa_id, limite),
    ).fetchall()[::-1]


def _gravar(conn, clinic_id, conversa_id, direcao, autor, texto, external_id: str | None = None) -> dict | None:
    """Grava uma mensagem. Com `external_id` repetido (webhook duplicado) não grava nada e devolve None."""
    m = conn.cursor(row_factory=dict_row).execute(
        """insert into messages (clinic_id, conversation_id, direction, author, content, external_id)
           values (%s, %s, %s, %s, %s, %s)
           on conflict (clinic_id, external_id) where external_id is not null do nothing
           returning id, direction, author, content, created_at""",
        (clinic_id, conversa_id, direcao, autor, texto, external_id),
    ).fetchone()
    if m:
        conn.execute("update conversations set last_message_at = now() where id = %s", (conversa_id,))
    return m


def processar(conn, clinica: dict, paciente: dict, conversa: dict, texto: str,
              external_id: str | None = None, responder: bool = True) -> list[dict]:
    """Grava a mensagem do paciente e, se a Ísis estiver ativa, a resposta dela. Vale para qualquer canal.

    Devolve as mensagens novas: [] se a mensagem já tinha chegado antes (duplicada),
    [paciente] se a Ísis está pausada, [paciente, isis] no caso normal.
    """
    entrada = _gravar(conn, clinica["id"], conversa["id"], "in", "paciente", texto, external_id)
    if entrada is None:
        return []
    novas = [entrada]
    crm.registrar(conn, clinica["id"], paciente["id"], "conversando", "paciente")

    # RN-MS-04 / RN-DP-04: "1" confirma o lembrete e "PARAR" desliga disparos — resolvidos no código, sem IA
    if responder and (direta := lembretes.tratar_resposta(conn, clinica, paciente, conversa, texto, relogio.agora())):
        novas.append(_gravar(conn, clinica["id"], conversa["id"], "out", "isis", direta))
        avisar(conn, clinica["id"], "conversa", conversa["id"])
        return novas

    if conversa["status"] == "humano" or not responder:  # RN-AT-06: Ísis pausada, a recepção responde
        avisar(conn, clinica["id"], "conversa", conversa["id"])
        return novas

    # Grava e mostra a mensagem do paciente já; a resposta da IA vem numa transação separada
    avisar(conn, clinica["id"], "conversa", conversa["id"])
    conn.commit()

    resposta = isis.responder(conn, clinica, paciente, conversa, texto.strip(), entrada["created_at"])
    novas.append(_gravar(conn, clinica["id"], conversa["id"], "out", "isis", resposta))
    avisar(conn, clinica["id"], "conversa", conversa["id"])
    return novas


def receber(conn, slug: str, telefone: str, texto: str, responder: bool = True) -> list[dict]:
    """Chat web de teste. responder=False só grava a mensagem (usado pelo seed da demo, sem chamar a IA)."""
    clinica = clinica_por_slug(conn, slug)
    paciente = obter_ou_criar_paciente(conn, clinica["id"], telefone, None, origem="web")
    conversa = _conversa(conn, clinica["id"], paciente["id"], "web")
    return processar(conn, clinica, paciente, conversa, texto, responder=responder)
