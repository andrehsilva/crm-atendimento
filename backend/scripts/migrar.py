"""Aplica as migrations de supabase/migrations/ no banco, em ordem, uma única vez cada.

Uso (na pasta backend):  uv run python scripts/migrar.py
Cada arquivo roda numa transação: se der erro, nada daquele arquivo fica pela metade.
"""

import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402

PASTA = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def main() -> int:
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL vazia no backend/.env")
        return 1

    arquivos = sorted(PASTA.glob("*.sql"))
    with psycopg.connect(s.database_url, autocommit=True) as conn:
        conn.execute(
            "create table if not exists schema_migrations ("
            " nome text primary key, aplicada_em timestamptz not null default now())"
        )
        conn.execute("alter table schema_migrations enable row level security")
        feitas = {r[0] for r in conn.execute("select nome from schema_migrations")}

        pendentes = [a for a in arquivos if a.name not in feitas]
        if not pendentes:
            print("Nada a aplicar: banco já está atualizado.")
            return 0

        for arq in pendentes:
            print(f"Aplicando {arq.name} ...", end=" ")
            with conn.transaction():
                conn.execute(arq.read_text(encoding="utf-8"))
                conn.execute("insert into schema_migrations (nome) values (%s)", (arq.name,))
            print("ok")
    print(f"{len(pendentes)} migration(s) aplicada(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
