"""Cria (ou recria) a clínica de demonstração com dados de exemplo.

Uso (na pasta backend):
    uv run python scripts/seed_demo.py            # cria se não existir
    uv run python scripts/seed_demo.py --reset    # apaga a clínica demo e cria de novo
"""

import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.demo import TELEFONE_CLINICA, criar_demo  # noqa: E402


def main() -> int:
    with psycopg.connect(get_settings().database_url) as conn:
        clinic_id = criar_demo(conn, reset="--reset" in sys.argv)
    print(f"Clínica demo pronta — id {clinic_id} — telefone (chave) {TELEFONE_CLINICA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
