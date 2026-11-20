"""Criar usuários do painel com senha provisória (D35) — até a tela do admin geral (Etapa 7B).

Uso (na pasta backend):
    uv run python scripts/usuarios.py super-admin voce@exemplo.com "Seu Nome"
    uv run python scripts/usuarios.py clinica demo clinic_admin pessoa@exemplo.com "Nome"
    uv run python scripts/usuarios.py clinica demo reception pessoa@exemplo.com "Nome"
    uv run python scripts/usuarios.py listar

A senha provisória aparece UMA vez. No 1º acesso o sistema pede para trocar.
"""

import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agenda.erros import AgendaError  # noqa: E402
from app.auth.supabase import AuthErro  # noqa: E402
from app.auth.usuarios import criar_ou_ligar  # noqa: E402
from app.config import get_settings  # noqa: E402


def _mostrar(email: str, senha: str | None) -> None:
    if senha:
        print(f"\n✅ Usuário criado: {email}\n   Senha provisória: {senha}\n   (anote agora — ela não aparece de novo; será trocada no 1º acesso)")
    else:
        print(f"\n✅ {email} já existia; papel atualizado. A senha continua a mesma.")


def main(a: list[str]) -> int:
    with psycopg.connect(get_settings().database_url) as conn:
        if a[:1] == ["super-admin"] and len(a) in (2, 3):
            _, senha = criar_ou_ligar(conn, a[1], a[2] if len(a) == 3 else None, super_admin=True)
            conn.commit()
            _mostrar(a[1], senha)
            return 0
        if a[:1] == ["clinica"] and len(a) in (4, 5):
            r = conn.execute("select id from clinics where slug = %s", (a[1],)).fetchone()
            if not r:
                raise SystemExit(f"Clínica '{a[1]}' não encontrada.")
            _, senha = criar_ou_ligar(conn, a[3], a[4] if len(a) == 5 else None, clinic_id=r[0], papel=a[2])
            conn.commit()
            _mostrar(a[3], senha)
            return 0
        if a == ["listar"]:
            for email, nome, admin, papeis in conn.execute(
                """select u.email, u.name, pa.user_id is not null,
                          string_agg(c.slug || ':' || cu.role, ', ')
                   from app_users u left join platform_admins pa on pa.user_id = u.user_id
                   left join clinic_users cu on cu.user_id = u.user_id left join clinics c on c.id = cu.clinic_id
                   group by u.email, u.name, pa.user_id order by u.email"""
            ).fetchall():
                print(f"- {email} ({nome or 'sem nome'})" + (" [super admin]" if admin else "") + (f" {papeis}" if papeis else ""))
            return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (AuthErro, AgendaError) as e:
        raise SystemExit(f"❌ {getattr(e, 'mensagem', e)}") from None
