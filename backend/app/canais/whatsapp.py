"""WhatsApp ↔ Ísis: recebe a mensagem do webhook do WAHA, gera a resposta e envia de volta.

Roda em segundo plano (o webhook responde ao WAHA na hora, a IA leva alguns segundos).
Mensagens do mesmo chat são processadas uma de cada vez, na ordem em que chegaram.

Etapa 13:
- D66 mensagens picadas: cada mensagem é gravada na hora; a resposta espera alguns segundos de silêncio
  (WHATSAPP_ESPERA_S, no máximo WHATSAPP_ESPERA_MAX_S desde a primeira) e responde tudo de uma vez.
- D68 foto, vídeo, figurinha, documento (e áudio, até a 13B): o código responde pedindo para escrever, sem IA.
"""

import logging
import threading
import time
from collections import defaultdict
from uuid import UUID

from psycopg.rows import dict_row

from app.agenda.erros import AgendaError
from app.agenda.servico import carregar_clinica, obter_ou_criar_paciente
from app.canais.waha import ROTULO_MIDIA, ClienteWaha, MensagemEntrada, WahaErro
from app.canais.conexao import cliente_da_clinica, isis_pausada_no_whatsapp
from app.config import get_settings
from app import ia, transcricao, uso_ia
from app.db import pool
from app.eventos import avisar
from app.painel import chat

log = logging.getLogger("isis.whatsapp")

_travas: dict[str, threading.Lock] = defaultdict(threading.Lock)
_trava_geral = threading.Lock()
_agrupando: dict[str, dict] = {}  # chat → {"primeira": instante, "timer": Timer} (D66)

RESPOSTA_MIDIA = "Ainda não consigo ver imagens e arquivos por aqui. 🙏 Pode me escrever o que precisa?"
RESPOSTA_AUDIO = "Ainda não consigo ouvir áudios por aqui. 🙏 Pode me escrever o que precisa?"
RESPOSTA_AUDIO_LONGO = "Recebi seu áudio, mas ele é um pouco longo para mim. 🙏 Pode me escrever em poucas palavras o que precisa?"


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
        processar_com(conn, msg, cliente, agrupar=get_settings().whatsapp_espera_s > 0)


def _enviar(conn, sessao: str, chat_id: str, clinic_id, conversa_id, mensagens: list[dict], cliente: ClienteWaha) -> None:
    for m in mensagens:
        try:
            id_ext = cliente.enviar_texto(sessao, chat_id, m["content"])
            if id_ext:
                conn.execute("update messages set external_id = %s where id = %s", (id_ext, m["id"]))
        except WahaErro as e:
            log.warning("falha ao enviar resposta pelo WAHA: %s", e)
            _registrar_falha(conn, clinic_id, conversa_id, str(e))
    conn.commit()


# ---------------------------------------------------------------------------
# D66: mensagens picadas — espera o paciente terminar de escrever e responde tudo junto
# ---------------------------------------------------------------------------
def _agendar(chave: str, dados: tuple) -> None:
    s = get_settings()
    with _trava_geral:
        agora = time.monotonic()
        anterior = _agrupando.get(chave)
        if anterior:
            anterior["timer"].cancel()
        primeira = anterior["primeira"] if anterior else agora
        espera = max(0.0, min(s.whatsapp_espera_s, s.whatsapp_espera_max_s - (agora - primeira)))
        timer = threading.Timer(espera, _disparar, args=(chave, dados))
        timer.daemon = True
        _agrupando[chave] = {"primeira": primeira, "timer": timer}
        timer.start()


def _disparar(chave: str, dados: tuple) -> None:
    with _trava_geral:
        _agrupando.pop(chave, None)
    with _trava(chave):
        try:
            with pool().connection() as conn:
                responder_agrupadas(conn, *dados)
        except Exception:  # noqa: BLE001
            log.exception("falha ao responder mensagens agrupadas de %s", chave)


def responder_agrupadas(conn, sessao: str, chat_id: str, clinic_id, telefone: str, cliente: ClienteWaha | None = None) -> list[dict]:
    """Responde de uma vez tudo o que o paciente mandou desde a última resposta. Devolve o que foi enviado."""
    clinica = carregar_clinica(conn, clinic_id)
    paciente = obter_ou_criar_paciente(conn, clinic_id, telefone, None, origem="whatsapp")
    conversa = chat._conversa(conn, clinic_id, paciente["id"], "whatsapp")
    respostas = chat.responder_pendentes(conn, clinica, paciente, conversa)
    conn.commit()
    _enviar(conn, sessao, chat_id, clinic_id, conversa["id"], respostas, cliente or cliente_da_clinica(conn, clinic_id))
    return respostas


def _ouvir(conn, clinica: dict, conversa: dict, msg: MensagemEntrada, cliente: ClienteWaha) -> str | None:
    """Transcreve o áudio se valer a pena: a assistente está atendendo (com IA e dentro do teto) e há transcrição
    configurada. Devolve o texto, "longo" (passou do limite) ou None (não transcreveu)."""
    if conversa["status"] == "humano" or not transcricao.configurada() or not msg.midia_url:
        return None
    if (clinica.get("settings") or {}).get("aceitar_audio") is False:  # a clínica escolheu não receber áudio
        return None
    if isis_pausada_no_whatsapp(clinica):  # D79: ninguém vai ler a transcrição pela IA; não gasta
        return None
    if ia.config_da_clinica(conn, clinica["id"]) is None or uso_ia.pausada(conn, clinica["id"]):
        return None
    if msg.duracao_s and msg.duracao_s > get_settings().transcricao_max_s:
        return "longo"
    try:
        dados = cliente.baixar_midia(msg.midia_url)
    except WahaErro as e:
        log.warning("não deu para baixar o áudio: %s", e)
        return None
    return transcricao.transcrever(conn, clinica["id"], conversa["id"], dados, msg.midia_mime, msg.duracao_s)


def processar_com(conn, msg: MensagemEntrada, cliente: ClienteWaha | None = None, agrupar: bool = False) -> None:
    inst = instancia_por_sessao(conn, msg.sessao)
    if not inst or not inst["enabled"]:
        log.warning("mensagem de sessão WAHA sem clínica ligada: %s", msg.sessao)
        return
    cliente = cliente or cliente_da_clinica(conn, inst["clinic_id"])
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

    # D79: assistente pausada no WhatsApp = nada sai automático (nem resposta de áudio/foto, nem "visto"/"digitando");
    # a mensagem fica registrada e a conversa vai direto para a equipe.
    if isis_pausada_no_whatsapp(clinica):
        texto = msg.texto or f"[{ROTULO_MIDIA.get(msg.midia or 'outro', ROTULO_MIDIA['outro'])}]"
        novas = chat.processar(conn, clinica, paciente, conversa, texto, external_id=msg.id_externo, adiar=True)
        if len(novas) >= 2:  # "1" confirma o lembrete / "PARAR": resolvidos no código, seguem valendo (D79)
            conn.commit()
            _enviar(conn, msg.sessao, msg.chat_id, clinica["id"], conversa["id"], novas[1:], cliente)
            return
        if novas:
            chat.responder_pendentes(conn, clinica, paciente, conversa)  # pausada: só passa para a equipe
        conn.commit()
        return

    # D67: áudio vira texto (transcrição) e segue o caminho normal; longo demais, pede um resumo por texto
    if msg.midia == "audio" and not msg.texto:
        situacao = _ouvir(conn, clinica, conversa, msg, cliente)
        if situacao == "longo":
            novas = chat.processar(conn, clinica, paciente, conversa, "[🎤 Áudio longo]", external_id=msg.id_externo, adiar=True)
            if novas and conversa["status"] != "humano":
                resposta = chat._gravar(conn, clinica["id"], conversa["id"], "out", "isis", RESPOSTA_AUDIO_LONGO)
                conn.commit()
                _enviar(conn, msg.sessao, msg.chat_id, clinica["id"], conversa["id"], [resposta], cliente)
            conn.commit()
            return
        if situacao:
            msg.texto = f"🎤 {situacao}"
            msg.midia = None

    # D68: mídia sem legenda não vai para a IA — fica registrada na conversa e o código pede para escrever
    if msg.midia and not msg.texto:
        rotulo = f"[{ROTULO_MIDIA.get(msg.midia, ROTULO_MIDIA['outro'])}]"
        novas = chat.processar(conn, clinica, paciente, conversa, rotulo, external_id=msg.id_externo, adiar=True)
        if not novas or conversa["status"] == "humano":
            conn.commit()
            return
        texto = RESPOSTA_AUDIO if msg.midia == "audio" else RESPOSTA_MIDIA
        resposta = chat._gravar(conn, clinica["id"], conversa["id"], "out", "isis", texto)
        conn.commit()
        _enviar(conn, msg.sessao, msg.chat_id, clinica["id"], conversa["id"], [resposta], cliente)
        return

    novas = chat.processar(conn, clinica, paciente, conversa, msg.texto, external_id=msg.id_externo, adiar=agrupar)
    conn.commit()
    if len(novas) >= 2:  # resposta direta ("1" confirma o lembrete, "PARAR"…) ou resposta da Ísis sem agrupar
        _enviar(conn, msg.sessao, msg.chat_id, clinica["id"], conversa["id"], novas[1:], cliente)
        return
    if agrupar and novas and conversa["status"] != "humano":
        cliente.digitando(msg.sessao, msg.chat_id)
        _agendar(f"{msg.sessao}:{msg.chat_id}", (msg.sessao, msg.chat_id, clinica["id"], telefone, cliente))


def enviar_da_equipe(conn, clinic_id: UUID, conversa: dict, texto: str, cliente: ClienteWaha | None = None) -> str | None:
    """Resposta manual da recepção numa conversa de WhatsApp. Levanta AgendaError se não der para enviar
    (assim a mensagem não fica gravada como se tivesse ido)."""
    inst = instancia_da_clinica(conn, clinic_id)
    if not inst or not inst["enabled"] or not conversa.get("external_chat_id"):
        raise AgendaError("DADOS_INVALIDOS", "Esta clínica não tem WhatsApp conectado para responder esta conversa.")
    try:
        return (cliente or cliente_da_clinica(conn, clinic_id)).enviar_texto(inst["session"], conversa["external_chat_id"], texto, simular_digitacao=False)
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", f"Não consegui enviar pelo WhatsApp: {e}") from e


# ---------------------------------------------------------------------------
# D85: entregue / lida
# ---------------------------------------------------------------------------
ENTREGA = {2: "entregue", 3: "lida", 4: "lida"}  # 1 = chegou ao servidor do WhatsApp (já é "enviada")
_NIVEL = "case {col} when 'entregue' then 2 when 'lida' then 3 else 1 end"


def registrar_entrega(conn, sessao: str, id_externo: str, ack: int) -> bool:
    """Marca entregue/lida na conversa e na fila de mensagens automáticas. Só avança, nunca volta; e só mexe
    em mensagens da clínica dona da sessão. Devolve True se mudou algo."""
    novo = ENTREGA.get(ack)
    inst = instancia_por_sessao(conn, sessao)
    if not novo or not inst:
        return False
    cid, nivel = inst["clinic_id"], 3 if novo == "lida" else 2
    conversas = conn.execute(
        f"""update messages set entrega = %s
            where clinic_id = %s and external_id = %s and direction = 'out' and {_NIVEL.format(col='entrega')} < %s
            returning conversation_id""",
        (novo, cid, id_externo, nivel),
    ).fetchall()
    fila = conn.execute(
        f"""update outbound_messages set status = %s
            where clinic_id = %s and external_id = %s and status in ('enviada', 'entregue')
              and {_NIVEL.format(col='status')} < %s returning id""",
        (novo, cid, id_externo, nivel),
    ).fetchall()
    for (conversa_id,) in conversas:
        avisar(conn, cid, "conversa", conversa_id)
    if fila:
        avisar(conn, cid, "mensagens")
    return bool(conversas or fila)


def processar_entrega(sessao: str, id_externo: str, ack: int) -> None:
    """Chamado em segundo plano pelo webhook. Nunca levanta erro."""
    try:
        with pool().connection() as conn:
            registrar_entrega(conn, sessao, id_externo, ack)
            conn.commit()
    except Exception:  # noqa: BLE001
        log.exception("falha ao registrar entregue/lida da mensagem %s", id_externo)


def registrar_falha_envio(conn, sessao: str, id_externo: str, motivo: str) -> bool:
    """36B: a Meta avisou depois que não entregou (ex.: fora da janela de 24 h, número inválido).
    Mensagem automática vira "falhou" com o motivo; resposta na conversa ganha um aviso para a equipe."""
    inst = instancia_por_sessao(conn, sessao)
    if not inst:
        return False
    cid = inst["clinic_id"]
    fila = conn.execute(
        """update outbound_messages set status = 'falhou', error = %s
           where clinic_id = %s and external_id = %s and status in ('enviada', 'entregue') returning id""",
        (f"Meta: {motivo}"[:300], cid, id_externo)).fetchall()
    conversa = conn.execute(
        "select conversation_id from messages where clinic_id = %s and external_id = %s and direction = 'out' limit 1",
        (cid, id_externo)).fetchone()
    if conversa and not fila:
        _registrar_falha(conn, cid, conversa[0], motivo)
    if fila:
        avisar(conn, cid, "mensagens")
    return bool(fila or conversa)


def processar_falha(sessao: str, id_externo: str, motivo: str) -> None:
    """Chamado em segundo plano pelo webhook da Meta. Nunca levanta erro."""
    try:
        with pool().connection() as conn:
            registrar_falha_envio(conn, sessao, id_externo, motivo)
            conn.commit()
    except Exception:  # noqa: BLE001
        log.exception("falha ao registrar envio não entregue %s", id_externo)
