"""IA de cada clínica (Etapa 10A — D42, D43, D46).

- A clínica cadastra a própria chave (Google, OpenAI, OpenCode ou OpenRouter) e escolhe o modelo.
- A chave é guardada CRIPTOGRAFADA (Fernet; a chave-mestra fica só no .env em IA_CHAVE_MESTRA)
  e nunca volta para a tela: só os 4 últimos caracteres.
- Ordem: chave da clínica → "usar a chave da plataforma" (ligado pelo admin geral) → desligada.
- Mensagens de erro do provedor nunca são repassadas cruas (algumas repetem parte da chave).
"""

from dataclasses import dataclass
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from openai import (APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, NotFoundError,
                    OpenAI, PermissionDeniedError, RateLimitError)

from app.config import get_settings

USER_AGENT = "isis-atendimento/0.1"

# estilo "responses" = API Responses da OpenAI; "chat" = Chat Completions (o que Google e OpenRouter aceitam)
PROVEDORES: dict[str, dict] = {
    "google": {"nome": "Google (Gemini)", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
               "estilo": "chat", "onde": "aistudio.google.com › Get API key"},
    "openai": {"nome": "OpenAI", "base_url": "https://api.openai.com/v1",
               "estilo": "responses", "onde": "platform.openai.com › API keys"},
    "opencode": {"nome": "OpenCode", "base_url": "https://opencode.ai/inference/go/openai/v1",
                 "estilo": "responses", "onde": "opencode.ai › API Keys"},
    "openrouter": {"nome": "OpenRouter", "base_url": "https://openrouter.ai/api/v1",
                   "estilo": "chat", "onde": "openrouter.ai › Keys"},
}

# D43: só entram na lista sugerida os modelos que passaram na bateria de cenários (scripts/cenarios.py).
# Os outros podem ser digitados, com o aviso de que ainda não foram testados.
MODELOS_APROVADOS: dict[str, list[str]] = {
    "opencode": ["gpt-6-luna"],
}


class ChaveMestraAusente(RuntimeError):
    pass


@dataclass
class ConfigIA:
    origem: str  # "clinica" ou "plataforma"
    provedor: str
    modelo: str
    base_url: str
    estilo: str
    api_key: str


# ---------------------------------------------------------------------------
# Criptografia
# ---------------------------------------------------------------------------
def _fernet() -> Fernet:
    chave = get_settings().ia_chave_mestra
    if not chave:
        raise ChaveMestraAusente("IA_CHAVE_MESTRA não configurada no backend/.env")
    return Fernet(chave.encode())


def chave_mestra_valida(chave: str) -> bool:
    try:
        Fernet(chave.encode())
        return True
    except (ValueError, TypeError):
        return False


def cifrar(texto: str) -> bytes:
    return _fernet().encrypt(texto.encode())


def decifrar(dados: bytes) -> str | None:
    """None se a chave-mestra mudou (a chave salva precisa ser cadastrada de novo)."""
    try:
        return _fernet().decrypt(bytes(dados)).decode()
    except InvalidToken:
        return None


def final_da_chave(chave: str) -> str:
    return chave[-4:]


# ---------------------------------------------------------------------------
# Qual IA a clínica usa
# ---------------------------------------------------------------------------
def _linha(conn, clinic_id: UUID):
    return conn.execute(
        "select provider, model, key_cipher, usa_plataforma from clinic_ai where clinic_id = %s", (clinic_id,)
    ).fetchone()


def da_plataforma() -> ConfigIA | None:
    s = get_settings()
    if not s.llm_api_key:
        return None
    return ConfigIA("plataforma", s.llm_provider, s.llm_model, s.llm_base_url,
                    "chat" if s.llm_api_style == "chat" else "responses", s.llm_api_key)


def config_da_clinica(conn, clinic_id: UUID) -> ConfigIA | None:
    """A IA que a clínica usa agora, ou None (assistente desligada — D46)."""
    r = _linha(conn, clinic_id)
    if not r:
        return None
    provedor, modelo, cifra, usa_plataforma = r
    if cifra is not None and provedor in PROVEDORES:
        try:
            chave = decifrar(cifra)
        except ChaveMestraAusente:
            chave = None
        if chave:
            p = PROVEDORES[provedor]
            return ConfigIA("clinica", provedor, modelo, p["base_url"], p["estilo"], chave)
    return da_plataforma() if usa_plataforma else None


def cliente(cfg: ConfigIA, sessao: str, timeout: float = 30) -> OpenAI:
    cabecalhos = {"User-Agent": USER_AGENT}
    if cfg.provedor.startswith("opencode"):
        cabecalhos["x-opencode-session"] = sessao  # mantém o cache do OpenCode por conversa
    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url, timeout=timeout, max_retries=1, default_headers=cabecalhos)


def modelo_agno(cfg: ConfigIA, sessao: str):
    """Modelo do Agno para a Ísis, conforme o estilo da API do provedor."""
    from agno.models.openai import OpenAIChat, OpenAIResponses

    cabecalhos = {"User-Agent": USER_AGENT}
    if cfg.provedor.startswith("opencode"):
        cabecalhos["x-opencode-session"] = sessao
    comum = dict(id=cfg.modelo, api_key=cfg.api_key, base_url=cfg.base_url, default_headers=cabecalhos,
                 client_params={"timeout": 60, "max_retries": 1})
    if cfg.estilo == "responses":
        return OpenAIResponses(store=False, **comum)  # store=False: não guardar conversas no provedor
    return OpenAIChat(**comum)


# ---------------------------------------------------------------------------
# Testar conexão
# ---------------------------------------------------------------------------
def explicar_erro(e: Exception) -> str:
    """Texto curto em português. Nunca repassa a mensagem do provedor (pode conter parte da chave)."""
    if isinstance(e, AuthenticationError):
        return "O provedor recusou a chave. Confira se copiou a chave inteira e se ela está ativa."
    if isinstance(e, PermissionDeniedError):
        return "A chave não tem permissão para este modelo."
    if isinstance(e, NotFoundError):
        return "O provedor não encontrou este modelo. Confira o nome exato do modelo."
    if isinstance(e, RateLimitError):
        return "O provedor recusou por limite de uso ou falta de saldo na conta."
    if isinstance(e, APITimeoutError):
        return "O provedor demorou demais para responder. Tente de novo."
    if isinstance(e, APIConnectionError):
        return "Não foi possível falar com o provedor (rede ou endereço)."
    if isinstance(e, APIStatusError):
        return f"O provedor respondeu com erro {e.status_code}."
    return "Falha inesperada ao falar com o provedor."


def testar(cfg: ConfigIA) -> dict:
    """Manda uma mensagem curtíssima. Gasta pouquíssimos tokens da conta da clínica."""
    import time

    inicio = time.perf_counter()
    try:
        c = cliente(cfg, sessao="teste-conexao", timeout=30)
        if cfg.estilo == "responses":
            r = c.responses.create(model=cfg.modelo, input="Responda apenas: ok", max_output_tokens=16, store=False)
            texto = r.output_text or ""
        else:
            r = c.chat.completions.create(model=cfg.modelo, messages=[{"role": "user", "content": "Responda apenas: ok"}],
                                          max_tokens=16)
            texto = (r.choices[0].message.content or "") if r.choices else ""
        return {"ok": True, "ms": round((time.perf_counter() - inicio) * 1000), "resposta": texto.strip()[:40]}
    except Exception as e:  # noqa: BLE001 — qualquer falha vira mensagem curta
        return {"ok": False, "detalhe": explicar_erro(e)}


# ---------------------------------------------------------------------------
# O que a tela vê (nunca a chave)
# ---------------------------------------------------------------------------
def estado_publico(conn, clinic_id: UUID) -> dict:
    r = conn.execute(
        """select provider, model, key_last4, key_cipher is not null, usa_plataforma, updated_at
           from clinic_ai where clinic_id = %s""", (clinic_id,)).fetchone()
    provedor, modelo, final, tem_chave, usa_plataforma, atualizado = r or (None, None, None, False, False, None)
    atual = config_da_clinica(conn, clinic_id)
    plataforma = da_plataforma()
    return {
        "provedor": provedor, "modelo": modelo, "tem_chave": tem_chave, "chave_final": final,
        "usa_plataforma": usa_plataforma, "atualizado_em": atualizado,
        "origem": atual.origem if atual else None,  # "clinica" | "plataforma" | None (desligada)
        # chave salva que não abre mais (a chave-mestra do servidor mudou): precisa cadastrar de novo
        "chave_ilegivel": bool(tem_chave and (atual is None or atual.origem != "clinica")),
        "modelo_aprovado": bool(provedor and modelo in MODELOS_APROVADOS.get(provedor, [])),
        "plataforma": {"configurada": plataforma is not None, "modelo": plataforma.modelo if plataforma else None},
        "provedores": [{"id": k, "nome": v["nome"], "onde": v["onde"], "modelos_aprovados": MODELOS_APROVADOS.get(k, [])}
                       for k, v in PROVEDORES.items()],
    }


def salvar_chave(conn, clinic_id: UUID, provedor: str, modelo: str, chave: str | None, autor: UUID) -> None:
    """Grava provedor/modelo e, se veio, a chave nova (criptografada). Erros de regra sobem como ValueError."""
    if provedor not in PROVEDORES:
        raise ValueError("Provedor desconhecido.")
    modelo = modelo.strip()
    if not modelo or len(modelo) > 120 or any(ch.isspace() for ch in modelo):
        raise ValueError("Escreva o nome do modelo, sem espaços.")
    atual = conn.execute("select provider, key_cipher is not null from clinic_ai where clinic_id = %s", (clinic_id,)).fetchone()
    if chave is not None:
        chave = chave.strip()
        if len(chave) < 8 or any(ch.isspace() for ch in chave):
            raise ValueError("Essa chave parece incompleta. Copie a chave inteira, sem espaços.")
        cifra, final = cifrar(chave), final_da_chave(chave)
        conn.execute(
            """insert into clinic_ai (clinic_id, provider, model, key_cipher, key_last4, updated_at, updated_by)
               values (%s, %s, %s, %s, %s, now(), %s)
               on conflict (clinic_id) do update set provider = excluded.provider, model = excluded.model,
                 key_cipher = excluded.key_cipher, key_last4 = excluded.key_last4,
                 updated_at = now(), updated_by = excluded.updated_by""",
            (clinic_id, provedor, modelo, cifra, final, autor))
        return
    if not atual or not atual[1]:
        raise ValueError("Cole a chave de IA da clínica.")
    if atual[0] != provedor:
        raise ValueError("Trocou de provedor: cole a chave do novo provedor.")
    conn.execute("update clinic_ai set model = %s, updated_at = now(), updated_by = %s where clinic_id = %s",
                 (modelo, autor, clinic_id))


def remover_chave(conn, clinic_id: UUID, autor: UUID) -> None:
    conn.execute("""update clinic_ai set key_cipher = null, key_last4 = null, provider = null, model = null,
                    updated_at = now(), updated_by = %s where clinic_id = %s""", (autor, clinic_id))


def usar_plataforma(conn, clinic_id: UUID, ligar: bool, autor: UUID) -> None:
    conn.execute(
        """insert into clinic_ai (clinic_id, usa_plataforma, updated_at, updated_by) values (%s, %s, now(), %s)
           on conflict (clinic_id) do update set usa_plataforma = excluded.usa_plataforma,
             updated_at = now(), updated_by = excluded.updated_by""", (clinic_id, ligar, autor))


def para_teste(conn, clinic_id: UUID, provedor: str | None, modelo: str | None, chave: str | None) -> ConfigIA | None:
    """Monta a IA a testar: os valores digitados (antes de salvar) ou, sem eles, a IA atual da clínica."""
    if not provedor:
        return config_da_clinica(conn, clinic_id)
    if provedor not in PROVEDORES or not (modelo or "").strip():
        raise ValueError("Escolha o provedor e o modelo.")
    if chave is None:
        salva = config_da_clinica(conn, clinic_id)
        if not salva or salva.origem != "clinica" or salva.provedor != provedor:
            raise ValueError("Cole a chave para testar.")
        chave = salva.api_key
    p = PROVEDORES[provedor]
    return ConfigIA("clinica", provedor, modelo.strip(), p["base_url"], p["estilo"], chave.strip())
