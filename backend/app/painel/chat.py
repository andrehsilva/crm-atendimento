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
from app import uso_ia
from app.ia import config_da_clinica
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
              external_id: str | None = None, responder: bool = True, adiar: bool = False) -> list[dict]:
    """Grava a mensagem do paciente e, se a Ísis estiver ativa, a resposta dela. Vale para qualquer canal.

    Devolve as mensagens novas: [] se a mensagem já tinha chegado antes (duplicada),
    [paciente] se a Ísis está pausada, [paciente, isis] no caso normal.
    adiar=True (WhatsApp, D66): só grava; a resposta vem depois, junta, por `responder_pendentes`.
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

    if conversa["status"] == "humano" or not responder or adiar:  # RN-AT-06: Ísis pausada, a recepção responde
        avisar(conn, clinica["id"], "conversa", conversa["id"])
        return novas
    return novas + _responder(conn, clinica, paciente, conversa, texto.strip(), entrada["created_at"])


def pendentes(conn, conversa_id) -> list[dict]:
    """Mensagens do paciente que chegaram depois da última resposta (da Ísis, da equipe ou do sistema)."""
    return conn.cursor(row_factory=dict_row).execute(
        """select id, content, created_at from messages m
           where m.conversation_id = %s and m.author = 'paciente'
             and m.created_at > coalesce((select max(created_at) from messages o
                                         where o.conversation_id = %s and o.direction = 'out'), '-infinity')
           order by m.created_at""", (conversa_id, conversa_id)).fetchall()


def responder_pendentes(conn, clinica: dict, paciente: dict, conversa: dict) -> list[dict]:
    """D66: responde de uma vez tudo o que o paciente mandou em mensagens picadas ("oi" / "tudo bem" / "queria…")."""
    if conversa["status"] == "humano":
        return []
    lista = pendentes(conn, conversa["id"])
    if not lista:
        return []
    texto = "\n".join(m["content"].strip() for m in lista if m["content"].strip())
    return _responder(conn, clinica, paciente, conversa, texto, lista[0]["created_at"])


def _responder(conn, clinica: dict, paciente: dict, conversa: dict, texto: str, recebida_em) -> list[dict]:
    """Gera a resposta da Ísis (ou passa para a equipe, se não houver IA ou o teto tiver sido atingido)."""
    novas: list[dict] = []
    ia = config_da_clinica(conn, clinica["id"])
    teto_atingido = ia is not None and uso_ia.pausada(conn, clinica["id"])
    if ia is None or teto_atingido:
        # D46: sem IA = assistente desligada. D45: teto do mês atingido = assistente pausa e o paciente é avisado.
        # Nos dois casos a conversa vai direto para a equipe.
        if conversa["status"] != "humano":
            conn.execute("update conversations set status = 'humano' where id = %s", (conversa["id"],))
            conversa["status"] = "humano"
            crm.registrar(conn, clinica["id"], paciente["id"], "aguardando_humano", "sistema")
            if teto_atingido:
                novas.append(_gravar(conn, clinica["id"], conversa["id"], "out", "isis", isis.AVISO_EQUIPE))
        avisar(conn, clinica["id"], "conversa", conversa["id"])
        return novas

    # Grava e mostra a mensagem do paciente já; a resposta da IA vem numa transação separada
    avisar(conn, clinica["id"], "conversa", conversa["id"])
    conn.commit()

    resposta = isis.responder(conn, clinica, paciente, conversa, texto, recebida_em, ia)
    novas.append(_gravar(conn, clinica["id"], conversa["id"], "out", "isis", resposta))
    avisar(conn, clinica["id"], "conversa", conversa["id"])
    return novas


def receber(conn, slug: str, telefone: str, texto: str, responder: bool = True) -> list[dict]:
    """Chat web de teste. responder=False só grava a mensagem (usado pelo seed da demo, sem chamar a IA)."""
    clinica = clinica_por_slug(conn, slug)
    paciente = obter_ou_criar_paciente(conn, clinica["id"], telefone, None, origem="web")
    conversa = _conversa(conn, clinica["id"], paciente["id"], "web")
    return processar(conn, clinica, paciente, conversa, texto, responder=responder)
