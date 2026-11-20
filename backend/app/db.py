"""Conexões com o Postgres (Supabase). Um pool reaproveita conexões — abrir uma nova leva ~2 s."""

from collections.abc import Iterator

import psycopg
from psycopg_pool import ConnectionPool

from app.config import get_settings

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        url = get_settings().database_url
        if not url:
            raise RuntimeError("DATABASE_URL vazia no backend/.env")
        _pool = ConnectionPool(
            url,
            min_size=1,
            max_size=5,
            open=True,
            kwargs={"connect_timeout": 10},
            check=ConnectionPool.check_connection,  # descarta conexões que o servidor derrubou
            max_idle=300,
        )
    return _pool


def fechar_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_conn() -> Iterator[psycopg.Connection]:
    """Dependência do FastAPI: uma conexão por requisição. Confirma se der certo; desfaz se der erro."""
    with pool().connection() as conn:
        yield conn
