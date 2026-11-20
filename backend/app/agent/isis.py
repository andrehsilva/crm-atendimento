"""A Ísis: monta o agente (Agno + o modelo de IA da clínica — Etapa 10A), envia o histórico e devolve a resposta.

Falhas do modelo nunca derrubam o atendimento: o paciente recebe uma mensagem padrão e,
se falhar duas vezes seguidas, a conversa vai para a equipe (RN-AT-06).
"""

import logging
import time
from datetime import datetime

from agno.agent import Agent
from agno.models.message import Message
from psycopg.types.json import Jsonb

from app.agent.contexto import esta_aberta, instrucoes
from app.agent.ferramentas import Sessao, criar_ferramentas
from app.eventos import avisar
from app.painel import crm
from app.ia import ConfigIA, config_da_clinica, modelo_agno

log = logging.getLogger("isis.agente")

MSG_FALHA = "Desculpe, tive um probleminha técnico agora. 😕 Pode repetir sua mensagem, por favor?"
MSG_HUMANO = "Vou chamar alguém da nossa equipe para continuar seu atendimento por aqui, tudo bem? Já já te respondem."
HISTORICO = 20  # mensagens anteriores enviadas ao modelo
AVISO_EQUIPE = "A partir de agora, quem continua seu atendimento é a nossa equipe, aqui mesmo nesta conversa."
AVISO_FECHADA = " Como estamos fora do horário, a resposta vem no próximo horário de atendimento."


TEXTO_TRANSFERENCIA = "Tudo bem! Já chamei alguém da nossa equipe para continuar com você."


def chamou_equipe(chamadas: list[dict]) -> bool:
    return any(c.get("ferramenta") == "chamar_humano" for c in chamadas)


def com_aviso_de_transferencia(saida: str, chamadas: list[dict], aberta: bool) -> str:
    """RN-AT-06 (D27): se a Ísis passou a conversa para a equipe, o paciente SEMPRE é avisado de que
    ela parou de responder. O aviso vem do código, não depende da IA lembrar."""
    if not chamou_equipe(chamadas):
        return saida
    return f"{saida}\n\n{AVISO_EQUIPE}{'' if aberta else AVISO_FECHADA}"




def _historico(conn, conversa_id, antes_de) -> list[Message]:
    rows = conn.execute(
        """select author, content from messages
           where conversation_id = %s and created_at < %s and author <> 'sistema'
           order by created_at desc limit %s""",
        (conversa_id, antes_de, HISTORICO),
    ).fetchall()[::-1]
    msgs = []
    for autor, texto in rows:
        if autor == "paciente":
            msgs.append(Message(role="user", content=texto))
        else:
            msgs.append(Message(role="assistant", content=f"[Equipe da clínica] {texto}" if autor == "recepcao" else texto))
    return msgs


def responder(conn, clinica: dict, paciente: dict, conversa: dict, texto: str, recebida_em: datetime,
              ia: ConfigIA | None = None) -> str:
    """Gera a resposta da Ísis para a mensagem `texto` (já gravada no banco em `recebida_em`).

    `ia` = a IA da clínica (chat.processar já buscou; sem ela, busca aqui). Sem IA a chamada falha e cai
    na resposta padrão — mas o normal é chat.processar nem chamar a Ísis quando ela está desligada (D46)."""
    ia = ia or config_da_clinica(conn, clinica["id"])
    agora = datetime.now(clinica["tz"])
    sessao = Sessao(conn=conn, clinica=clinica, paciente=paciente, conversa=conversa, agora=agora)
    inicio = time.perf_counter()
    saida, erro = None, None

    try:
        if ia is None:
            raise RuntimeError("assistente sem IA configurada")
        agente = Agent(
            model=modelo_agno(ia, f"{clinica['phone']}:{paciente['phone']}"),
            instructions=instrucoes(conn, clinica, paciente, agora),
            tools=criar_ferramentas(sessao),
            tool_call_limit=8,
            markdown=False,
            telemetry=False,
        )
        entrada = _historico(conn, conversa["id"], recebida_em) + [Message(role="user", content=texto)]
        r = agente.run(entrada)
        saida = (r.content or "").strip() if isinstance(r.content, str) else str(r.content or "").strip()
        if not saida:
            if not chamou_equipe(sessao.chamadas):
                raise RuntimeError("resposta vazia do modelo")
            saida = TEXTO_TRANSFERENCIA  # chamou a equipe e não escreveu nada: o código completa (achado da Etapa 8)
        saida = com_aviso_de_transferencia(saida, sessao.chamadas, esta_aberta(conn, clinica, agora))
    except Exception as e:  # noqa: BLE001 — qualquer falha vira resposta padrão
        erro = f"{type(e).__name__}: {e}"[:500]
        log.warning("falha da Ísis: %s", erro)
        saida = None

    if saida is None and chamou_equipe(sessao.chamadas):
        # A conversa já foi para a equipe: nunca pedir para o paciente repetir
        saida = com_aviso_de_transferencia(TEXTO_TRANSFERENCIA, sessao.chamadas, esta_aberta(conn, clinica, agora))
    if saida is None:
        anterior = conn.execute(
            "select content from messages where conversation_id = %s and author = 'isis' order by created_at desc limit 1",
            (conversa["id"],),
        ).fetchone()
        if anterior and anterior[0] == MSG_FALHA:  # 2ª falha seguida → equipe
            conn.execute("update conversations set status = 'humano' where id = %s", (conversa["id"],))
            conversa["status"] = "humano"
            crm.registrar(conn, clinica["id"], paciente["id"], "aguardando_humano", "sistema")
            avisar(conn, clinica["id"], "conversa", conversa["id"])
            saida = MSG_HUMANO
        else:
            saida = MSG_FALHA

    conn.execute(
        """insert into agent_runs (clinic_id, conversation_id, input, tools, output, latency_ms, error)
           values (%s, %s, %s, %s, %s, %s, %s)""",
        (clinica["id"], conversa["id"], texto, Jsonb(sessao.chamadas), saida,
         round((time.perf_counter() - inicio) * 1000), erro),
    )
    return saida
