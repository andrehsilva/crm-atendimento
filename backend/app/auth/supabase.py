"""Conversa com o Supabase Auth (D34). A senha nunca passa pelo nosso banco.

- login/renovação/recuperação usam a chave pública (publishable);
- criar usuário e trocar senha pelo admin usam a chave secret (só no backend, no .env);
- o token de acesso é conferido localmente com a chave pública de assinatura (JWKS, ES256).
"""

import logging
from dataclasses import dataclass
from functools import lru_cache

import httpx
import jwt

from app.config import Settings, get_settings
from app.services.llm import USER_AGENT

log = logging.getLogger("isis.auth")


class AuthErro(Exception):
    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


@dataclass
class Sessao:
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str


def _base(s: Settings) -> str:
    if not (s.supabase_url and s.supabase_anon_key):
        raise AuthErro("SUPABASE_URL e SUPABASE_ANON_KEY precisam estar no backend/.env", 503)
    return s.supabase_url.rstrip("/") + "/auth/v1"


def _req(metodo: str, caminho: str, *, chave: str, token: str | None = None, s: Settings | None = None, **kw) -> dict:
    s = s or get_settings()
    headers = {"apikey": chave, "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = httpx.request(metodo, _base(s) + caminho, headers=headers, timeout=15, **kw)
    except httpx.HTTPError as e:
        raise AuthErro("Não foi possível falar com o serviço de login. Tente de novo.", 503) from e
    if r.status_code >= 400:
        try:
            d = r.json()
        except ValueError:
            d = {}
        msg = d.get("msg") or d.get("error_description") or d.get("message") or r.text[:200]
        log.info("Supabase Auth %s %s → %s: %s", metodo, caminho, r.status_code, msg)
        raise AuthErro(msg, r.status_code)
    return r.json() if r.content else {}


def _sessao(d: dict) -> Sessao:
    return Sessao(d["access_token"], d["refresh_token"], int(d.get("expires_in", 3600)), d["user"]["id"])


def login(email: str, senha: str) -> Sessao:
    s = get_settings()
    try:
        return _sessao(_req("POST", "/token", params={"grant_type": "password"}, chave=s.supabase_anon_key,
                            json={"email": email, "password": senha}))
    except AuthErro as e:
        if e.status in (400, 401):
            raise AuthErro("E-mail ou senha incorretos.", 401) from e
        raise


def renovar(refresh_token: str) -> Sessao:
    s = get_settings()
    try:
        return _sessao(_req("POST", "/token", params={"grant_type": "refresh_token"}, chave=s.supabase_anon_key,
                            json={"refresh_token": refresh_token}))
    except AuthErro as e:
        raise AuthErro("Sua sessão expirou. Entre de novo.", 401) from e


def sair(access_token: str) -> None:
    s = get_settings()
    try:
        _req("POST", "/logout", chave=s.supabase_anon_key, token=access_token)
    except AuthErro:
        pass  # sair nunca falha para o usuário


def recuperar_senha(email: str, redirecionar_para: str) -> None:
    s = get_settings()
    try:
        _req("POST", "/recover", chave=s.supabase_anon_key, params={"redirect_to": redirecionar_para}, json={"email": email})
    except AuthErro as e:
        log.warning("recuperação de senha falhou: %s", e.mensagem)  # não revela se o e-mail existe


def trocar_senha_com_token(access_token: str, nova: str) -> None:
    s = get_settings()
    _req("PUT", "/user", chave=s.supabase_anon_key, token=access_token, json={"password": nova})


# ---- admin (chave secret) --------------------------------------------------
def _chave_admin(s: Settings) -> str:
    if not s.supabase_service_role_key:
        raise AuthErro("SUPABASE_SERVICE_ROLE_KEY vazia no backend/.env", 503)
    return s.supabase_service_role_key


def criar_usuario(email: str, senha: str, nome: str | None = None) -> str:
    s = get_settings()
    d = _req("POST", "/admin/users", chave=_chave_admin(s), json={
        "email": email, "password": senha, "email_confirm": True, "user_metadata": {"name": nome} if nome else {},
    })
    return d["id"]


def buscar_usuario_por_email(email: str) -> str | None:
    s = get_settings()
    pagina = 1
    while pagina < 50:
        d = _req("GET", "/admin/users", chave=_chave_admin(s), params={"page": pagina, "per_page": 200})
        usuarios = d.get("users", [])
        for u in usuarios:
            if (u.get("email") or "").lower() == email.lower():
                return u["id"]
        if len(usuarios) < 200:
            return None
        pagina += 1
    return None


def definir_senha(user_id: str, senha: str) -> None:
    s = get_settings()
    _req("PUT", f"/admin/users/{user_id}", chave=_chave_admin(s), json={"password": senha})


# ---- conferência do token --------------------------------------------------
@lru_cache
def _jwks() -> jwt.PyJWKClient:
    s = get_settings()
    return jwt.PyJWKClient(_base(s) + "/.well-known/jwks.json", cache_keys=True, lifespan=3600,
                           headers={"apikey": s.supabase_anon_key, "User-Agent": USER_AGENT})


class TokenExpirado(Exception):
    pass


def conferir_token(token: str) -> dict:
    """Devolve os dados do token (sub = id do usuário). TokenExpirado se venceu; AuthErro se for inválido."""
    s = get_settings()
    try:
        chave = _jwks().get_signing_key_from_jwt(token).key
        return jwt.decode(token, chave, algorithms=["ES256", "RS256"], audience="authenticated",
                          issuer=_base(s), leeway=10)
    except jwt.ExpiredSignatureError as e:
        raise TokenExpirado from e
    except (jwt.PyJWTError, jwt.PyJWKClientError) as e:
        raise AuthErro("Sessão inválida. Entre de novo.", 401) from e
