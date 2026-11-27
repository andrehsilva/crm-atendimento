"""WhatsApp de cada clínica (Etapa 16 — D76; Etapa 31 — D122–D124): qual servidor WAHA e qual webhook ela usa.

- Servidor próprio (endereço + chave criptografada) ou, sem ele, o servidor da plataforma (.env).
  Pode ser configurado ANTES de ligar a sessão (a linha da clínica existe com session = null).
- Webhook exclusivo: /webhooks/waha/<token>, com segredo próprio (criptografado). Criado sozinho ao ligar (D123).
- Desligar mantém servidor e webhook (D124): session = null, enabled = false.
- Chave e segredo nunca saem daqui em texto: a tela só vê os 4 últimos caracteres da chave.
"""

import secrets
from uuid import UUID

from app import ia
from app.canais.meta import ClienteMeta, MetaErro
from app.canais.waha import ClienteWaha
from app.config import get_settings


def _linha(conn, clinic_id: UUID):
    return conn.execute(
        """select session, waha_url, waha_key_cipher, waha_key_last4, webhook_token, webhook_secret_cipher, numero
           from whatsapp_instances where clinic_id = %s""", (clinic_id,)).fetchone()


def garantir_linha(conn, clinic_id: UUID) -> None:
    """A linha da clínica existe mesmo sem sessão ligada (para guardar servidor e webhook)."""
    conn.execute("""insert into whatsapp_instances (clinic_id, session, enabled, status) values (%s, null, false, 'DESLIGADO')
                    on conflict (clinic_id) do nothing""", (clinic_id,))


def garantir_webhook(conn, clinic_id: UUID) -> tuple[str, str]:
    """D123: toda clínica ligada usa o webhook exclusivo dela. Cria se ainda não tem; devolve (endereço, segredo)."""
    garantir_linha(conn, clinic_id)
    r = _linha(conn, clinic_id)
    if not (r[4] and r[5] and ia.decifrar(r[5])):
        gerar_webhook(conn, clinic_id)
    return webhook_da_clinica(conn, clinic_id)


def webhook_alinhado(info: dict, url: str) -> bool:
    """A sessão (resposta do WAHA) manda os eventos que usamos para o endereço desta clínica?"""
    from app.canais.waha import EVENTOS_WEBHOOK

    for g in ((info.get("config") or {}).get("webhooks") or []):
        if g.get("url") == url and all(e in (g.get("events") or []) for e in EVENTOS_WEBHOOK):
            return True
    return False


def provedor(conn, clinic_id: UUID) -> str:
    """D131: 'waha' (padrão, todas as clínicas de hoje) ou 'meta' (WhatsApp oficial)."""
    r = conn.execute("select provider from whatsapp_instances where clinic_id = %s", (clinic_id,)).fetchone()
    return r[0] if r else "waha"


def cliente_da_clinica(conn, clinic_id: UUID) -> "ClienteWaha | ClienteMeta":
    if provedor(conn, clinic_id) == "meta":  # D131: só quem o super admin passou para a Meta entra aqui
        return cliente_meta(conn, clinic_id)
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
    garantir_linha(conn, clinic_id)
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
        return {"numero_cadastrado": None, "servidor_proprio": False, "servidor_url": None, "chave_final": None}
    url, segredo = webhook_da_clinica(conn, clinic_id)
    return {"numero_cadastrado": r[6], "servidor_proprio": bool(r[1]), "servidor_url": r[1], "chave_final": r[3],
            "webhook_url": url, "webhook_exclusivo": bool(r[4] and r[5]), "webhook_pronto": bool(segredo)}


def isis_pausada_no_whatsapp(clinica: dict) -> bool:
    """D79: o admin da clínica pausou a Ísis no WhatsApp (Configurações › Canais)."""
    return bool((clinica.get("settings") or {}).get("isis_pausada_whatsapp"))


def atualizar_webhooks() -> int:
    """D86: ao subir, acrescenta os eventos novos (entregue/lida) no webhook das clínicas já ligadas.
    Roda em segundo plano; falha numa clínica não impede as outras. Devolve quantas mudaram."""
    import logging

    from app.db import pool

    log = logging.getLogger("isis.whatsapp")
    if not get_settings().public_base_url:
        return 0
    mudaram = 0
    with pool().connection() as conn:
        for cid, sessao in conn.execute("select clinic_id, session from whatsapp_instances where enabled and session is not null").fetchall():
            try:
                url, segredo = webhook_da_clinica(conn, cid)
                if segredo and cliente_da_clinica(conn, cid).atualizar_eventos_do_webhook(sessao, url, segredo):
                    mudaram += 1
                    log.info("webhook da sessão %s atualizado (entregue/lida)", sessao)
            except Exception as e:  # noqa: BLE001 — servidor fora do ar etc.: tenta na próxima subida
                log.warning("não deu para atualizar o webhook da sessão %s: %s", sessao, e)
    return mudaram


# ---------------------------------------------------------------------------
# WhatsApp oficial (Etapa 36A — D131). Dados em docs/conexao_meta.md. Token e chave secreta nunca voltam para a tela.
# ---------------------------------------------------------------------------
def _meta(conn, clinic_id: UUID):
    return conn.execute(
        """select meta_phone_number_id, meta_waba_id, meta_token_cipher, meta_token_last4, meta_app_secret_cipher,
                  meta_verify_token from whatsapp_instances where clinic_id = %s""", (clinic_id,)).fetchone()


def cliente_meta(conn, clinic_id: UUID) -> ClienteMeta:
    r = _meta(conn, clinic_id)
    token = ia.decifrar(r[2]) if r and r[2] else None
    if not (r and r[0] and token):
        raise MetaErro("WhatsApp oficial ainda não configurado: falta o ID do número ou o token da Meta.")
    return ClienteMeta(r[0], token)


def trocar_provedor(conn, clinic_id: UUID, novo: str) -> None:
    """Só o super admin (Admin geral). Os dados do outro provedor ficam guardados para voltar depois."""
    if novo not in ("waha", "meta"):
        raise ValueError("Provedor inválido.")
    garantir_linha(conn, clinic_id)
    conn.execute("update whatsapp_instances set provider = %s, updated_at = now() where clinic_id = %s", (novo, clinic_id))


def salvar_meta(conn, clinic_id: UUID, *, phone_number_id: str, waba_id: str, token: str | None,
                app_secret: str | None) -> None:
    """Token ou chave secreta vazios = mantém os já salvos. O token de verificação do webhook é gerado aqui."""
    garantir_linha(conn, clinic_id)
    atual = _meta(conn, clinic_id)
    if not token and not (atual and atual[2]):
        raise ValueError("Cole o token de acesso permanente da Meta.")
    if not app_secret and not (atual and atual[4]):
        raise ValueError("Cole a chave secreta do app da Meta.")
    sets = ["meta_phone_number_id = %s", "meta_waba_id = %s"]
    vals: list = [phone_number_id.strip(), waba_id.strip()]
    if token:
        sets += ["meta_token_cipher = %s", "meta_token_last4 = %s"]
        vals += [ia.cifrar(token.strip()), token.strip()[-4:]]
    if app_secret:
        sets.append("meta_app_secret_cipher = %s")
        vals.append(ia.cifrar(app_secret.strip()))
    if not (atual and atual[5]):
        sets.append("meta_verify_token = %s")
        vals.append(secrets.token_urlsafe(24))
    conn.execute(f"update whatsapp_instances set {', '.join(sets)}, updated_at = now() where clinic_id = %s",
                 (*vals, clinic_id))
    linha = _linha(conn, clinic_id)
    if not (linha and linha[4]):  # endereço exclusivo (opaco) do webhook, o mesmo usado pelo WAHA (D123)
        gerar_webhook(conn, clinic_id)


def estado_meta(conn, clinic_id: UUID) -> dict:
    """O que a tela pode ver (sem segredos)."""
    r = _meta(conn, clinic_id)
    base = get_settings().public_base_url.rstrip("/")
    return {"provedor": provedor(conn, clinic_id),
            "phone_number_id": r[0] if r else None, "waba_id": r[1] if r else None,
            "token_final": r[3] if r else None, "tem_app_secret": bool(r and r[4]),
            "webhook_url": f"{base}/webhooks/meta/{w[4]}" if base and (w := _linha(conn, clinic_id)) and w[4] else None,
            "verify_token": r[5] if r else None}
