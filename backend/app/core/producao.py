"""Checagens de produção (Etapa 8B): em ENV=prod o backend NÃO sobe com configuração perigosa ou incompleta.

Melhor o servidor recusar subir (e o log dizer o motivo) do que atender clínicas sem assinatura no webhook,
sem HTTPS ou com o chat de teste aberto.
"""

from app.config import Settings

OBRIGATORIAS = {
    "database_url": "DATABASE_URL",
    "supabase_url": "SUPABASE_URL",
    "supabase_anon_key": "SUPABASE_ANON_KEY",
    "supabase_service_role_key": "SUPABASE_SERVICE_ROLE_KEY",
    "llm_api_key": "LLM_API_KEY",
    "waha_api_url": "WAHA_API_URL",
    "waha_api_key": "WAHA_API_KEY",
    "waha_webhook_hmac_key": "WAHA_WEBHOOK_HMAC_KEY",
    "public_base_url": "PUBLIC_BASE_URL",
    "frontend_origin": "FRONTEND_ORIGIN",
}


def problemas(s: Settings) -> list[str]:
    """Lista o que impede subir em produção. Vazia = tudo certo (ou estamos em dev)."""
    if not s.producao:
        return []
    erros = [f"{nome} está vazia" for campo, nome in OBRIGATORIAS.items() if not getattr(s, campo)]
    for campo, nome in (("public_base_url", "PUBLIC_BASE_URL"), ("frontend_origin", "FRONTEND_ORIGIN")):
        valor = getattr(s, campo)
        if valor and not valor.startswith("https://"):
            erros.append(f"{nome} precisa começar com https:// (está {valor!r})")
        if "localhost" in valor or "trycloudflare.com" in valor:
            erros.append(f"{nome} ainda aponta para desenvolvimento ({valor!r})")
    if s.waha_webhook_hmac_key and len(s.waha_webhook_hmac_key) < 32:
        erros.append("WAHA_WEBHOOK_HMAC_KEY curta demais (use 32+ caracteres aleatórios)")
    if s.chat_teste:
        erros.append("CHAT_TESTE=true em produção expõe conversas de pacientes: remova a linha do .env")
    return erros
