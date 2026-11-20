from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.services.checks import checar_banco, checar_ia

router = APIRouter(tags=["saúde"])


@router.get("/health")
async def health(ia: bool = Query(False, description="Também testa o modelo de IA (gasta poucos tokens)")) -> dict:
    """Mostra se o servidor está de pé, se o banco conecta e (opcional) se a IA responde."""
    s = get_settings()
    banco = await run_in_threadpool(checar_banco, s)
    if ia:
        ia_info = await run_in_threadpool(checar_ia, s)
    else:
        ia_info = {"status": "configurada" if s.llm_api_key else "não configurada"}
    return {"status": "ok", "app": s.app_name, "env": s.env, "banco": banco, "ia": ia_info,
            "chat_teste": s.chat_teste_liberado}
