"""Envio da fila de saída (outbound_messages) pelo WhatsApp — spec 05, Etapa 6.

Cada rodada pega as mensagens vencidas, uma por vez (FOR UPDATE SKIP LOCKED), e envia pelo WAHA.
Travas que ficam no código (não na IA):
- RN-MS-09: nada de mensagem automática na janela de silêncio (padrão 21h–08h).
- RN-DP-07: no máximo 20/min e 300/dia por clínica.
- RN-DP-04: quem pediu PARAR não recebe aniversário.
- Modo de teste (ENV=dev): só envia para os telefones de ENVIO_SOMENTE_PARA. Os dados de exemplo
  têm telefones inventados, que podem ser de pessoas reais.
"""

import logging
from datetime import datetime, timedelta

from psycopg.rows import dict_row

from app.agenda.erros import AgendaError
from app.agenda.servico import carregar_clinica
from app.canais.waha import ClienteWaha, WahaErro
from app.canais.whatsapp import instancia_da_clinica
from app.config import Settings, get_settings
from app.core.telefone import TelefoneInvalido, normalizar_telefone
from app.eventos import avisar
from app.mensagens import regras as R
from app.painel import chat

log = logging.getLogger("isis.envio")
MAX_TENTATIVAS = 3


def lista_de_teste(s: Settings) -> set[str] | None:
    """None = sem restrição (produção). Em dev, o conjunto de telefones liberados (pode ser vazio)."""
    if s.env != "dev":
        return None
    saida = set()
    for t in s.envio_somente_para.replace(";", ",").split(","):
        try:
            if t.strip():
                saida.add(normalizar_telefone(t.strip()))
        except TelefoneInvalido:
            log.warning("telefone inválido em ENVIO_SOMENTE_PARA: %s", t)
    return saida


def _finalizar(conn, oid, status: str, erro: str | None = None) -> None:
    conn.execute("update outbound_messages set status = %s, error = %s where id = %s", (status, erro, oid))


def _enviados_desde(conn, clinic_id, desde: datetime) -> int:
    return conn.execute(
        """select count(*) from outbound_messages where clinic_id = %s
           and status in ('enviada', 'entregue', 'lida') and sent_at > %s""",
        (clinic_id, desde),
    ).fetchone()[0]


def enviar_pendentes(conn, agora: datetime, cliente: ClienteWaha | None = None, maximo: int = 20,
                     s: Settings | None = None) -> int:
    """Envia até `maximo` mensagens vencidas. Devolve quantas foram enviadas."""
    s = s or get_settings()
    permitidos = lista_de_teste(s)
    pular: list = []  # clínicas em silêncio ou no limite nesta rodada
    enviados = 0
    while enviados < maximo:
        o = conn.cursor(row_factory=dict_row).execute(
            """select o.id, o.clinic_id, o.patient_id, o.kind, o.body, o.attempts, p.phone, p.optout_disparos
               from outbound_messages o join patients p on p.id = o.patient_id
               where o.status = 'agendada' and o.channel = 'whatsapp' and o.scheduled_for <= %s
                 and not (o.clinic_id = any(%s))
               order by o.scheduled_for limit 1
               for update of o skip locked""",
            (agora, pular),
        ).fetchone()
        if o is None:
            break
        cid = o["clinic_id"]
        try:
            clinica = carregar_clinica(conn, cid)
        except AgendaError as e:  # clínica suspensa
            _finalizar(conn, o["id"], "cancelada", e.mensagem)
            conn.commit()
            continue

        regras = clinica["regras"]
        if R.em_silencio(agora.astimezone(clinica["tz"]).time(), R.hora(regras.silencio_inicio), R.hora(regras.silencio_fim)):
            pular.append(cid)
            conn.rollback()
            continue
        if (_enviados_desde(conn, cid, agora - timedelta(minutes=1)) >= regras.envio_por_minuto
                or _enviados_desde(conn, cid, agora - timedelta(days=1)) >= regras.envio_por_dia):
            pular.append(cid)
            conn.rollback()
            continue

        if o["kind"] == "aniversario" and o["optout_disparos"]:
            _finalizar(conn, o["id"], "cancelada", "paciente pediu para não receber disparos")
        elif permitidos is not None and o["phone"] not in permitidos:
            _finalizar(conn, o["id"], "cancelada", "modo de teste: telefone fora de ENVIO_SOMENTE_PARA")
        elif not (inst := instancia_da_clinica(conn, cid)) or not inst["enabled"]:
            _finalizar(conn, o["id"], "falhou", "clínica sem WhatsApp conectado")
        else:
            if _enviar(conn, clinica, inst["session"], o, agora, cliente or ClienteWaha(s)):
                enviados += 1
        avisar(conn, cid, "mensagens")
        conn.commit()
    return enviados


def _enviar(conn, clinica: dict, sessao: str, o: dict, agora: datetime, cliente: ClienteWaha) -> bool:
    conversa = chat._conversa(conn, clinica["id"], o["patient_id"], "whatsapp")
    chat_id = conversa.get("external_chat_id") or f"{o['phone'].lstrip('+')}@c.us"
    try:
        id_ext = cliente.enviar_texto(sessao, chat_id, o["body"])
    except WahaErro as e:
        tentativas = o["attempts"] + 1
        if tentativas >= MAX_TENTATIVAS:
            conn.execute("update outbound_messages set status = 'falhou', attempts = %s, error = %s where id = %s",
                         (tentativas, str(e)[:300], o["id"]))
        else:  # tenta de novo daqui a alguns minutos
            conn.execute(
                "update outbound_messages set attempts = %s, error = %s, scheduled_for = %s where id = %s",
                (tentativas, str(e)[:300], agora + timedelta(minutes=2 * tentativas), o["id"]),
            )
        log.warning("falha ao enviar mensagem automática %s: %s", o["id"], e)
        return False

    ext = id_ext or f"outbound:{o['id']}"  # liga a mensagem da conversa à da fila (resposta ao lembrete)
    conn.execute(
        """update outbound_messages set status = 'enviada', sent_at = %s, attempts = attempts + 1,
                  external_id = %s, error = null where id = %s""",
        (agora, ext, o["id"]),
    )
    if not conversa.get("external_chat_id"):
        conn.execute("update conversations set external_chat_id = %s where id = %s", (chat_id, conversa["id"]))
    # Aparece na conversa (painel) e no histórico da Ísis: se o paciente responder, ela sabe do que se trata (RN-DP-09)
    chat._gravar(conn, clinica["id"], conversa["id"], "out", "isis", o["body"], ext)
    avisar(conn, clinica["id"], "conversa", conversa["id"])
    return True
