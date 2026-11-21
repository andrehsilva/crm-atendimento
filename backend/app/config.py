"""Configurações lidas do arquivo .env (nunca coloque segredos no código)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "dev"  # "dev" (sua máquina) ou "prod" (servidor) — ver docs/GUIA-PRODUCAO.md
    app_name: str = "Ísis"
    frontend_origin: str = "http://localhost:5173"
    timezone_default: str = "America/Sao_Paulo"

    # Etapa 1B — preenchidos no .env
    database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    llm_provider: str = "opencode-go"
    llm_base_url: str = "https://opencode.ai/inference/go/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-6-luna"
    llm_api_style: str = "responses"
    # Etapa 10A: criptografa as chaves de IA das clínicas (Fernet). Perdeu = as chaves salvas precisam ser recadastradas.
    ia_chave_mestra: str = ""

    # Etapa 5 — WhatsApp pelo WAHA (servidor do usuário, D28). Segredos só aqui no .env.
    waha_api_url: str = ""            # ex.: https://waha.seudominio.com.br
    waha_api_key: str = ""            # chave X-Api-Key do servidor WAHA
    waha_webhook_hmac_key: str = ""   # segredo que assina os webhooks (HMAC SHA-512)
    public_base_url: str = ""         # endereço público do backend (túnel em dev), ex.: https://xxx.trycloudflare.com
    waha_simular_digitacao: bool = True
    # Etapa 13 (D66): mensagens picadas — espera este silêncio (s) antes de responder, no máximo o total abaixo
    whatsapp_espera_s: float = 8.0
    whatsapp_espera_max_s: float = 30.0
    # Etapa 13B (D67): transcrição de áudio (API compatível com OpenAI). Sem chave = áudio pede para escrever.
    transcricao_api_key: str = ""
    transcricao_base_url: str = "https://api.openai.com/v1"
    transcricao_modelo: str = "whisper-1"
    transcricao_usd_minuto: float = 0.006  # confira o preço atual no provedor
    transcricao_max_s: int = 120  # "visto" + "digitando…" antes de responder (evita bloqueio)

    # Etapa 6 — mensagens automáticas (lembretes, avisos, aniversário)
    mensagens_automaticas: bool = True  # liga o envio automático da fila
    envio_somente_para: str = ""  # ENV=dev: só envia para estes telefones (separados por vírgula); vazio = não envia

    # Etapa 11 — site de apresentação: endereço público onde fica <base>/<clinica>.
    # Em dev, o painel (Vite) repassa /site para o backend. Em produção: https://<dominio> (Q50).
    site_base_url: str = "http://localhost:5173/site"

    # Etapa 8B — produção
    chat_teste: bool | None = None  # chat web de TESTE (D15) aberto? Padrão: só em dev (em produção expõe conversas)

    @property
    def producao(self) -> bool:
        return self.env != "dev"

    @property
    def chat_teste_liberado(self) -> bool:
        return (not self.producao) if self.chat_teste is None else self.chat_teste


@lru_cache
def get_settings() -> Settings:
    return Settings()
