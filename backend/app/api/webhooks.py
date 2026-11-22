"""Entrada dos webhooks dos canais (spec 04). Hoje: WAHA (Etapa 5)."""

import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.canais import waha, whatsapp
from app.config import get_settings
from app.db import pool
from app.eventos import avisar

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = logging.getLogger("isis.webhooks")


@router.post("/waha", summary="Eventos do WAHA (mensagens recebidas e status da sessão)")
async def webhook_waha(request: Request, tarefas: BackgroundTasks):
    s = get_settings()
    corpo = await request.body()
    if not s.waha_webhook_hmac_key:
        if s.env != "dev":
            raise HTTPException(503, "WAHA_WEBHOOK_HMAC_KEY não configurada")
        log.warning("webhook do WAHA aceito SEM assinatura (WAHA_WEBHOOK_HMAC_KEY vazia; só em dev)")
    elif not waha.verificar_assinatura(corpo, request.headers.get("x-webhook-hmac"), s.waha_webhook_hmac_key):
        raise HTTPException(401, "assinatura inválida")

    try:
        evento = json.loads(corpo)
    except ValueError as e:
        raise HTTPException(400, "JSON inválido") from e

    if evento.get("event") == "session.status":
        _atualizar_status(evento)
        return {"ok": True}
    if ack := waha.interpretar_ack(evento):  # D85: entregue/lida
        tarefas.add_task(whatsapp.processar_entrega, evento.get("session") or "", *ack)
        return {"ok": True}

    msg = waha.interpretar(evento)
    if msg is None:
        return {"ok": True, "ignorada": True}
    tarefas.add_task(whatsapp.processar, msg)  # responde ao WAHA já; a Ísis trabalha em segundo plano
    return {"ok": True}


def _atualizar_status(evento: dict) -> None:
    status = ((evento.get("payload") or {}).get("status") or "DESCONHECIDO")[:40]
    meu = waha._numero((evento.get("me") or {}).get("id"))
    with pool().connection() as conn:
        r = conn.execute(
            """update whatsapp_instances set status = %s, phone = coalesce(%s, phone), updated_at = now()
               where session = %s returning clinic_id""",
            (status, meu, evento.get("session")),
        ).fetchone()
        if r:
            avisar(conn, r[0], "whatsapp", r[0])


@router.post("/waha/{token}", summary="Webhook exclusivo de uma clínica (Etapa 16): segredo e sessão dela")
async def webhook_da_clinica(token: str, request: Request, tarefas: BackgroundTasks):
    from app.canais import conexao

    corpo = await request.body()
    with pool().connection() as conn:
        achado = conexao.por_token(conn, token)
    if not achado:
        raise HTTPException(404, "webhook desconhecido")
    _, sessao, segredo = achado
    if not segredo or not waha.verificar_assinatura(corpo, request.headers.get("x-webhook-hmac"), segredo):
        raise HTTPException(401, "assinatura inválida")
    try:
        evento = json.loads(corpo)
    except ValueError as e:
        raise HTTPException(400, "JSON inválido") from e
    if evento.get("session") != sessao:  # nunca aceita a sessão de outra clínica neste endereço
        return {"ok": True, "ignorada": True}
    if evento.get("event") == "session.status":
        _atualizar_status(evento)
        return {"ok": True}
    if ack := waha.interpretar_ack(evento):  # D85: entregue/lida
        tarefas.add_task(whatsapp.processar_entrega, evento.get("session") or "", *ack)
        return {"ok": True}
    msg = waha.interpretar(evento)
    if msg is None:
        return {"ok": True, "ignorada": True}
    tarefas.add_task(whatsapp.processar, msg)
    return {"ok": True}

