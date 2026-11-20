"""Criação de usuários com senha provisória (D35). Usado pelo script e, na 7B, pela tela do admin geral."""

import secrets
import string
from uuid import UUID

from app.agenda.erros import AgendaError
from app.auth import supabase as sb

PAPEIS = ("clinic_admin", "reception")


def senha_provisoria() -> str:
    """12 caracteres com letras e números, sem os que se confundem (0/O, 1/l/I)."""
    letras = "".join(c for c in string.ascii_letters if c not in "OlI")
    numeros = "23456789"
    while True:
        s = "".join(secrets.choice(letras + numeros) for _ in range(12))
        if any(c in numeros for c in s) and any(c in letras for c in s):
            return s


def criar_ou_ligar(conn, email: str, nome: str | None = None, *, super_admin: bool = False,
                   clinic_id: UUID | None = None, papel: str | None = None) -> tuple[UUID, str | None]:
    """Cria o usuário (ou reaproveita, se o e-mail já existe) e dá o papel pedido.

    Devolve (id, senha_provisoria). A senha só vem quando o usuário é NOVO — mostre uma vez e não guarde.
    """
    email = email.strip().lower()
    if "@" not in email:
        raise AgendaError("DADOS_INVALIDOS", "E-mail inválido.")
    if clinic_id and papel not in PAPEIS:
        raise AgendaError("DADOS_INVALIDOS", f"Papel inválido: {papel}")

    senha = None
    existente = conn.execute("select user_id from app_users where email = %s", (email,)).fetchone()
    if existente:
        user_id = existente[0]
    else:
        uid = sb.buscar_usuario_por_email(email)
        if uid is None:
            senha = senha_provisoria()
            uid = sb.criar_usuario(email, senha, nome)
        user_id = UUID(uid)
        conn.execute(
            """insert into app_users (user_id, email, name, must_change_password) values (%s, %s, %s, %s)
               on conflict (user_id) do nothing""",
            (user_id, email, nome, senha is not None),
        )

    if super_admin:
        conn.execute("insert into platform_admins (user_id) values (%s) on conflict do nothing", (user_id,))
    if clinic_id:
        conn.execute(
            """insert into clinic_users (clinic_id, user_id, role) values (%s, %s, %s)
               on conflict (clinic_id, user_id) do update set role = excluded.role, active = true""",
            (clinic_id, user_id, papel),
        )
    return user_id, senha
