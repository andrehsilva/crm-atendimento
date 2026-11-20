"""Chat web de TESTE (D15): o paciente informa o telefone e conversa.

Etapa 4: quem responde é a Ísis (IA). Com a conversa em atendimento humano, ela fica quieta.
"""

from uuid import UUID

from psycopg.rows import dict_row

from app.agenda.erros import AgendaError
from app.agenda.servico import carregar_clinica, obter_ou_criar_paciente
from app.agent import isis
from app.eventos import avisar
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


def _gravar(conn, clinic_id, conversa_id, direcao, autor, texto) -> dict:
    m = conn.cursor(row_factory=dict_row).execute(
        """insert into messages (clinic_id, conversation_id, direction, author, content)
           values (%s, %s, %s, %s, %s) returning id, direction, author, content, created_at""",
        (clinic_id, conversa_id, direcao, autor, texto),
    ).fetchone()
    conn.execute("update conversations set last_message_at = now() where id = %s", (conversa_id,))
    return m


def receber(conn, slug: str, telefone: str, texto: str, responder: bool = True) -> list[dict]:
    """Grava a mensagem do paciente e a resposta da Ísis. Devolve as mensagens novas.

    responder=False só grava a mensagem (usado pelo seed da demo, sem chamar a IA).
    """
    clinica = clinica_por_slug(conn, slug)
    paciente = obter_ou_criar_paciente(conn, clinica["id"], telefone, None, origem="web")
    conversa = _conversa(conn, clinica["id"], paciente["id"], "web")
    novas = [_gravar(conn, clinica["id"], conversa["id"], "in", "paciente", texto)]
    crm.registrar(conn, clinica["id"], paciente["id"], "conversando", "paciente")

    if conversa["status"] == "humano" or not responder:  # RN-AT-06: Ísis pausada, a recepção responde
        avisar(conn, clinica["id"], "conversa", conversa["id"])
        return novas

    # Grava e mostra a mensagem do paciente já; a resposta da IA vem numa transação separada
    avisar(conn, clinica["id"], "conversa", conversa["id"])
    conn.commit()

    resposta = isis.responder(conn, clinica, paciente, conversa, texto.strip(), novas[0]["created_at"])
    novas.append(_gravar(conn, clinica["id"], conversa["id"], "out", "isis", resposta))
    avisar(conn, clinica["id"], "conversa", conversa["id"])
    return novas
