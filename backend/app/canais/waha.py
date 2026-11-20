"""Canal WhatsApp pelo WAHA (spec 04, D28).

- `verificar_assinatura`: confere o HMAC SHA-512 que o WAHA manda em cada webhook.
- `interpretar`: transforma o JSON do webhook numa `MensagemEntrada` (ou None, se for para ignorar).
- `ClienteWaha`: chamadas à API do WAHA (enviar texto, status, QR, configurar webhook).

Identidade vem do canal (princípio do projeto): a clínica sai da SESSÃO do WAHA e o paciente do
remetente da mensagem, nunca do texto.
"""

import hashlib
import hmac
import logging
import random
import re
import time
from dataclasses import dataclass

import httpx

from app.config import Settings, get_settings
from app.services.llm import USER_AGENT

log = logging.getLogger("isis.waha")

TEXTO_MIDIA = "(o paciente enviou um arquivo, foto ou áudio — peça com gentileza para escrever a mensagem em texto)"
_SUFIXOS_IGNORADOS = ("@g.us", "@newsletter", "@broadcast")  # grupos, canais, status e listas
_NUMERO_EM_ID = re.compile(r"^(\d{10,15})@(c\.us|s\.whatsapp\.net)$")


class WahaErro(Exception):
    pass


@dataclass
class MensagemEntrada:
    sessao: str
    chat_id: str          # para onde responder (ex.: 5511999999999@c.us ou 123@lid)
    telefone: str | None  # E.164 sem formatação (+5511...); None se o WhatsApp esconder o número (@lid)
    texto: str
    id_externo: str
    nome: str | None = None


def verificar_assinatura(corpo: bytes, assinatura: str | None, chave: str) -> bool:
    if not assinatura:
        return False
    esperado = hmac.new(chave.encode(), corpo, hashlib.sha512).hexdigest()
    return hmac.compare_digest(esperado, assinatura.strip().lower())


def _numero(chat_id: str | None) -> str | None:
    m = _NUMERO_EM_ID.match(chat_id or "")
    return f"+{m.group(1)}" if m else None


def _procurar_numero(dados, ignorar: str | None) -> str | None:
    """Procura um id com número de telefone dentro de `_data` (alguns motores mandam o número junto do @lid)."""
    if isinstance(dados, str):
        n = _numero(dados)
        return n if n and n != ignorar else None
    valores = dados.values() if isinstance(dados, dict) else dados if isinstance(dados, list) else []
    for v in valores:
        n = _procurar_numero(v, ignorar)
        if n:
            return n
    return None


def interpretar(evento: dict) -> MensagemEntrada | None:
    """Só mensagens recebidas de pessoas, em conversa individual. O resto é ignorado (None)."""
    if evento.get("event") != "message":
        return None
    p = evento.get("payload") or {}
    remetente = p.get("from") or ""
    if p.get("fromMe") or not remetente or remetente.endswith(_SUFIXOS_IGNORADOS) or remetente == "status@broadcast":
        return None
    texto = (p.get("body") or "").strip()
    if not texto:
        if not p.get("hasMedia"):
            return None
        texto = TEXTO_MIDIA
    dados = p.get("_data") if isinstance(p.get("_data"), dict) else {}
    meu = _numero(((evento.get("me") or {}).get("id")))
    telefone = _numero(remetente)
    if telefone is None and remetente.endswith("@lid"):
        telefone = _procurar_numero(dados, ignorar=meu)
    nome = dados.get("notifyName") or dados.get("pushName") or None
    return MensagemEntrada(
        sessao=evento.get("session") or "",
        chat_id=remetente,
        telefone=telefone,
        texto=texto[:2000],
        id_externo=str(p.get("id") or evento.get("id") or ""),
        nome=nome,
    )


class ClienteWaha:
    def __init__(self, s: Settings | None = None):
        s = s or get_settings()
        if not (s.waha_api_url and s.waha_api_key):
            raise WahaErro("WAHA_API_URL e WAHA_API_KEY precisam estar no backend/.env")
        self.s = s
        self.http = httpx.Client(
            base_url=s.waha_api_url.rstrip("/"),
            headers={"X-Api-Key": s.waha_api_key, "User-Agent": USER_AGENT},
            timeout=20,
        )

    def _req(self, metodo: str, caminho: str, **kw) -> httpx.Response:
        try:
            r = self.http.request(metodo, caminho, **kw)
        except httpx.HTTPError as e:
            raise WahaErro(f"WAHA fora do ar ou inacessível: {type(e).__name__}") from e
        if r.status_code >= 400:
            raise WahaErro(f"WAHA respondeu {r.status_code} em {caminho}: {r.text[:200]}")
        return r

    # ---- envio -------------------------------------------------------------
    def enviar_texto(self, sessao: str, chat_id: str, texto: str, simular_digitacao: bool | None = None) -> str | None:
        """Envia `texto`. Antes marca como lido e mostra "digitando…" por um tempo proporcional ao texto
        (recomendação do WAHA para não parecer robô e reduzir risco de bloqueio). Devolve o id da mensagem."""
        alvo = {"session": sessao, "chatId": chat_id}
        if self.s.waha_simular_digitacao if simular_digitacao is None else simular_digitacao:
            try:
                self._req("POST", "/api/sendSeen", json=alvo)
                self._req("POST", "/api/startTyping", json=alvo)
                time.sleep(min(1.0 + len(texto) / 60, 4.0) + random.uniform(0, 0.8))
                self._req("POST", "/api/stopTyping", json=alvo)
            except WahaErro as e:  # "visto"/"digitando" é cortesia: não impede o envio
                log.info("sem visto/digitando: %s", e)
        r = self._req("POST", "/api/sendText", json={**alvo, "text": texto})
        try:
            d = r.json()
        except ValueError:
            return None
        if not isinstance(d, dict):
            return None
        i = d.get("id")
        if isinstance(i, dict):
            i = i.get("_serialized") or i.get("id")
        return str(i) if i else None

    # ---- sessão ------------------------------------------------------------
    def sessao(self, sessao: str) -> dict:
        return self._req("GET", f"/api/sessions/{sessao}").json()

    def qr_png(self, sessao: str) -> bytes:
        return self._req("GET", f"/api/{sessao}/auth/qr", params={"format": "image"}, headers={"Accept": "image/png"}).content

    def numero_do_lid(self, sessao: str, lid: str) -> str | None:
        """Versões novas do WAHA convertem @lid em número. Se não existir, devolve None."""
        try:
            d = self._req("GET", f"/api/{sessao}/lids/{lid.split('@')[0]}").json()
        except (WahaErro, ValueError):
            return None
        return _numero((d or {}).get("pn")) if isinstance(d, dict) else None

    def configurar_webhook(self, sessao: str, url: str, chave_hmac: str) -> dict:
        """Aponta o webhook da sessão para o nosso backend. ATENÇÃO: substitui os webhooks atuais da sessão."""
        atual = self.sessao(sessao)
        config = dict(atual.get("config") or {})
        config["webhooks"] = [{
            "url": url,
            "events": ["message", "session.status"],
            "hmac": {"key": chave_hmac},
            "retries": {"policy": "constant", "delaySeconds": 2, "attempts": 5},
        }]
        config.setdefault("ignore", {"status": True, "groups": True, "channels": True, "broadcast": True})
        return self._req("PUT", f"/api/sessions/{sessao}", json={"name": sessao, "config": config}).json()
