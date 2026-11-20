"""Quem está logado e o que pode acessar (spec 01, RN-MT-03, D34).

O "crachá" (token do Supabase) fica num cookie httpOnly — o JavaScript da página não consegue lê-lo.
Quando vence, é renovado automaticamente com o cookie de renovação.

Regra de ouro: toda rota com {clinic_id} (no caminho ou na consulta) só responde para quem é da clínica,
ou para o super admin. Isso é conferido ANTES da rota rodar, para todas as rotas do painel.
"""

from dataclasses import dataclass, field
from uuid import UUID

from fastapi import Depends, Request, Response

from app.agenda.erros import AgendaError
from app.auth import supabase as sb
from app.config import get_settings
from app.db import get_conn

COOKIE_ACESSO = "isis_at"
COOKIE_RENOVACAO = "isis_rt"
RENOVACAO_DIAS = 30

# Abertos de propósito: chat web de TESTE (D15) e webhooks (protegidos pela assinatura HMAC)
ROTAS_PUBLICAS = ("/api/web/", "/api/auth/")


@dataclass
class Usuario:
    id: UUID
    email: str
    nome: str | None
    super_admin: bool
    trocar_senha: bool
    clinicas: dict[UUID, str] = field(default_factory=dict)  # clinic_id → papel

    def papel(self, clinic_id: UUID) -> str | None:
        if self.super_admin:
            return "super_admin"
        return self.clinicas.get(clinic_id)

    def publico(self) -> dict:
        return {
            "id": str(self.id), "email": self.email, "nome": self.nome, "super_admin": self.super_admin,
            "trocar_senha": self.trocar_senha,
            "clinicas": [{"clinic_id": str(c), "papel": p} for c, p in self.clinicas.items()],
        }


def gravar_cookies(response: Response, sessao: sb.Sessao) -> None:
    seguro = get_settings().producao  # em produção o cookie só viaja por HTTPS
    response.set_cookie(COOKIE_ACESSO, sessao.access_token, max_age=sessao.expires_in, httponly=True,
                        secure=seguro, samesite="lax", path="/")
    response.set_cookie(COOKIE_RENOVACAO, sessao.refresh_token, max_age=RENOVACAO_DIAS * 86400, httponly=True,
                        secure=seguro, samesite="lax", path="/")


def apagar_cookies(response: Response) -> None:
    response.delete_cookie(COOKIE_ACESSO, path="/")
    response.delete_cookie(COOKIE_RENOVACAO, path="/")


def _carregar(conn, user_id: str) -> Usuario:
    r = conn.execute(
        "select user_id, email, name, must_change_password, active from app_users where user_id = %s", (user_id,)
    ).fetchone()
    if not r or not r[4]:
        raise AgendaError("SEM_ACESSO", "Seu usuário não tem acesso ao sistema. Fale com o administrador.")
    admin = conn.execute("select 1 from platform_admins where user_id = %s", (user_id,)).fetchone() is not None
    clinicas = {
        cid: papel for cid, papel in conn.execute(
            """select cu.clinic_id, cu.role from clinic_users cu join clinics c on c.id = cu.clinic_id
               where cu.user_id = %s and cu.active and c.status = 'ativa'""", (user_id,)
        ).fetchall()
    }
    return Usuario(id=r[0], email=r[1], nome=r[2], super_admin=admin, trocar_senha=r[3], clinicas=clinicas)


def obter_usuario(request: Request, response: Response | None, conn, pode_renovar: bool = True) -> Usuario:
    """Lê o crachá do cookie. Se venceu e der para renovar, renova e grava os cookies novos na resposta."""
    token = request.cookies.get(COOKIE_ACESSO)
    renovacao = request.cookies.get(COOKIE_RENOVACAO)
    claims = None
    if token:
        try:
            claims = sb.conferir_token(token)
        except sb.TokenExpirado:
            claims = None
        except sb.AuthErro:
            claims = None
    if claims is None:
        if not (renovacao and pode_renovar and response is not None):
            raise AgendaError("NAO_AUTENTICADO", "Entre com seu e-mail e senha.")
        try:
            nova = sb.renovar(renovacao)
        except sb.AuthErro as e:
            raise AgendaError("NAO_AUTENTICADO", e.mensagem) from e
        gravar_cookies(response, nova)
        claims = sb.conferir_token(nova.access_token)
    return _carregar(conn, claims["sub"])


def _clinica_pedida(request: Request) -> UUID | None:
    bruto = request.path_params.get("clinic_id") or request.query_params.get("clinic_id")
    if not bruto:
        return None
    try:
        return UUID(str(bruto))
    except ValueError as e:
        raise AgendaError("CLINICA_NAO_ENCONTRADA", "Clínica não encontrada.") from e


def acesso(request: Request, response: Response, conn=Depends(get_conn)) -> Usuario | None:
    """Dependência de TODAS as rotas do painel (colocada no router)."""
    if request.url.path.startswith(ROTAS_PUBLICAS):
        return None
    # A conexão de eventos (SSE) não consegue gravar cookie novo: se o crachá venceu, a tela renova e reconecta.
    usuario = obter_usuario(request, response, conn, pode_renovar=not request.url.path.endswith("/events"))
    if usuario.trocar_senha:
        raise AgendaError("TROCAR_SENHA", "Troque a senha provisória antes de continuar.")
    clinic_id = _clinica_pedida(request)
    if clinic_id and not usuario.papel(clinic_id):
        raise AgendaError("SEM_ACESSO", "Você não tem acesso a esta clínica.")
    request.state.usuario = usuario
    return usuario


def usuario_da_requisicao(request: Request) -> Usuario:
    u = getattr(request.state, "usuario", None)
    if u is None:
        raise AgendaError("NAO_AUTENTICADO", "Entre com seu e-mail e senha.")
    return u


def exigir_admin_clinica(request: Request, clinic_id: UUID) -> Usuario:
    """Configurações da clínica: só o admin da clínica (ou o super admin)."""
    u = usuario_da_requisicao(request)
    if u.papel(clinic_id) not in ("clinic_admin", "super_admin"):
        raise AgendaError("SEM_ACESSO", "Só o administrador da clínica pode mudar as configurações.")
    return u


def exigir_super_admin(request: Request) -> Usuario:
    u = usuario_da_requisicao(request)
    if not u.super_admin:
        raise AgendaError("SEM_ACESSO", "Só o administrador da plataforma pode fazer isso.")
    return u
