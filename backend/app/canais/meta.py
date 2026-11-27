"""WhatsApp oficial — Cloud API da Meta (Etapa 36A, D131).

Mesmos métodos de envio do ClienteWaha, para a fila, a Ísis e a equipe não precisarem saber qual provedor a clínica
usa. O `sessao` recebido é ignorado: cada cliente já nasce preso ao número (Phone Number ID) da clínica.

Ainda não cobre (etapas seguintes): receber mensagens pelo webhook (36B) e modelos fora da janela de 24 h (36C).
"""

import logging
import re

import httpx

from app.canais.waha import WahaErro
from app.config import get_settings
from app.services.llm import USER_AGENT

log = logging.getLogger("isis.meta")


class MetaErro(WahaErro):
    """Erro da API da Meta. Herda de WahaErro para os tratamentos de falha que já existem (fila, tentativas,
    "não enviou") valerem igual para os dois provedores."""


def numero_do_chat(chat_id: str) -> str:
    """'5511999998888@c.us' ou '+55 11 99999-8888' → '5511999998888' (formato que a Meta espera)."""
    return re.sub(r"\D", "", chat_id.split("@")[0])


class ClienteMeta:
    provedor = "meta"

    def __init__(self, phone_number_id: str, token: str, base_url: str | None = None,
                 transport: httpx.BaseTransport | None = None):
        if not (phone_number_id and token):
            raise MetaErro("WhatsApp oficial sem ID do número ou sem token: confira a configuração da Meta.")
        self.phone_number_id = phone_number_id
        self.http = httpx.Client(
            base_url=(base_url or get_settings().meta_graph_url).rstrip("/"),
            headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
            timeout=20, transport=transport,
        )

    def _req(self, metodo: str, caminho: str, **kw) -> httpx.Response:
        try:
            r = self.http.request(metodo, caminho, **kw)
        except httpx.HTTPError as e:
            raise MetaErro(f"Meta fora do ar ou inacessível: {type(e).__name__}") from e
        if r.status_code >= 400:
            try:
                msg = (r.json().get("error") or {}).get("message") or r.text
            except ValueError:
                msg = r.text
            raise MetaErro(f"Meta respondeu {r.status_code}: {str(msg)[:200]}")
        return r

    # ---- envio -------------------------------------------------------------
    def enviar_texto(self, sessao: str | None, chat_id: str, texto: str, simular_digitacao: bool | None = None) -> str | None:
        """Mensagem de texto livre (só vale dentro da janela de 24 h; fora dela, modelo — Etapa 36C).
        Devolve o id da mensagem (wamid), usado depois para entregue/lida."""
        r = self._req("POST", f"/{self.phone_number_id}/messages", json={
            "messaging_product": "whatsapp", "recipient_type": "individual",
            "to": numero_do_chat(chat_id), "type": "text", "text": {"preview_url": False, "body": texto},
        })
        try:
            msgs = r.json().get("messages") or []
        except ValueError:
            return None
        return msgs[0].get("id") if msgs else None

    def marcar_lido(self, message_id: str) -> None:
        """"Visto" na mensagem recebida (na Meta é por mensagem, não por conversa)."""
        try:
            self._req("POST", f"/{self.phone_number_id}/messages",
                      json={"messaging_product": "whatsapp", "status": "read", "message_id": message_id})
        except MetaErro as e:  # cortesia: não impede nada
            log.info("sem visto: %s", e)

    def digitando(self, sessao: str | None, chat_id: str) -> None:
        """Na Meta o "digitando…" precisa do id da mensagem recebida; fica para o webhook (36B). Aqui não faz nada."""

    def baixar_midia(self, media_id: str, limite: int = 5_000_000) -> bytes:
        """Mídia recebida (áudio, imagem): a Meta dá um id; pede o endereço temporário e baixa com o mesmo token.
        Só aceita endereço da própria Meta."""
        if not re.fullmatch(r"[0-9]{5,30}", media_id or ""):
            raise MetaErro("id de mídia inválido")
        url = self._req("GET", f"/{media_id}").json().get("url") or ""
        host = httpx.URL(url).host if url else ""
        if not (host == "lookaside.fbsbx.com" or host.endswith(".facebook.com") or host.endswith(".fbcdn.net")):
            raise MetaErro("endereço de mídia fora da Meta")
        r = self._req("GET", url)
        if len(r.content) > limite:
            raise MetaErro("arquivo grande demais")
        return r.content

    # ---- conferência -------------------------------------------------------
    def testar(self) -> dict:
        """Confere ID do número + token: devolve o número e o nome que a Meta tem cadastrados."""
        d = self._req("GET", f"/{self.phone_number_id}",
                      params={"fields": "display_phone_number,verified_name,quality_rating"}).json()
        return {"numero": d.get("display_phone_number"), "nome": d.get("verified_name"),
                "qualidade": d.get("quality_rating")}

    # ---- só existe no WAHA -------------------------------------------------
    def _so_waha(self, *_a, **_k):
        raise MetaErro("Essa ação é do WAHA (sessão/QR code). No WhatsApp oficial a conexão é feita na Meta.")

    sessao = qr_png = reiniciar = desconectar = listar_sessoes = criar_sessao = _so_waha
    configurar_webhook = remover_webhook = numero_do_lid = _so_waha

    def atualizar_eventos_do_webhook(self, *_a, **_k) -> bool:
        return False  # o webhook da Meta é configurado no painel da Meta
