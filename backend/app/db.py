"""Conexões com o Postgres (Supabase). Um pool reaproveita conexões — abrir uma nova leva ~2 s."""

import time
import weakref
from collections.abc import Iterator

import psycopg
from psycopg_pool import ConnectionPool

from app.config import get_settings

_pool: ConnectionPool | None = None
_usada_em: "weakref.WeakKeyDictionary[psycopg.Connection, float]" = weakref.WeakKeyDictionary()
PARADA_S = 30  # conexão usada há menos que isso não precisa ser conferida


def _conferir(conn: psycopg.Connection) -> None:
    """Etapa 32: conferir a conexão custa uma ida e volta ao banco (~0,2 s com o servidor longe dele).
    Só confere a que ficou parada um tempo — é essa que o servidor do banco pode ter derrubado."""
    if time.monotonic() - _usada_em.get(conn, 0) < PARADA_S:
        return
    ConnectionPool.check_connection(conn)


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
            check=_conferir,  # descarta conexões que o servidor derrubou (só confere as paradas)
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
        try:
            yield conn
        finally:
            _usada_em[conn] = time.monotonic()
