"""WhatsApp oficial — Cloud API da Meta (Etapa 36A, D131).

Mesmos métodos de envio do ClienteWaha, para a fila, a Ísis e a equipe não precisarem saber qual provedor a clínica
usa. O `sessao` recebido é ignorado: cada cliente já nasce preso ao número (Phone Number ID) da clínica.

36B: webhook da Meta — assinatura, mensagens recebidas e status (entregue/lida/falhou).
Ainda não cobre: modelos fora da janela de 24 h (36C).
"""

import hashlib
import hmac
import logging
import re

import httpx

from app.canais.waha import MensagemEntrada, WahaErro
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

    def enviar_modelo(self, chat_id: str, nome: str, parametros: list[str], idioma: str = "pt_BR") -> str | None:
        """Modelo aprovado (36C): o único jeito de escrever fora da janela de 24 h. Devolve o wamid."""
        comp = [{"type": "body", "parameters": [{"type": "text", "text": p} for p in parametros]}] if parametros else []
        r = self._req("POST", f"/{self.phone_number_id}/messages", json={
            "messaging_product": "whatsapp", "recipient_type": "individual", "to": numero_do_chat(chat_id),
            "type": "template", "template": {"name": nome, "language": {"code": idioma}, "components": comp},
        })
        try:
            msgs = r.json().get("messages") or []
        except ValueError:
            return None
        return msgs[0].get("id") if msgs else None

    def listar_modelos(self, waba_id: str) -> list[dict]:
        d = self._req("GET", f"/{waba_id}/message_templates",
                      params={"fields": "name,language,status,category,rejected_reason", "limit": 200}).json()
        return d.get("data") or []

    def criar_modelo(self, waba_id: str, pedido: dict) -> dict:
        return self._req("POST", f"/{waba_id}/message_templates", json=pedido).json()

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


# ---------------------------------------------------------------------------
# Webhook (Etapa 36B)
# ---------------------------------------------------------------------------
def sessao_meta(phone_number_id: str) -> str:
    """Nome interno da "sessão" de uma clínica na Meta (a coluna session é única e o resto do sistema usa ela)."""
    return f"meta:{phone_number_id}"


def verificar_assinatura(corpo: bytes, assinatura: str | None, app_secret: str) -> bool:
    """X-Hub-Signature-256 = "sha256=" + HMAC-SHA256(chave secreta do app, corpo cru)."""
    if not (assinatura and app_secret and assinatura.startswith("sha256=")):
        return False
    esperado = hmac.new(app_secret.encode(), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, assinatura[7:].strip().lower())


_MIDIA = {"audio": "audio", "image": "foto", "video": "video", "sticker": "figurinha", "document": "documento"}
ENTREGA = {"delivered": 2, "read": 3}  # mesmos níveis do WAHA (D85); "sent" já é "enviada"


def _texto(m: dict) -> str:
    t = m.get("type")
    if t == "text":
        return (m.get("text") or {}).get("body") or ""
    if t == "button":  # botão de resposta rápida de um modelo (36C: lembrete)
        return (m.get("button") or {}).get("text") or (m.get("button") or {}).get("payload") or ""
    if t == "interactive":
        i = m.get("interactive") or {}
        r = i.get("button_reply") or i.get("list_reply") or {}
        return r.get("title") or r.get("id") or ""
    if t in _MIDIA:
        return (m.get(t) or {}).get("caption") or ""
    return ""


def interpretar_webhook(evento: dict, sessao: str, phone_number_id: str) -> tuple[list, list, list]:
    """(mensagens recebidas, entregas [(id, nível)], falhas [(id, motivo)]) — só do número desta clínica."""
    mensagens: list[MensagemEntrada] = []
    entregas: list[tuple[str, int]] = []
    falhas: list[tuple[str, str]] = []
    if evento.get("object") != "whatsapp_business_account":
        return mensagens, entregas, falhas
    for entrada in evento.get("entry") or []:
        for mudanca in entrada.get("changes") or []:
            v = mudanca.get("value") or {}
            if mudanca.get("field") != "messages" or (v.get("metadata") or {}).get("phone_number_id") != phone_number_id:
                continue  # nunca aceita evento de outro número neste endereço
            nomes = {c.get("wa_id"): ((c.get("profile") or {}).get("name")) for c in v.get("contacts") or []}
            for m in v.get("messages") or []:
                de = re.sub(r"\D", "", str(m.get("from") or ""))
                t = m.get("type")
                midia = _MIDIA.get(t) or (None if t in ("text", "button", "interactive") else "outro")
                texto = _texto(m).strip()
                if not de or not m.get("id") or (not texto and not midia):
                    continue
                dados = m.get(t) if t in _MIDIA and isinstance(m.get(t), dict) else {}
                mensagens.append(MensagemEntrada(
                    sessao=sessao, chat_id=de, telefone=f"+{de}", texto=texto[:2000], id_externo=str(m["id"]),
                    nome=nomes.get(m.get("from")), midia=midia,
                    midia_url=dados.get("id"), midia_mime=dados.get("mime_type"), duracao_s=None,
                ))
            for st in v.get("statuses") or []:
                i, nome = st.get("id"), st.get("status")
                if not i:
                    continue
                if nome in ENTREGA:
                    entregas.append((str(i), ENTREGA[nome]))
                elif nome == "failed":
                    erros = st.get("errors") or [{}]
                    e0 = erros[0] if isinstance(erros[0], dict) else {}
                    motivo = f"{e0.get('code', '')} {e0.get('title') or e0.get('message') or 'falhou na Meta'}".strip()
                    falhas.append((str(i), motivo[:300]))
    return mensagens, entregas, falhas
