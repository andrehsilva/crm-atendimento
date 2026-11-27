"""Painel de admin geral (D30, spec 07-B). Tudo aqui é só para o super admin (dono da plataforma)."""

import re
from urllib.parse import urlparse
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from psycopg.rows import dict_row
from pydantic import BaseModel, Field, field_validator

from app.admin import servico as adm
from app.agenda.erros import AgendaError
from app.auth.acesso import acesso, exigir_super_admin, usuario_da_requisicao
from app.auth.usuarios import PAPEIS, criar_ou_ligar
from app.canais.waha import ClienteWaha, WahaErro
from app.config import get_settings
from app.core.telefone import TelefoneInvalido, normalizar_telefone
from app.db import get_conn
from app.eventos import avisar
from app.segmentos import SEGMENTOS
from app import ia, uso_ia
from app.canais import conexao, custo_meta, modelos_meta
from app.core import relogio


def _so_super_admin(request: Request, _=Depends(acesso)) -> None:
    exigir_super_admin(request)


router = APIRouter(prefix="/api/admin", tags=["admin geral"], dependencies=[Depends(_so_super_admin)])

SESSAO_VALIDA = re.compile(r"^[a-zA-Z0-9_-]{2,40}$")


def _fuso(v: str) -> str:
    try:
        ZoneInfo(v)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError("Fuso horário inválido") from e
    return v


SEGMENTOS_RE = "^(" + "|".join(SEGMENTOS) + ")$"


class NovaClinica(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    telefone: str = Field(min_length=8, max_length=30)
    fuso: str = "America/Sao_Paulo"
    endereco: str | None = Field(None, max_length=300)
    nome_assistente: str = Field("Ísis", min_length=1, max_length=40)
    admin_email: str = Field(min_length=3, max_length=200)
    admin_nome: str | None = Field(None, max_length=120)
    segmento: str = Field("odontologia", pattern=SEGMENTOS_RE)
    profissional: str | None = Field(None, max_length=120)

    _fuso_ok = field_validator("fuso")(_fuso)


class EdicaoClinica(BaseModel):
    nome: str | None = Field(None, min_length=2, max_length=120)
    telefone: str | None = Field(None, min_length=8, max_length=30)
    endereco: str | None = Field(None, max_length=300)
    fuso: str | None = None
    nome_assistente: str | None = Field(None, min_length=1, max_length=40)
    segmento: str | None = Field(None, pattern=SEGMENTOS_RE)
    status: str | None = Field(None, pattern="^(ativa|suspensa)$")
    apresentacao: bool | None = None  # D55: clínica de apresentação da plataforma

    @field_validator("fuso")
    @classmethod
    def _f(cls, v):
        return _fuso(v) if v else v


class NovoUsuario(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    nome: str | None = Field(None, max_length=120)
    papel: str = Field(pattern="^(clinic_admin|reception)$")


class EdicaoUsuario(BaseModel):
    ativo: bool | None = None
    papel: str | None = Field(None, pattern="^(clinic_admin|reception)$")


class LigarSessao(BaseModel):
    sessao: str = Field(min_length=2, max_length=40)


def _waha(conn=None, clinic_id: UUID | None = None) -> ClienteWaha:
    """Servidor WAHA da clínica (Etapa 16) ou, sem clínica/servidor próprio, o da plataforma."""
    try:
        return conexao.cliente_da_clinica(conn, clinic_id) if conn is not None and clinic_id else ClienteWaha()
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", str(e)) from e


def _instancia(conn, clinic_id: UUID) -> dict:
    r = conn.execute("""select session, status, phone, enabled from whatsapp_instances
                        where clinic_id = %s and enabled and session is not null""", (clinic_id,)).fetchone()
    if not r:
        raise AgendaError("DADOS_INVALIDOS", "Esta clínica ainda não tem WhatsApp ligado.")
    return {"sessao": r[0], "status": r[1], "numero": r[2], "ativo": r[3]}


def _existe(conn, clinic_id: UUID) -> None:
    if not conn.execute("select 1 from clinics where id = %s", (clinic_id,)).fetchone():
        raise AgendaError("CLINICA_NAO_ENCONTRADA", "Clínica não encontrada.")


# ---------------------------------------------------------------------------
# Clínicas
# ---------------------------------------------------------------------------
@router.get("/clinicas", summary="Todas as clínicas da plataforma")
def clinicas(conn=Depends(get_conn)):
    return adm.listar_clinicas(conn)


@router.post("/clinicas", status_code=201, summary="Criar clínica (com horários, procedimentos e 1º admin)")
def criar(body: NovaClinica, request: Request, conn=Depends(get_conn)):
    u = usuario_da_requisicao(request)
    r = adm.criar_clinica(conn, **body.model_dump())
    adm.auditar(conn, u.id, "criar_clinica", r["id"], {"nome": body.nome})
    return r


@router.get("/clinicas/{clinic_id}", summary="Detalhe da clínica")
def detalhe(clinic_id: UUID, conn=Depends(get_conn)):
    c = next((x for x in adm.listar_clinicas(conn) if x["id"] == clinic_id), None)
    if not c:
        raise AgendaError("CLINICA_NAO_ENCONTRADA", "Clínica não encontrada.")
    return c


@router.patch("/clinicas/{clinic_id}", summary="Editar ou suspender/reativar a clínica")
def editar(clinic_id: UUID, body: EdicaoClinica, request: Request, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    dados = body.model_dump(exclude_none=True)
    alteracao_telefone = adm.atualizar_clinica(conn, clinic_id, dados)
    u = usuario_da_requisicao(request)
    if alteracao_telefone:
        adm.auditar(conn, u.id, "alterar_telefone_clinica", clinic_id,
                    {"anterior": alteracao_telefone[0], "novo": alteracao_telefone[1]})
    if "status" in dados:
        adm.auditar(conn, u.id, "suspender" if dados["status"] == "suspensa" else "reativar", clinic_id)
    return detalhe(clinic_id, conn)


@router.post("/clinicas/{clinic_id}/entrar", summary="Entrar como a clínica (suporte) — fica registrado")
def entrar_como(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    adm.auditar(conn, usuario_da_requisicao(request).id, "entrar_como", clinic_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Usuários da clínica
# ---------------------------------------------------------------------------
@router.get("/clinicas/{clinic_id}/usuarios", summary="Usuários da clínica")
def usuarios(clinic_id: UUID, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    return adm.usuarios_da_clinica(conn, clinic_id)


@router.post("/clinicas/{clinic_id}/usuarios", status_code=201, summary="Criar usuário (senha provisória aparece uma vez)")
def criar_usuario(clinic_id: UUID, body: NovoUsuario, request: Request, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    uid, senha = criar_ou_ligar(conn, body.email, body.nome, clinic_id=clinic_id, papel=body.papel)
    adm.auditar(conn, usuario_da_requisicao(request).id, "criar_usuario", clinic_id, {"email": body.email, "papel": body.papel})
    return {"id": uid, "email": body.email.strip().lower(), "senha_provisoria": senha}


@router.patch("/clinicas/{clinic_id}/usuarios/{user_id}", summary="Ativar/desativar ou mudar o papel")
def editar_usuario(clinic_id: UUID, user_id: UUID, body: EdicaoUsuario, request: Request, conn=Depends(get_conn)):
    if body.papel and body.papel not in PAPEIS:
        raise AgendaError("DADOS_INVALIDOS", "Papel inválido.")
    r = conn.execute(
        """update clinic_users set active = coalesce(%s, active), role = coalesce(%s, role)
           where clinic_id = %s and user_id = %s returning user_id""",
        (body.ativo, body.papel, clinic_id, user_id),
    ).fetchone()
    if not r:
        raise AgendaError("DADOS_INVALIDOS", "Usuário não encontrado nesta clínica.")
    adm.auditar(conn, usuario_da_requisicao(request).id, "editar_usuario", clinic_id, {"user_id": str(user_id), **body.model_dump(exclude_none=True)})
    return {"ok": True}


# ---------------------------------------------------------------------------
# WhatsApp da clínica (D31; Etapa 16 — D76; Etapa 31 — D122–D124)
#   1. servidor (da plataforma ou próprio) — dá para salvar antes de ligar;
#   2. sessão (uma livre desse servidor, ou nova com QR code);
#   3. webhook exclusivo da clínica, criado e apontado sozinho ao ligar.
# Desligar guarda servidor e webhook. Mudar o webhook de uma sessão reinicia a sessão no WAHA.
# ---------------------------------------------------------------------------
def _sessoes_do_servidor(conn, w: ClienteWaha) -> list[dict]:
    ligadas = {r[0]: {"clinic_id": r[1], "clinica": r[2]} for r in conn.execute(
        """select w.session, c.id, c.name from whatsapp_instances w join clinics c on c.id = w.clinic_id
           where w.session is not null""").fetchall()}
    try:
        lista = w.listar_sessoes()
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", f"Não consegui falar com o servidor WAHA ({_motivo(e)}). "
                                          "Confira o endereço e a chave da API.") from e
    return [{"sessao": x.get("name"), "status": x.get("status"),
             "numero": ((x.get("me") or {}).get("id") or "").split("@")[0] or None,
             "webhooks": [g.get("url") for g in ((x.get("config") or {}).get("webhooks") or [])],
             **(ligadas.get(x.get("name")) or {"clinic_id": None, "clinica": None})}
            for x in lista if isinstance(x, dict)]


def _motivo(e: WahaErro) -> str:
    """Erro do WAHA em português simples (401 = chave errada é o caso mais comum)."""
    t = str(e)
    if " 401 " in t:
        return "chave da API recusada (401)"
    if " 404 " in t:
        return "sessão não encontrada no servidor (404)"
    if "fora do ar" in t:
        return "servidor fora do ar, endereço errado ou demorou demais para responder"
    return t[:160]


@router.get("/whatsapp/sessoes", summary="Sessões do servidor WAHA da plataforma e a clínica ligada a cada uma")
def sessoes(conn=Depends(get_conn)):
    return _sessoes_do_servidor(conn, _waha())


@router.get("/clinicas/{clinic_id}/whatsapp/sessoes", summary="Sessões do servidor que ESTA clínica usa")
def sessoes_da_clinica(clinic_id: UUID, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    return _sessoes_do_servidor(conn, _waha(conn, clinic_id))


def _ligada(conn, clinic_id: UUID):
    return conn.execute("select session from whatsapp_instances where clinic_id = %s and enabled and session is not null",
                        (clinic_id,)).fetchone()


@router.get("/clinicas/{clinic_id}/whatsapp", summary="Status do WhatsApp da clínica (com servidor e webhook)")
def whatsapp_status(clinic_id: UUID, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    prov = conexao.provedor(conn, clinic_id)
    base = {"conexao": conexao.estado(conn, clinic_id), "provedor": prov}
    r = _ligada(conn, clinic_id)
    if not r:
        return {**base, "ligado": False}
    if prov == "meta":  # 36D: a conexão é na Meta — nada de sessão/QR do WAHA aqui
        return {**base, "ligado": True, **_instancia(conn, clinic_id)}
    try:
        info = _waha(conn, clinic_id).sessao(r[0])
    except WahaErro as e:
        return {**base, "ligado": True, **_instancia(conn, clinic_id), "erro": _motivo(e)}
    status = info.get("status") or "DESCONHECIDO"
    numero = ((info.get("me") or {}).get("id") or "").split("@")[0] or None
    conn.execute("update whatsapp_instances set status = %s, phone = coalesce(%s, phone), updated_at = now() where clinic_id = %s",
                 (status, f"+{numero}" if numero else None, clinic_id))
    url, _ = conexao.webhook_da_clinica(conn, clinic_id)
    return {**base, "ligado": True, **_instancia(conn, clinic_id),
            "webhooks": [g.get("url") for g in ((info.get("config") or {}).get("webhooks") or [])],
            "webhook_ok": conexao.webhook_alinhado(info, url)}


def _exigir_endereco_publico() -> None:
    if not get_settings().public_base_url:
        raise AgendaError("DADOS_INVALIDOS", "Preencha PUBLIC_BASE_URL no backend (endereço público deste sistema).")


@router.put("/clinicas/{clinic_id}/whatsapp", summary="Ligar a clínica a uma sessão (existente ou nova) — já aponta o webhook")
def whatsapp_ligar(clinic_id: UUID, body: LigarSessao, request: Request, criar: bool = False, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    _exigir_endereco_publico()
    if not SESSAO_VALIDA.match(body.sessao):
        raise AgendaError("DADOS_INVALIDOS", "Nome da sessão: só letras, números, - e _ (2 a 40).")
    dono = conn.execute("select clinic_id from whatsapp_instances where session = %s", (body.sessao,)).fetchone()
    if dono and dono[0] != clinic_id:
        raise AgendaError("DADOS_INVALIDOS", "Essa sessão já está ligada a outra clínica (1 número = 1 clínica, D29).")
    url, segredo = conexao.garantir_webhook(conn, clinic_id)  # D123: sempre o webhook exclusivo da clínica
    w = _waha(conn, clinic_id)
    reiniciando = criar
    try:
        if criar:
            info = w.criar_sessao(body.sessao, url, segredo)
        else:
            info = w.sessao(body.sessao)
            if not conexao.webhook_alinhado(info, url):
                w.configurar_webhook(body.sessao, url, segredo)  # o WAHA reinicia a sessão
                reiniciando = True
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", f"O servidor WAHA recusou: {_motivo(e)}.") from e
    conn.execute(
        "update whatsapp_instances set session = %s, enabled = true, status = %s, updated_at = now() where clinic_id = %s",
        (body.sessao, "STARTING" if reiniciando else (info.get("status") or "STARTING"), clinic_id))
    adm.auditar(conn, usuario_da_requisicao(request).id, "ligar_whatsapp", clinic_id, {"sessao": body.sessao, "nova": criar})
    avisar(conn, clinic_id, "whatsapp", clinic_id)
    return {**whatsapp_status(clinic_id, conn), "reiniciando": reiniciando}


@router.delete("/clinicas/{clinic_id}/whatsapp", summary="Desligar a clínica da sessão (guarda servidor e webhook)")
def whatsapp_desligar(clinic_id: UUID, request: Request, tirar_webhook: bool = False, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    r = _ligada(conn, clinic_id)
    aviso = None
    if r and tirar_webhook:
        url, _ = conexao.webhook_da_clinica(conn, clinic_id)
        try:
            _waha(conn, clinic_id).remover_webhook(r[0], url)
        except WahaErro as e:
            aviso = f"Desligado, mas não consegui tirar o webhook no WAHA ({_motivo(e)})."
    conn.execute("""update whatsapp_instances set session = null, enabled = false, status = 'DESLIGADO', phone = null,
                    updated_at = now() where clinic_id = %s""", (clinic_id,))
    adm.auditar(conn, usuario_da_requisicao(request).id, "desligar_whatsapp", clinic_id,
                {"sessao": r[0] if r else None, "tirou_webhook": tirar_webhook})
    avisar(conn, clinic_id, "whatsapp", clinic_id)
    return {**whatsapp_status(clinic_id, conn), **({"aviso": aviso} if aviso else {})}


@router.post("/clinicas/{clinic_id}/whatsapp/webhook", summary="Corrigir: apontar o webhook exclusivo da clínica na sessão")
def whatsapp_webhook(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    _exigir_endereco_publico()
    inst = _instancia(conn, clinic_id)
    url, segredo = conexao.garantir_webhook(conn, clinic_id)
    try:
        _waha(conn, clinic_id).configurar_webhook(inst["sessao"], url, segredo)
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", f"O servidor WAHA recusou: {_motivo(e)}.") from e
    adm.auditar(conn, usuario_da_requisicao(request).id, "configurar_webhook", clinic_id, {"sessao": inst["sessao"]})
    return {**whatsapp_status(clinic_id, conn), "reiniciando": True}


@router.post("/clinicas/{clinic_id}/whatsapp/reiniciar", summary="Reiniciar a sessão no WAHA")
def whatsapp_reiniciar(clinic_id: UUID, conn=Depends(get_conn)):
    inst = _instancia(conn, clinic_id)
    try:
        _waha(conn, clinic_id).reiniciar(inst["sessao"])
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", f"O servidor WAHA recusou: {_motivo(e)}.") from e
    return {"ok": True}


@router.get("/clinicas/{clinic_id}/whatsapp/qr", summary="QR code para conectar o número (imagem PNG)")
def whatsapp_qr(clinic_id: UUID, conn=Depends(get_conn)):
    inst = _instancia(conn, clinic_id)
    try:
        png = _waha(conn, clinic_id).qr_png(inst["sessao"])
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", f"QR indisponível agora (a sessão precisa estar em SCAN_QR_CODE). {_motivo(e)}") from e
    return Response(png, media_type="image/png", headers={"Cache-Control": "no-store"})


class ServidorClinica(BaseModel):
    numero: str | None = Field(None, max_length=20)
    url: str | None = Field(None, max_length=200)   # vazio = servidor da plataforma
    chave: str | None = Field(None, max_length=300)  # vazio = mantém a salva


@router.get("/clinicas/{clinic_id}/whatsapp/conexao", summary="Número e servidor da clínica (sem segredos)")
def ver_conexao(clinic_id: UUID, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    return conexao.estado(conn, clinic_id)


@router.put("/clinicas/{clinic_id}/whatsapp/conexao", summary="Salvar número e servidor WAHA da clínica (antes ou depois de ligar)")
def salvar_conexao(clinic_id: UUID, body: ServidorClinica, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    novo = (body.url or "").strip().rstrip("/") or None
    if _ligada(conn, clinic_id) and novo != conexao.estado(conn, clinic_id).get("servidor_url"):
        raise AgendaError("DADOS_INVALIDOS", "Para trocar de servidor, desligue o WhatsApp da clínica primeiro.")
    numero = None
    if body.numero and body.numero.strip():
        try:
            numero = normalizar_telefone(body.numero)
        except TelefoneInvalido as e:
            raise AgendaError("TELEFONE_INVALIDO", f"Número do WhatsApp: {e}") from e
    try:
        conexao.salvar_servidor(conn, clinic_id, numero=numero, url=novo, chave=(body.chave or "").strip() or None)
    except ValueError as e:
        raise AgendaError("DADOS_INVALIDOS", str(e)) from e
    return conexao.estado(conn, clinic_id)


@router.post("/clinicas/{clinic_id}/whatsapp/testar", summary="Testar o servidor WAHA da clínica (lista as sessões)")
def testar_conexao(clinic_id: UUID, conn=Depends(get_conn)):
    try:
        sessoes = _waha(conn, clinic_id).listar_sessoes()
    except WahaErro as e:
        return {"ok": False, "detalhe": f"Não consegui falar com o servidor WAHA: {_motivo(e)}. Confira o endereço e a chave."}
    return {"ok": True, "sessoes": [x.get("name") for x in sessoes if isinstance(x, dict)]}


# ---------------------------------------------------------------------------
# WhatsApp oficial (Etapa 36A — D131): o super admin escolhe o provedor de cada clínica (padrão WAHA)
# ---------------------------------------------------------------------------
class Provedor(BaseModel):
    provedor: str = Field(pattern="^(waha|meta)$")


class DadosMeta(BaseModel):
    phone_number_id: str = Field(pattern=r"^\s*[0-9]{5,30}\s*$")
    waba_id: str = Field(pattern=r"^\s*[0-9]{5,30}\s*$")
    token: str | None = Field(None, max_length=1000)  # vazio = mantém o salvo
    app_secret: str | None = Field(None, max_length=200)  # vazio = mantém a salva


@router.get("/clinicas/{clinic_id}/whatsapp/meta", summary="Provedor e dados da Meta da clínica (sem segredos)")
def ver_meta(clinic_id: UUID, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    return conexao.estado_meta(conn, clinic_id)


@router.put("/clinicas/{clinic_id}/whatsapp/meta", summary="Salvar os dados da Meta (não troca o provedor)")
def salvar_meta(clinic_id: UUID, body: DadosMeta, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    try:
        conexao.salvar_meta(conn, clinic_id, phone_number_id=body.phone_number_id, waba_id=body.waba_id,
                            token=(body.token or "").strip() or None, app_secret=(body.app_secret or "").strip() or None)
    except ValueError as e:
        raise AgendaError("DADOS_INVALIDOS", str(e)) from e
    return conexao.estado_meta(conn, clinic_id)


@router.post("/clinicas/{clinic_id}/whatsapp/meta/testar", summary="Testar ID do número e token na Meta")
def testar_meta(clinic_id: UUID, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    try:
        return {"ok": True, **conexao.cliente_meta(conn, clinic_id).testar()}
    except WahaErro as e:  # MetaErro herda de WahaErro
        return {"ok": False, "detalhe": f"A Meta não aceitou: {_motivo(e)}"}


def _modelos(conn, clinic_id: UUID, criar: bool) -> dict:
    """36C: os modelos do TemHorario na conta da Meta da clínica (criar os que faltam ou só ver a situação)."""
    _existe(conn, clinic_id)
    waba = conexao.estado_meta(conn, clinic_id)["waba_id"]
    if not waba:
        raise AgendaError("DADOS_INVALIDOS", "Salve o ID da conta do WhatsApp Business antes.")
    try:
        c = conexao.cliente_meta(conn, clinic_id)
        lista = modelos_meta.criar_faltantes(c, waba) if criar else modelos_meta.situacao(c.listar_modelos(waba))
    except WahaErro as e:  # MetaErro herda de WahaErro
        raise AgendaError("ENVIO_FALHOU", f"A Meta não aceitou: {_motivo(e)}") from e
    return {"modelos": lista, "aprovados": sum(m["situacao"] == "aprovado" for m in lista), "total": len(lista)}


@router.get("/clinicas/{clinic_id}/whatsapp/meta/modelos", summary="Situação dos modelos do TemHorario na Meta")
def ver_modelos(clinic_id: UUID, conn=Depends(get_conn)):
    return _modelos(conn, clinic_id, criar=False)


@router.post("/clinicas/{clinic_id}/whatsapp/meta/modelos", summary="Criar na Meta os modelos que faltam")
def criar_modelos(clinic_id: UUID, conn=Depends(get_conn)):
    return _modelos(conn, clinic_id, criar=True)


@router.get("/clinicas/{clinic_id}/whatsapp/meta/custo", summary="Mensagens cobradas no mês e gasto estimado (Meta)")
def custo_meta_clinica(clinic_id: UUID, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    return custo_meta.do_mes(conn, clinic_id, relogio.agora())


class PrecosMeta(BaseModel):
    marketing: float = Field(ge=0, le=1)
    utility: float = Field(ge=0, le=1)
    authentication: float = Field(ge=0, le=1)
    service: float = Field(ge=0, le=1)
    servico_gratis: int = Field(1000, ge=0, le=100000)


@router.get("/whatsapp/meta/precos", summary="Preços da Meta usados na estimativa (US$ por mensagem)")
def ver_precos_meta(conn=Depends(get_conn)):
    tabela, gratis, cotacao = custo_meta.precos(conn)
    return {**tabela, "servico_gratis": gratis, "cotacao_brl": float(cotacao) if cotacao else None}


@router.put("/whatsapp/meta/precos", summary="Atualizar os preços da Meta (mudam por trimestre)")
def salvar_precos_meta(body: PrecosMeta, conn=Depends(get_conn)):
    d = body.model_dump()
    gratis = d.pop("servico_gratis")
    custo_meta.salvar_precos(conn, d, gratis)
    return ver_precos_meta(conn)


@router.put("/clinicas/{clinic_id}/whatsapp/provedor", summary="Trocar o provedor do WhatsApp da clínica (WAHA ou Meta)")
def trocar_provedor(clinic_id: UUID, body: Provedor, request: Request, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    if body.provedor == "meta":
        m = conexao.estado_meta(conn, clinic_id)
        if not (m["phone_number_id"] and m["token_final"] and m["tem_app_secret"]):
            raise AgendaError("DADOS_INVALIDOS", "Salve os dados da Meta (ID do número, token e chave secreta) antes de trocar.")
    try:
        conexao.trocar_provedor(conn, clinic_id, body.provedor)
    except ValueError as e:
        raise AgendaError("DADOS_INVALIDOS", str(e)) from e
    adm.auditar(conn, usuario_da_requisicao(request).id, "whatsapp_provedor", clinic_id, {"provedor": body.provedor})
    return conexao.estado_meta(conn, clinic_id)


# ---------------------------------------------------------------------------
# IA da clínica vista pelo admin geral (D46): ligar/desligar "usar a chave da plataforma"
# ---------------------------------------------------------------------------
class UsoPlataforma(BaseModel):
    usa_plataforma: bool


@router.get("/clinicas/{clinic_id}/ia", summary="Situação da IA da clínica")
def ia_da_clinica(clinic_id: UUID, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    return _estado_ia(conn, clinic_id)


def _estado_ia(conn, clinic_id: UUID) -> dict:
    liberado = conn.execute("select pergunte_liberado from clinics where id = %s", (clinic_id,)).fetchone()[0]
    return {**ia.estado_publico(conn, clinic_id), "pergunte_liberado": liberado}


class PergunteLiberado(BaseModel):
    liberado: bool


@router.put("/clinicas/{clinic_id}/pergunte", summary="Liberar/bloquear o \"Perguntar à assistente\" (D121)")
def pergunte_liberado(clinic_id: UUID, body: PergunteLiberado, request: Request, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    conn.execute("update clinics set pergunte_liberado = %s where id = %s", (body.liberado, clinic_id))
    adm.auditar(conn, usuario_da_requisicao(request).id, "liberar_pergunte" if body.liberado else "bloquear_pergunte", clinic_id)
    return _estado_ia(conn, clinic_id)


@router.put("/clinicas/{clinic_id}/ia", summary="Ligar/desligar o uso da chave da plataforma")
def ia_plataforma(clinic_id: UUID, body: UsoPlataforma, request: Request, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    ia.usar_plataforma(conn, clinic_id, body.usa_plataforma, usuario_da_requisicao(request).id)
    return _estado_ia(conn, clinic_id)


# ---------------------------------------------------------------------------
# Preços dos modelos e cotação do dólar (Etapa 10B — D44)
# ---------------------------------------------------------------------------
class Preco(BaseModel):
    provedor: str = Field(pattern="^(google|openai|opencode|openrouter)$")
    modelo: str = Field(min_length=1, max_length=120)
    entrada_usd: float = Field(ge=0, le=10000)  # por 1 milhão de tokens
    saida_usd: float = Field(ge=0, le=10000)
    cache_usd: float | None = Field(None, ge=0, le=10000)


class Cotacao(BaseModel):
    cotacao_brl: float | None = Field(None, gt=0, le=1000)


@router.get("/precos", summary="Tabela de preços dos modelos (US$ por 1 milhão de tokens)")
def ver_precos(conn=Depends(get_conn)):
    c = uso_ia.cotacao(conn)
    return {"precos": uso_ia.precos(conn), "cotacao_brl": float(c) if c else None}


@router.put("/precos", summary="Cadastrar ou mudar o preço de um modelo (vale para as próximas respostas)")
def salvar_preco(body: Preco, conn=Depends(get_conn)):
    uso_ia.salvar_preco(conn, body.provedor, body.modelo, body.entrada_usd, body.saida_usd, body.cache_usd)
    return ver_precos(conn)


@router.delete("/precos/{provedor}/{modelo:path}", summary="Tirar o preço de um modelo")
def apagar_preco(provedor: str, modelo: str, conn=Depends(get_conn)):
    uso_ia.apagar_preco(conn, provedor, modelo)
    return ver_precos(conn)


@router.put("/cotacao", summary="Cotação do dólar em R$ (só para mostrar valores em reais)")
def salvar_cotacao(body: Cotacao, conn=Depends(get_conn)):
    uso_ia.salvar_cotacao(conn, body.cotacao_brl)
    return ver_precos(conn)


# ---------------------------------------------------------------------------
# Uso e configurações da plataforma
# ---------------------------------------------------------------------------
@router.get("/uso", summary="Uso do mês por clínica")
def uso(conn=Depends(get_conn)):
    return conn.cursor(row_factory=dict_row).execute(
        """select c.id, c.name, c.status,
                  (select count(distinct m.conversation_id) from messages m where m.clinic_id = c.id
                     and m.created_at >= date_trunc('month', now())) as conversas,
                  (select count(*) from messages m where m.clinic_id = c.id and m.direction = 'in'
                     and m.created_at >= date_trunc('month', now())) as mensagens_recebidas,
                  (select count(*) from agent_runs r where r.clinic_id = c.id and r.tipo = 'resposta'
                     and r.created_at >= date_trunc('month', now())) as respostas_ia,
                  (select round(avg(latency_ms) / 1000.0, 1) from agent_runs r where r.clinic_id = c.id
                     and r.tipo = 'resposta' and r.created_at >= date_trunc('month', now())) as tempo_medio_s,
                  (select count(*) from agent_runs r where r.clinic_id = c.id and r.error is not null
                     and r.tipo <> 'equipe' and r.created_at >= date_trunc('month', now())) as falhas_ia,
                  (select coalesce(sum(coalesce(r.tokens_entrada, 0) + coalesce(r.tokens_saida, 0)), 0) from agent_runs r
                     where r.clinic_id = c.id and r.created_at >= date_trunc('month', now())) as tokens_ia,
                  (select coalesce(sum(r.custo_usd), 0)::float from agent_runs r where r.clinic_id = c.id
                     and r.origem = 'clinica' and r.created_at >= date_trunc('month', now())) as custo_clinica_usd,
                  (select coalesce(sum(r.custo_usd), 0)::float from agent_runs r where r.clinic_id = c.id
                     and r.origem = 'plataforma' and r.created_at >= date_trunc('month', now())) as custo_plataforma_usd,
                  (select count(*) from outbound_messages o where o.clinic_id = c.id and o.status in ('enviada', 'entregue', 'lida')
                     and o.sent_at >= date_trunc('month', now())) as automaticas_enviadas,
                  (select count(*) from appointments a where a.clinic_id = c.id and a.source = 'isis'
                     and a.created_at >= date_trunc('month', now())) as consultas_pela_ia
           from clinics c order by c.name"""
    ).fetchall()


@router.get("/plataforma", summary="Configurações da plataforma (somente leitura; mudam no backend/.env)")
def plataforma():
    s = get_settings()
    host = lambda u: urlparse(u).netloc or None  # noqa: E731 — só o domínio, nunca chaves
    return {
        "ambiente": s.env,
        "modelo_ia": s.llm_model,
        "ia_configurada": bool(s.llm_api_key),
        "waha_servidor": host(s.waha_api_url),
        "waha_configurado": bool(s.waha_api_url and s.waha_api_key),
        "webhook_assinado": bool(s.waha_webhook_hmac_key),
        "endereco_publico": s.public_base_url or None,
        "mensagens_automaticas": s.mensagens_automaticas,
        "modo_teste_numeros": len([x for x in s.envio_somente_para.split(",") if x.strip()]) if s.env == "dev" else None,
        "supabase": host(s.supabase_url),
        "transcricao_configurada": bool(s.transcricao_api_key),  # 13B: áudio do WhatsApp vira texto
    }
