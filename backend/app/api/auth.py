"""Login do painel (D34, D35): entrar, sair, quem sou eu, trocar senha e "Esqueci minha senha"."""

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.agenda.erros import AgendaError
from app.auth import acesso as A
from app.auth import supabase as sb
from app.config import get_settings
from app.db import get_conn

router = APIRouter(prefix="/api/auth", tags=["login"])
SENHA_MIN = 8


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    senha: str = Field(min_length=1, max_length=200)


class TrocaSenha(BaseModel):
    atual: str = Field(min_length=1, max_length=200)
    nova: str = Field(max_length=200)


class Esqueci(BaseModel):
    email: str = Field(min_length=3, max_length=200)


class Redefinir(BaseModel):
    access_token: str = Field(min_length=10, max_length=5000)
    nova: str = Field(max_length=200)


def validar_senha(nova: str, atual: str | None = None) -> None:
    if len(nova) < SENHA_MIN:
        raise AgendaError("SENHA_FRACA", f"A senha precisa ter pelo menos {SENHA_MIN} caracteres.")
    if not (any(c.isalpha() for c in nova) and any(c.isdigit() for c in nova)):
        raise AgendaError("SENHA_FRACA", "Use letras e números na senha.")
    if atual is not None and nova == atual:
        raise AgendaError("SENHA_FRACA", "A nova senha precisa ser diferente da atual.")


def _erro(e: sb.AuthErro) -> AgendaError:
    return AgendaError("NAO_AUTENTICADO" if e.status in (400, 401, 403) else "ENVIO_FALHOU", e.mensagem)


@router.post("/login", summary="Entrar com e-mail e senha")
def entrar(body: Login, response: Response, conn=Depends(get_conn)):
    try:
        sessao = sb.login(body.email.strip().lower(), body.senha)
    except sb.AuthErro as e:
        raise _erro(e) from e
    usuario = A._carregar(conn, sessao.user_id)  # sem perfil no sistema → SEM_ACESSO
    A.gravar_cookies(response, sessao)
    return usuario.publico()


@router.get("/me", summary="Quem está logado")
def quem_sou(request: Request, response: Response, conn=Depends(get_conn)):
    return A.obter_usuario(request, response, conn).publico()


@router.post("/logout", summary="Sair")
def sair(request: Request, response: Response):
    if token := request.cookies.get(A.COOKIE_ACESSO):
        sb.sair(token)
    A.apagar_cookies(response)
    return {"ok": True}


@router.post("/trocar-senha", summary="Trocar a senha (inclusive a provisória do 1º acesso)")
def trocar_senha(body: TrocaSenha, request: Request, response: Response, conn=Depends(get_conn)):
    u = A.obter_usuario(request, response, conn)
    validar_senha(body.nova, body.atual)
    try:
        sb.login(u.email, body.atual)  # confere a senha atual
    except sb.AuthErro as e:
        raise AgendaError("NAO_AUTENTICADO", "A senha atual está incorreta.") from e
    try:
        sb.definir_senha(str(u.id), body.nova)
        nova_sessao = sb.login(u.email, body.nova)
    except sb.AuthErro as e:
        raise _erro(e) from e
    conn.execute("update app_users set must_change_password = false where user_id = %s", (u.id,))
    A.gravar_cookies(response, nova_sessao)
    u.trocar_senha = False
    return u.publico()


@router.post("/esqueci", summary="Manda o e-mail para criar uma nova senha")
def esqueci(body: Esqueci):
    destino = get_settings().frontend_origin.rstrip("/") + "/redefinir-senha"
    sb.recuperar_senha(body.email.strip().lower(), destino)
    return {"ok": True, "mensagem": "Se o e-mail estiver cadastrado, você vai receber um link para criar uma nova senha."}


@router.post("/redefinir", summary="Cria a nova senha a partir do link do e-mail")
def redefinir(body: Redefinir, conn=Depends(get_conn)):
    validar_senha(body.nova)
    try:
        claims = sb.conferir_token(body.access_token)
        sb.trocar_senha_com_token(body.access_token, body.nova)
    except sb.TokenExpirado as e:
        raise AgendaError("NAO_AUTENTICADO", "O link expirou. Peça um novo em \"Esqueci minha senha\".") from e
    except sb.AuthErro as e:
        raise _erro(e) from e
    conn.execute("update app_users set must_change_password = false where user_id = %s", (claims["sub"],))
    return {"ok": True}
