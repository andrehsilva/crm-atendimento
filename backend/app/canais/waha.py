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
from urllib.parse import urlparse
from dataclasses import dataclass

import httpx

from app.config import Settings, get_settings
from app.services.llm import USER_AGENT

log = logging.getLogger("isis.waha")

# Etapa 13 (D68): mídia sem texto não vai para a IA; o código responde e a equipe vê o que chegou na conversa
ROTULO_MIDIA = {"foto": "📷 Foto", "video": "🎬 Vídeo", "figurinha": "🙂 Figurinha", "documento": "📄 Documento",
                "audio": "🎤 Áudio", "outro": "📎 Arquivo"}


def _tipo_midia(p: dict, dados: dict) -> str:
    t = str(dados.get("type") or "").lower()
    mime = str(((p.get("media") or {}) if isinstance(p.get("media"), dict) else {}).get("mimetype") or dados.get("mimetype") or "").lower()
    if t in ("ptt", "audio") or mime.startswith("audio/"):
        return "audio"
    if t == "sticker" or mime == "image/webp" and t != "image":
        return "figurinha"
    if t == "image" or mime.startswith("image/"):
        return "foto"
    if t == "video" or mime.startswith("video/"):
        return "video"
    if t == "document" or mime:
        return "documento"
    return "outro"
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
    midia: str | None = None  # "foto", "audio"… (Etapa 13); texto = legenda, ou "" se veio sem legenda
    midia_url: str | None = None   # 13B: onde o WAHA guardou o arquivo (só baixamos do próprio WAHA)
    midia_mime: str | None = None
    duracao_s: int | None = None   # duração do áudio, quando o WhatsApp informa


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


# D85: "message.ack" = o WhatsApp avisa que a mensagem chegou ao celular (2) ou foi lida (3) / ouvida (4)
EVENTOS_WEBHOOK = ["message", "session.status", "message.ack"]
_ACK_NOME = {"SERVER": 1, "DEVICE": 2, "READ": 3, "PLAYED": 4}


def interpretar_ack(evento: dict) -> tuple[str, int] | None:
    """(id da mensagem no WhatsApp, nível do aviso) — só das mensagens que NÓS enviamos."""
    if evento.get("event") != "message.ack":
        return None
    p = evento.get("payload") or {}
    if p.get("fromMe") is False:
        return None
    i = p.get("id")
    if isinstance(i, dict):
        i = i.get("_serialized") or i.get("id")
    ack = p.get("ack")
    if not isinstance(ack, int):
        ack = _ACK_NOME.get(str(p.get("ackName") or "").upper())
    return (str(i), ack) if i and isinstance(ack, int) else None


def interpretar(evento: dict) -> MensagemEntrada | None:
    """Só mensagens recebidas de pessoas, em conversa individual. O resto é ignorado (None)."""
    if evento.get("event") != "message":
        return None
    p = evento.get("payload") or {}
    remetente = p.get("from") or ""
    if p.get("fromMe") or not remetente or remetente.endswith(_SUFIXOS_IGNORADOS) or remetente == "status@broadcast":
        return None
    texto = (p.get("body") or "").strip()
    dados = p.get("_data") if isinstance(p.get("_data"), dict) else {}
    midia = _tipo_midia(p, dados) if p.get("hasMedia") else None
    if midia and texto == (dados.get("body") or "") and len(texto) > 500:
        texto = ""  # alguns servidores mandam a mídia em base64 no "body": não é legenda
    if not texto and not midia:
        return None
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
        midia=midia,
        midia_url=(p.get("media") or {}).get("url") if isinstance(p.get("media"), dict) else None,
        midia_mime=(p.get("media") or {}).get("mimetype") if isinstance(p.get("media"), dict) else None,
        duracao_s=_inteiro(dados.get("duration") or dados.get("seconds")),
    )


def _inteiro(v) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


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

    def baixar_midia(self, url: str, limite: int = 5_000_000) -> bytes:
        """Baixa um arquivo que o próprio WAHA guardou. Recusa qualquer outro endereço (evita usar o servidor
        para buscar endereços de terceiros) e arquivos grandes demais."""
        base, alvo = urlparse(self.s.waha_api_url), urlparse(url)
        if not url or (alvo.scheme, alvo.netloc) != (base.scheme, base.netloc):
            raise WahaErro("endereço de mídia fora do servidor WAHA")
        r = self._req("GET", alvo.path + (f"?{alvo.query}" if alvo.query else ""))
        if len(r.content) > limite:
            raise WahaErro("arquivo grande demais")
        return r.content

    def digitando(self, sessao: str, chat_id: str) -> None:
        """D66: "visto" e "digitando…" enquanto a assistente espera o paciente terminar de escrever."""
        alvo = {"session": sessao, "chatId": chat_id}
        try:
            self._req("POST", "/api/sendSeen", json=alvo)
            self._req("POST", "/api/startTyping", json=alvo)
        except WahaErro as e:
            log.info("sem visto/digitando: %s", e)

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

    @staticmethod
    def _webhook(url: str, chave_hmac: str) -> dict:
        return {
            "url": url,
            "events": EVENTOS_WEBHOOK,
            "hmac": {"key": chave_hmac},
            "retries": {"policy": "constant", "delaySeconds": 2, "attempts": 5},
        }

    def configurar_webhook(self, sessao: str, url: str, chave_hmac: str) -> dict:
        """Aponta o webhook da sessão para o nosso backend. ATENÇÃO: substitui os webhooks atuais da sessão."""
        atual = self.sessao(sessao)
        config = dict(atual.get("config") or {})
        config["webhooks"] = [self._webhook(url, chave_hmac)]
        config.setdefault("ignore", {"status": True, "groups": True, "channels": True, "broadcast": True})
        return self._req("PUT", f"/api/sessions/{sessao}", json={"name": sessao, "config": config}).json()

    def atualizar_eventos_do_webhook(self, sessao: str, url: str, chave_hmac: str) -> bool:
        """D86: se a sessão já manda para `url` mas falta algum evento (ex.: message.ack), atualiza SÓ esse webhook.
        Os outros webhooks da sessão ficam como estão; sessão que manda para outro sistema não é tocada.
        Devolve True se mudou algo."""
        atual = self.sessao(sessao)
        config = dict(atual.get("config") or {})
        ganchos = list(config.get("webhooks") or [])
        mudou = False
        for i, g in enumerate(ganchos):
            if g.get("url") == url and any(e not in (g.get("events") or []) for e in EVENTOS_WEBHOOK):
                ganchos[i] = self._webhook(url, chave_hmac)
                mudou = True
        if mudou:
            config["webhooks"] = ganchos
            self._req("PUT", f"/api/sessions/{sessao}", json={"name": sessao, "config": config})
        return mudou

    def listar_sessoes(self) -> list[dict]:
        return self._req("GET", "/api/sessions", params={"all": "true"}).json()

    def criar_sessao(self, sessao: str, url: str, chave_hmac: str) -> dict:
        """Cria e inicia uma sessão nova já com o nosso webhook (depois é só ler o QR code)."""
        return self._req("POST", "/api/sessions", json={
            "name": sessao, "start": True,
            "config": {"webhooks": [self._webhook(url, chave_hmac)],
                       "ignore": {"status": True, "groups": True, "channels": True, "broadcast": True}},
        }).json()

    def reiniciar(self, sessao: str) -> None:
        self._req("POST", f"/api/sessions/{sessao}/restart")

    def desconectar(self, sessao: str) -> None:
        """Desliga o número da sessão (logout). Para conectar de novo, é preciso ler outro QR code."""
        self._req("POST", f"/api/sessions/{sessao}/logout")
