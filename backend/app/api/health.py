from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["saúde"])


@router.get("/health")
def health() -> dict:
    """Mostra se o servidor está de pé e o que já está configurado."""
    s = get_settings()
    return {
        "status": "ok",
        "app": s.app_name,
        "env": s.env,
        # Etapa 1B: aqui passaremos a testar a conexão de verdade.
        "banco": "configurado" if s.database_url else "não configurado",
        "ia": "configurada" if s.llm_api_key else "não configurada",
    }
