"""Configurações › Canais (D79, D80): o WhatsApp visto pela própria clínica.

Ver o status: toda a equipe. Mostrar o QR, reiniciar e pausar a Ísis: só o administrador da clínica.
Servidor WAHA, sessão e webhook continuam no Admin geral (Etapa 16) — aqui nada disso aparece.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from app.admin import servico as adm
from app.agenda import servico
from app.agenda.erros import AgendaError
from app.auth.acesso import acesso, exigir_admin_clinica
from app.canais import custo_meta
from app.canais.conexao import cliente_da_clinica, isis_pausada_no_whatsapp, provedor
from app.canais.waha import WahaErro
from app.canais.whatsapp import instancia_da_clinica
from app.core import relogio
from app.db import get_conn
from app.eventos import avisar

router = APIRouter(prefix="/api/clinics/{clinic_id}/config/canais", tags=["configurações"], dependencies=[Depends(acesso)])

# Status do WAHA → situação em português simples
SITUACAO = {"WORKING": "conectado", "SCAN_QR_CODE": "qr", "STARTING": "iniciando", "STOPPED": "parado", "FAILED": "falhou"}


def _instancia(conn, clinic_id: UUID) -> dict:
    inst = instancia_da_clinica(conn, clinic_id)
    if not inst or not inst["enabled"]:
        raise AgendaError("DADOS_INVALIDOS", "Esta clínica ainda não tem WhatsApp ligado. Fale com o suporte da plataforma.")
    return inst


def _cliente(conn, clinic_id: UUID):
    try:
        return cliente_da_clinica(conn, clinic_id)
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", str(e)) from e


def _so_waha(conn, clinic_id: UUID) -> None:
    if provedor(conn, clinic_id) == "meta":
        raise AgendaError("DADOS_INVALIDOS", "No WhatsApp oficial não há QR code nem reinício: a conexão fica na Meta.")


@router.get("/whatsapp", summary="Status do WhatsApp da clínica (sem dados técnicos)")
def whatsapp(clinic_id: UUID, conn=Depends(get_conn)):
    clinica = servico.carregar_clinica(conn, clinic_id)
    base = {"isis_pausada": isis_pausada_no_whatsapp(clinica)}
    inst = instancia_da_clinica(conn, clinic_id)
    base["provedor"] = provedor(conn, clinic_id)
    if not inst or not inst["enabled"]:
        return {**base, "ligado": False, "situacao": "sem_whatsapp", "numero": None}
    if base["provedor"] == "meta":  # 36D: WhatsApp oficial — confere na Meta se o número responde
        try:
            t = _cliente(conn, clinic_id).testar()
        except (WahaErro, AgendaError):
            return {**base, "ligado": True, "situacao": "sem_resposta", "numero": inst["phone"]}
        return {**base, "ligado": True, "situacao": "conectado", "numero": t.get("numero") or inst["phone"]}
    try:
        info = _cliente(conn, clinic_id).sessao(inst["session"])
    except (WahaErro, AgendaError):
        # não mostra o erro técnico (endereço do servidor etc.) para a clínica
        return {**base, "ligado": True, "situacao": "sem_resposta", "numero": inst["phone"]}
    status = info.get("status") or "DESCONHECIDO"
    numero = ((info.get("me") or {}).get("id") or "").split("@")[0] or None
    conn.execute("update whatsapp_instances set status = %s, phone = coalesce(%s, phone), updated_at = now() where clinic_id = %s",
                 (status, f"+{numero}" if numero else None, clinic_id))
    return {**base, "ligado": True, "situacao": SITUACAO.get(status, "desconhecido"),
            "numero": f"+{numero}" if numero else inst["phone"]}


@router.get("/whatsapp/qr", summary="QR code para conectar o celular (imagem PNG) — só o admin da clínica")
def whatsapp_qr(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    inst = _instancia(conn, clinic_id)
    _so_waha(conn, clinic_id)
    try:
        png = _cliente(conn, clinic_id).qr_png(inst["session"])
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", "O QR code ainda não está disponível. Espere alguns segundos ou reinicie a conexão.") from e
    return Response(png, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/whatsapp/reiniciar", summary="Reiniciar a conexão do WhatsApp — só o admin da clínica")
def whatsapp_reiniciar(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    u = exigir_admin_clinica(request, clinic_id)
    inst = _instancia(conn, clinic_id)
    _so_waha(conn, clinic_id)
    try:
        _cliente(conn, clinic_id).reiniciar(inst["session"])
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", "Não consegui reiniciar agora. Tente de novo em instantes ou fale com o suporte.") from e
    adm.auditar(conn, u.id, "reiniciar_whatsapp_clinica", clinic_id)
    avisar(conn, clinic_id, "whatsapp", clinic_id)
    return {"ok": True}


class Pausa(BaseModel):
    pausada: bool


@router.put("/whatsapp/pausa", summary="Pausar ou retomar a Ísis no WhatsApp — só o admin da clínica")
def whatsapp_pausa(clinic_id: UUID, body: Pausa, request: Request, conn=Depends(get_conn)):
    u = exigir_admin_clinica(request, clinic_id)
    servico.carregar_clinica(conn, clinic_id)
    conn.execute("update clinics set settings = coalesce(settings, '{}'::jsonb) || %s, updated_at = now() where id = %s",
                 (Jsonb({"isis_pausada_whatsapp": body.pausada}), clinic_id))
    adm.auditar(conn, u.id, "pausar_isis_whatsapp" if body.pausada else "retomar_isis_whatsapp", clinic_id)
    avisar(conn, clinic_id, "whatsapp", clinic_id)
    return whatsapp(clinic_id, conn)


@router.get("/whatsapp/custo", summary="WhatsApp oficial: mensagens cobradas no mês e gasto estimado")
def whatsapp_custo(clinic_id: UUID, conn=Depends(get_conn)):
    servico.carregar_clinica(conn, clinic_id)
    if provedor(conn, clinic_id) != "meta":
        raise AgendaError("DADOS_INVALIDOS", "Só o WhatsApp oficial (Meta) cobra por mensagem.")
    return custo_meta.do_mes(conn, clinic_id, relogio.agora())
