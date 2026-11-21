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
from app.db import get_conn
from app.eventos import avisar
from app.segmentos import SEGMENTOS
from app import ia, uso_ia


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


def _waha() -> ClienteWaha:
    try:
        return ClienteWaha()
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", str(e)) from e


def _instancia(conn, clinic_id: UUID) -> dict:
    r = conn.execute("select session, status, phone, enabled from whatsapp_instances where clinic_id = %s", (clinic_id,)).fetchone()
    if not r:
        raise AgendaError("DADOS_INVALIDOS", "Esta clínica ainda não tem WhatsApp ligado.")
    return {"sessao": r[0], "status": r[1], "numero": r[2], "ativo": r[3]}


def _url_webhook() -> str:
    s = get_settings()
    if not (s.public_base_url and s.waha_webhook_hmac_key):
        raise AgendaError("DADOS_INVALIDOS", "Preencha PUBLIC_BASE_URL e WAHA_WEBHOOK_HMAC_KEY no backend/.env (endereço do túnel).")
    return s.public_base_url.rstrip("/") + "/webhooks/waha"


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
    adm.atualizar_clinica(conn, clinic_id, dados)
    if "status" in dados:
        adm.auditar(conn, usuario_da_requisicao(request).id, "suspender" if dados["status"] == "suspensa" else "reativar", clinic_id)
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
# WhatsApp da clínica (substitui o scripts/whatsapp.py — D31)
# ---------------------------------------------------------------------------
@router.get("/whatsapp/sessoes", summary="Sessões do servidor WAHA e a clínica ligada a cada uma")
def sessoes(conn=Depends(get_conn)):
    ligadas = {r[0]: {"clinic_id": r[1], "clinica": r[2]} for r in conn.execute(
        "select w.session, c.id, c.name from whatsapp_instances w join clinics c on c.id = w.clinic_id").fetchall()}
    try:
        lista = _waha().listar_sessoes()
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", str(e)) from e
    return [{"sessao": x.get("name"), "status": x.get("status"),
             "numero": ((x.get("me") or {}).get("id") or "").split("@")[0] or None,
             "webhooks": [w.get("url") for w in ((x.get("config") or {}).get("webhooks") or [])],
             **(ligadas.get(x.get("name")) or {"clinic_id": None, "clinica": None})} for x in lista]


@router.get("/clinicas/{clinic_id}/whatsapp", summary="Status do WhatsApp da clínica")
def whatsapp_status(clinic_id: UUID, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    r = conn.execute("select session from whatsapp_instances where clinic_id = %s", (clinic_id,)).fetchone()
    if not r:
        return {"ligado": False}
    try:
        info = _waha().sessao(r[0])
    except WahaErro as e:
        return {"ligado": True, **_instancia(conn, clinic_id), "erro": str(e)}
    status = info.get("status") or "DESCONHECIDO"
    numero = ((info.get("me") or {}).get("id") or "").split("@")[0] or None
    conn.execute("update whatsapp_instances set status = %s, phone = coalesce(%s, phone), updated_at = now() where clinic_id = %s",
                 (status, f"+{numero}" if numero else None, clinic_id))
    webhooks = [w.get("url") for w in ((info.get("config") or {}).get("webhooks") or [])]
    s = get_settings()
    esperado = (s.public_base_url.rstrip("/") + "/webhooks/waha") if s.public_base_url else None
    return {"ligado": True, **_instancia(conn, clinic_id), "webhooks": webhooks,
            "webhook_ok": bool(esperado and esperado in webhooks), "webhook_esperado": esperado}


@router.put("/clinicas/{clinic_id}/whatsapp", summary="Ligar a clínica a uma sessão do WAHA (existente ou nova)")
def whatsapp_ligar(clinic_id: UUID, body: LigarSessao, request: Request, criar: bool = False, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    if not SESSAO_VALIDA.match(body.sessao):
        raise AgendaError("DADOS_INVALIDOS", "Nome da sessão: só letras, números, - e _ (2 a 40).")
    dono = conn.execute("select clinic_id from whatsapp_instances where session = %s", (body.sessao,)).fetchone()
    if dono and dono[0] != clinic_id:
        raise AgendaError("DADOS_INVALIDOS", "Essa sessão já está ligada a outra clínica (1 número = 1 clínica, D29).")
    w = _waha()
    try:
        info = w.criar_sessao(body.sessao, _url_webhook(), get_settings().waha_webhook_hmac_key) if criar else w.sessao(body.sessao)
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", str(e)) from e
    conn.execute(
        """insert into whatsapp_instances (clinic_id, session, status) values (%s, %s, %s)
           on conflict (clinic_id) do update set session = excluded.session, status = excluded.status, updated_at = now()""",
        (clinic_id, body.sessao, info.get("status") or "STARTING"),
    )
    adm.auditar(conn, usuario_da_requisicao(request).id, "ligar_whatsapp", clinic_id, {"sessao": body.sessao, "nova": criar})
    avisar(conn, clinic_id, "whatsapp", clinic_id)
    return whatsapp_status(clinic_id, conn)


@router.delete("/clinicas/{clinic_id}/whatsapp", summary="Desligar a clínica da sessão (não mexe no WAHA)")
def whatsapp_desligar(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    conn.execute("delete from whatsapp_instances where clinic_id = %s", (clinic_id,))
    adm.auditar(conn, usuario_da_requisicao(request).id, "desligar_whatsapp", clinic_id)
    return {"ligado": False}


@router.post("/clinicas/{clinic_id}/whatsapp/webhook", summary="Apontar o webhook da sessão para este backend")
def whatsapp_webhook(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    inst = _instancia(conn, clinic_id)
    try:
        _waha().configurar_webhook(inst["sessao"], _url_webhook(), get_settings().waha_webhook_hmac_key)
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", str(e)) from e
    adm.auditar(conn, usuario_da_requisicao(request).id, "configurar_webhook", clinic_id, {"sessao": inst["sessao"]})
    return whatsapp_status(clinic_id, conn)


@router.post("/clinicas/{clinic_id}/whatsapp/reiniciar", summary="Reiniciar a sessão no WAHA")
def whatsapp_reiniciar(clinic_id: UUID, conn=Depends(get_conn)):
    inst = _instancia(conn, clinic_id)
    try:
        _waha().reiniciar(inst["sessao"])
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", str(e)) from e
    return {"ok": True}


@router.get("/clinicas/{clinic_id}/whatsapp/qr", summary="QR code para conectar o número (imagem PNG)")
def whatsapp_qr(clinic_id: UUID, conn=Depends(get_conn)):
    inst = _instancia(conn, clinic_id)
    try:
        png = _waha().qr_png(inst["sessao"])
    except WahaErro as e:
        raise AgendaError("ENVIO_FALHOU", f"QR indisponível agora (a sessão precisa estar em SCAN_QR_CODE). {e}") from e
    return Response(png, media_type="image/png", headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------
# IA da clínica vista pelo admin geral (D46): ligar/desligar "usar a chave da plataforma"
# ---------------------------------------------------------------------------
class UsoPlataforma(BaseModel):
    usa_plataforma: bool


@router.get("/clinicas/{clinic_id}/ia", summary="Situação da IA da clínica")
def ia_da_clinica(clinic_id: UUID, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    return ia.estado_publico(conn, clinic_id)


@router.put("/clinicas/{clinic_id}/ia", summary="Ligar/desligar o uso da chave da plataforma")
def ia_plataforma(clinic_id: UUID, body: UsoPlataforma, request: Request, conn=Depends(get_conn)):
    _existe(conn, clinic_id)
    ia.usar_plataforma(conn, clinic_id, body.usa_plataforma, usuario_da_requisicao(request).id)
    return ia.estado_publico(conn, clinic_id)


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
                     and r.created_at >= date_trunc('month', now())) as tempo_medio_s,
                  (select count(*) from agent_runs r where r.clinic_id = c.id and r.error is not null
                     and r.created_at >= date_trunc('month', now())) as falhas_ia,
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
