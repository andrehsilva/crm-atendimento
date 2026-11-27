"""Entrada dos webhooks dos canais (spec 04): WAHA (Etapa 5) e WhatsApp oficial da Meta (Etapa 36B, D131)."""

import json
import logging

import hmac

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.canais import meta, waha, whatsapp
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



# ---------------------------------------------------------------------------
# WhatsApp oficial (Meta) — Etapa 36B. Endereço exclusivo e opaco por clínica (o mesmo token do WAHA, D123).
# ---------------------------------------------------------------------------
@router.get("/meta/{token}", summary="Meta: verificação do endereço do webhook (hub.challenge)")
def verificar_webhook_meta(token: str, request: Request):
    from app.canais import conexao

    q = request.query_params
    with pool().connection() as conn:
        achado = conexao.por_token_meta(conn, token, exigir_meta=False)
    if not achado or not achado["verify_token"] or q.get("hub.mode") != "subscribe" or not hmac.compare_digest(
            q.get("hub.verify_token") or "", achado["verify_token"]):
        raise HTTPException(403, "verificação recusada")
    return PlainTextResponse(q.get("hub.challenge") or "")


@router.post("/meta/{token}", summary="Meta: mensagens recebidas e status (entregue, lida, falhou)")
async def webhook_meta(token: str, request: Request, tarefas: BackgroundTasks):
    from app.canais import conexao

    corpo = await request.body()
    with pool().connection() as conn:
        achado = conexao.por_token_meta(conn, token)
    if not achado:
        raise HTTPException(404, "webhook desconhecido")
    if not meta.verificar_assinatura(corpo, request.headers.get("x-hub-signature-256"), achado["app_secret"] or ""):
        raise HTTPException(401, "assinatura inválida")
    try:
        evento = json.loads(corpo)
    except ValueError as e:
        raise HTTPException(400, "JSON inválido") from e
    mensagens, entregas, falhas = meta.interpretar_webhook(evento, achado["sessao"], achado["phone_number_id"])
    for msg in mensagens:
        tarefas.add_task(whatsapp.processar, msg)  # responde à Meta já; a Ísis trabalha em segundo plano
    for i, nivel in entregas:
        tarefas.add_task(whatsapp.processar_entrega, achado["sessao"], i, nivel)
    for i, motivo in falhas:
        tarefas.add_task(whatsapp.processar_falha, achado["sessao"], i, motivo)
    return {"ok": True}
