"""Verificações de conexão usadas pelo /health e pelo script de teste.

Nunca devolvem segredos: só "ok" ou uma mensagem de erro curta.
"""

import time

import psycopg

from app.config import Settings
from app.services.llm import cliente_llm


def checar_banco(s: Settings) -> dict:
    if not s.database_url:
        return {"status": "não configurado"}
    inicio = time.perf_counter()
    try:
        with psycopg.connect(s.database_url, connect_timeout=5) as conn:
            versao = conn.execute("select current_setting('server_version')").fetchone()[0]
        return {"status": "ok", "postgres": versao, "ms": round((time.perf_counter() - inicio) * 1000)}
    except Exception as e:  # noqa: BLE001 — queremos mostrar qualquer falha de conexão
        return {"status": "erro", "detalhe": _resumo_erro(e)}


def checar_ia(s: Settings) -> dict:
    """Manda uma mensagem curtíssima ao modelo. Gasta poucos tokens; use sob demanda."""
    if not s.llm_api_key:
        return {"status": "não configurada"}
    inicio = time.perf_counter()
    try:
        resp = cliente_llm(s, sessao="health-check").responses.create(
            model=s.llm_model,
            input="Responda apenas: ok",
            max_output_tokens=16,
        )
        return {
            "status": "ok",
            "modelo": s.llm_model,
            "resposta": (resp.output_text or "").strip()[:40],
            "ms": round((time.perf_counter() - inicio) * 1000),
        }
    except Exception as e:  # noqa: BLE001
        return {"status": "erro", "detalhe": _resumo_erro(e)}


def _resumo_erro(e: Exception) -> str:
    texto = f"{type(e).__name__}: {e}"
    return texto.splitlines()[0][:200]
