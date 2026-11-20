"""WhatsApp ↔ Ísis: recebe a mensagem do webhook do WAHA, gera a resposta e envia de volta.

Roda em segundo plano (o webhook responde ao WAHA na hora, a IA leva alguns segundos).
Mensagens do mesmo chat são processadas uma de cada vez, na ordem em que chegaram.
"""

import logging
import threading
from collections import defaultdict
from uuid import UUID

from psycopg.rows import dict_row

from app.agenda.erros import AgendaError
from app.agenda.servico import carregar_clinica, obter_ou_criar_paciente
from app.canais.waha import ClienteWaha, MensagemEntrada, WahaErro
from app.db import pool
from app.eventos import avisar
from app.painel import chat

log = logging.getLogger("isis.whatsapp")

_travas: dict[str, threading.Lock] = defaultdict(threading.Lock)
_trava_geral = threading.Lock()


def _trava(chave: str) -> threading.Lock:
    with _trava_geral:
        return _travas[chave]


def instancia_por_sessao(conn, sessao: str) -> dict | None:
    return conn.cursor(row_factory=dict_row).execute(
        "select clinic_id, session, enabled from whatsapp_instances where session = %s", (sessao,)
    ).fetchone()


def instancia_da_clinica(conn, clinic_id: UUID) -> dict | None:
    return conn.cursor(row_factory=dict_row).execute(
        "select clinic_id, session, enabled, status, phone from whatsapp_instances where clinic_id = %s", (clinic_id,)
    ).fetchone()


def _registrar_falha(conn, clinic_id, conversa_id, erro: str) -> None:
    """A falha de envio aparece na conversa do painel (como mensagem de sistema), para a recepção ver."""
    conn.execute(
        """insert into messages (clinic_id, conversation_id, direction, author, content)
           values (%s, %s, 'out', 'sistema', %s)""",
        (clinic_id, conversa_id, f"⚠️ Não consegui enviar a última resposta pelo WhatsApp ({erro[:150]})."),
    )
    avisar(conn, clinic_id, "conversa", conversa_id)


def processar(msg: MensagemEntrada, cliente: ClienteWaha | None = None) -> None:
    """Chamado em segundo plano pelo webhook. Nunca levanta erro (só registra no log)."""
    with _trava(f"{msg.sessao}:{msg.chat_id}"):
        try:
            _processar(msg, cliente)
        except Exception:  # noqa: BLE001
            log.exception("falha ao processar mensagem do WhatsApp %s", msg.id_externo)


def _processar(msg: MensagemEntrada, cliente: ClienteWaha | None) -> None:
    with pool().connection() as conn:
        processar_com(conn, msg, cliente)


def processar_com(conn, msg: MensagemEntrada, cliente: ClienteWaha | None = None) -> None:
    inst = instancia_por_sessao(conn, msg.sessao)
    if not inst or not inst["enabled"]:
        log.warning("mensagem de sessão WAHA sem clínica ligada: %s", msg.sessao)
        return
    cliente = cliente or ClienteWaha()
    telefone = msg.telefone or (cliente.numero_do_lid(msg.sessao, msg.chat_id) if msg.chat_id.endswith("@lid") else None)
    if not telefone:
        log.warning("não deu para saber o telefone do remetente %s; mensagem ignorada", msg.chat_id)
        return

    clinica = carregar_clinica(conn, inst["clinic_id"])
    try:
        paciente = obter_ou_criar_paciente(conn, clinica["id"], telefone, None, origem="whatsapp")
    except AgendaError as e:
        log.warning("telefone inválido vindo do WhatsApp (%s): %s", msg.chat_id, e.mensagem)
        return
    conversa = chat._conversa(conn, clinica["id"], paciente["id"], "whatsapp")
    if conversa.get("external_chat_id") != msg.chat_id:
        conn.execute("update conversations set external_chat_id = %s where id = %s", (msg.chat_id, conversa["id"]))
        conversa["external_chat_id"] = msg.chat_id

    novas = chat.processar(conn, clinica, paciente, conversa, msg.texto, external_id=msg.id_externo)
    conn.commit()
    if len(novas) < 2:  # duplicada ou Ísis pausada: nada a enviar
        return

    resposta = novas[1]
    try:
        id_ext = cliente.enviar_texto(msg.sessao, msg.chat_id, resposta["content"])
        if id_ext:
            conn.execute("update messages set external_id = %s where id = %s", (id_ext, resposta["id"]))
    except WahaErro as e:
        log.warning("falha ao enviar resposta pelo WAHA: %s", e)
        _registrar_falha(conn, clinica["id"], conversa["id"], str(e))
    conn.commit()


def enviar_da_equipe(conn, clinic_id: UUID, conversa: dict, texto: str, cliente: ClienteWaha | None = None) -> str | None:
    """Resposta manual da recepção numa conversa de WhatsApp. Levanta AgendaError se não der para enviar
    (assim a mensagem não fica gravada como se tivesse ido)."""
    inst = instancia_da_clinica(conn, clinic_id)
    if not inst or not inst["enabled"] or not conversa.get("external_chat_id"):
        raise AgendaError("DADOS_INVALIDOS", "Esta clínica não tem WhatsApp conectado para responder esta conversa.")
    try:
        return (cliente or ClienteWaha()).enviar_texto(inst["session"], conversa["external_chat_id"], texto, simular_digitacao=False)
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", f"Não consegui enviar pelo WhatsApp: {e}") from e
