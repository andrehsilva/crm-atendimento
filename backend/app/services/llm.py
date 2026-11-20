"""Cliente do modelo de IA (OpenCode Go, API compatível com OpenAI — decisão D13)."""

from openai import OpenAI

from app.config import Settings

USER_AGENT = "isis-atendimento/0.1"


def cliente_llm(s: Settings, sessao: str) -> OpenAI:
    """Cria o cliente. `sessao` deve ser estável por conversa (cabeçalho x-opencode-session)."""
    return OpenAI(
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
        timeout=30,
        max_retries=1,
        default_headers={"User-Agent": USER_AGENT, "x-opencode-session": sessao},
    )
