"""WhatsApp de cada clínica (Etapa 16 — D76): qual servidor WAHA e qual webhook ela usa.

- Servidor próprio (endereço + chave criptografada) ou, sem ele, o servidor da plataforma (.env).
- Webhook exclusivo: /webhooks/waha/<token>, com segredo próprio (criptografado). Sem ele, o webhook geral.
- Chave e segredo nunca saem daqui em texto: a tela só vê os 4 últimos caracteres da chave.
"""

import secrets
from uuid import UUID

from app import ia
from app.canais.waha import ClienteWaha
from app.config import get_settings


def _linha(conn, clinic_id: UUID):
    return conn.execute(
        """select session, waha_url, waha_key_cipher, waha_key_last4, webhook_token, webhook_secret_cipher, numero
           from whatsapp_instances where clinic_id = %s""", (clinic_id,)).fetchone()


def cliente_da_clinica(conn, clinic_id: UUID) -> ClienteWaha:
    r = _linha(conn, clinic_id)
    if r and r[1] and r[2]:
        chave = ia.decifrar(r[2])
        if chave:
            return ClienteWaha(get_settings().model_copy(update={"waha_api_url": r[1], "waha_api_key": chave}))
    return ClienteWaha()


def webhook_da_clinica(conn, clinic_id: UUID) -> tuple[str, str]:
    """(endereço, segredo HMAC) que o WAHA da clínica deve usar."""
    s = get_settings()
    r = _linha(conn, clinic_id)
    base = s.public_base_url.rstrip("/")
    if r and r[4] and r[5]:
        segredo = ia.decifrar(r[5])
        if segredo:
            return f"{base}/webhooks/waha/{r[4]}", segredo
    return f"{base}/webhooks/waha", s.waha_webhook_hmac_key


def gerar_webhook(conn, clinic_id: UUID) -> None:
    """Cria (ou troca) o endereço e o segredo exclusivos do webhook da clínica."""
    conn.execute("update whatsapp_instances set webhook_token = %s, webhook_secret_cipher = %s where clinic_id = %s",
                 (secrets.token_urlsafe(18), ia.cifrar(secrets.token_urlsafe(48)), clinic_id))


def salvar_servidor(conn, clinic_id: UUID, *, numero: str | None, url: str | None, chave: str | None) -> None:
    """url vazio = servidor da plataforma. chave vazia = mantém a salva."""
    if url and not url.startswith("https://") and get_settings().producao:
        raise ValueError("O endereço do servidor precisa começar com https://")
    if url and not chave and not (_linha(conn, clinic_id) or [None, None, None])[2]:
        raise ValueError("Cole a chave da API do servidor WAHA.")
    if not url:
        conn.execute("""update whatsapp_instances set numero = %s, waha_url = null, waha_key_cipher = null, waha_key_last4 = null
                        where clinic_id = %s""", (numero, clinic_id))
        return
    if chave:
        conn.execute("""update whatsapp_instances set numero = %s, waha_url = %s, waha_key_cipher = %s, waha_key_last4 = %s
                        where clinic_id = %s""", (numero, url.rstrip("/"), ia.cifrar(chave.strip()), chave.strip()[-4:], clinic_id))
    else:
        conn.execute("update whatsapp_instances set numero = %s, waha_url = %s where clinic_id = %s", (numero, url.rstrip("/"), clinic_id))


def por_token(conn, token: str):
    """(clinic_id, sessão, segredo) do webhook exclusivo, ou None."""
    r = conn.execute("select clinic_id, session, webhook_secret_cipher from whatsapp_instances where webhook_token = %s",
                     (token,)).fetchone()
    if not r or not r[2]:
        return None
    return r[0], r[1], ia.decifrar(r[2])


def estado(conn, clinic_id: UUID) -> dict:
    r = _linha(conn, clinic_id)
    if not r:
        return {}
    url, segredo = webhook_da_clinica(conn, clinic_id)
    return {"numero_cadastrado": r[6], "servidor_proprio": bool(r[1]), "servidor_url": r[1], "chave_final": r[3],
            "webhook_url": url, "webhook_exclusivo": bool(r[4] and r[5]), "webhook_pronto": bool(segredo)}
