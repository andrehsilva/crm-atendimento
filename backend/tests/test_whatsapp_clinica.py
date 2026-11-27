"""Etapa 16 (D76) — WhatsApp próprio de cada clínica: servidor WAHA, número e webhook exclusivo."""

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.canais import conexao
from app.main import app
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401

SESSAO = "clinica_a"


def _ligar(conn, clinica):
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, %s)", (clinica.id, SESSAO))


def test_servidor_proprio_e_usado_e_a_chave_nunca_aparece(conn, clinica):
    _ligar(conn, clinica)
    conexao.salvar_servidor(conn, clinica.id, numero="+5511912345678", url="https://waha.clinica-a.com/", chave="chave-secreta-1234")
    c = conexao.cliente_da_clinica(conn, clinica.id)
    assert str(c.http.base_url).startswith("https://waha.clinica-a.com") and c.http.headers["X-Api-Key"] == "chave-secreta-1234"
    e = conexao.estado(conn, clinica.id)
    assert e["servidor_proprio"] and e["chave_final"] == "1234" and "chave-secreta" not in json.dumps(e, default=str)
    conexao.salvar_servidor(conn, clinica.id, numero=None, url=None, chave=None)  # volta para o da plataforma
    assert not conexao.estado(conn, clinica.id)["servidor_proprio"]


def test_webhook_exclusivo_confere_segredo_e_sessao(conn, clinica, monkeypatch):
    from app.api import webhooks

    _ligar(conn, clinica)
    conexao.gerar_webhook(conn, clinica.id)
    url, segredo = conexao.webhook_da_clinica(conn, clinica.id)
    token = url.rsplit("/", 1)[1]
    achado = conexao.por_token(conn, token)
    monkeypatch.setattr(conexao, "por_token", lambda c, t: achado if t == token else None)
    recebidas = []
    monkeypatch.setattr(webhooks.whatsapp, "processar", lambda msg: recebidas.append(msg))

    def post(evento, chave=segredo, t=token):
        corpo = json.dumps(evento).encode()
        assinatura = hmac.new(chave.encode(), corpo, hashlib.sha512).hexdigest()
        return TestClient(app).post(f"/webhooks/waha/{t}", content=corpo, headers={"x-webhook-hmac": assinatura})

    msg = {"event": "message", "session": SESSAO, "payload": {"id": "M1", "from": "5511988887777@c.us", "body": "Oi", "fromMe": False}}
    assert post(msg).json() == {"ok": True} and len(recebidas) == 1
    assert post(msg, chave="segredo-errado").status_code == 401
    assert post({**msg, "session": "outra_clinica"}).json()["ignorada"] is True and len(recebidas) == 1
    assert post(msg, t="token-que-nao-existe").status_code == 404


def test_so_admin_geral_configura(cliente, conn, clinica):  # noqa: F811
    _ligar(conn, clinica)
    url = f"/api/admin/clinicas/{clinica.id}/whatsapp/conexao"
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    assert adm.put(url, json={"numero": "11912345678"}).status_code == 403
    sup = _como(cliente, _usuario(conn, super_admin=True))
    r = sup.put(url, json={"numero": "(11) 91234-5678"})
    assert r.status_code == 200 and r.json()["numero_cadastrado"] == "+5511912345678"
    assert sup.put(url, json={"numero": "123"}).status_code == 422


# --- Etapa 31 (D122–D124): servidor antes de ligar, webhook exclusivo automático, desligar sem perder nada ----
from app.api import admin as rotas_admin  # noqa: E402
from app.canais.waha import EVENTOS_WEBHOOK  # noqa: E402
from app.config import get_settings  # noqa: E402


class WahaMemoria:
    """WAHA simulado que guarda os webhooks de cada sessão (e conta os reinícios)."""

    sessoes: dict = {}
    reinicios: list = []

    def __init__(self, *a, **k):
        pass

    def sessao(self, nome):
        s = self.sessoes[nome]
        return {"name": nome, "status": s["status"], "me": {"id": "5516991122235@c.us"}, "config": {"webhooks": s["webhooks"]}}

    def listar_sessoes(self):
        return [self.sessao(n) for n in self.sessoes]

    def criar_sessao(self, nome, url, chave):
        self.sessoes[nome] = {"status": "SCAN_QR_CODE", "webhooks": [{"url": url, "events": EVENTOS_WEBHOOK}]}
        return self.sessao(nome)

    def configurar_webhook(self, nome, url, chave):
        self.sessoes[nome]["webhooks"] = [{"url": url, "events": EVENTOS_WEBHOOK}]
        self.reinicios.append(nome)
        return {}

    def remover_webhook(self, nome, url):
        self.sessoes[nome]["webhooks"] = [g for g in self.sessoes[nome]["webhooks"] if g["url"] != url]
        self.reinicios.append(nome)
        return True


def _waha_memoria(monkeypatch, **sessoes):
    WahaMemoria.sessoes = {n: {"status": "WORKING", "webhooks": w} for n, w in sessoes.items()}
    WahaMemoria.reinicios = []
    monkeypatch.setattr(rotas_admin, "ClienteWaha", WahaMemoria)
    monkeypatch.setattr(conexao, "ClienteWaha", WahaMemoria)
    monkeypatch.setattr(rotas_admin, "get_settings", lambda: get_settings().model_copy(update={"public_base_url": "https://isis.exemplo.com"}))
    monkeypatch.setattr(conexao, "get_settings", lambda: get_settings().model_copy(update={"public_base_url": "https://isis.exemplo.com"}))


def test_ligar_ja_aponta_o_webhook_exclusivo_e_status_reconhece(cliente, conn, clinica, monkeypatch):  # noqa: F811
    _waha_memoria(monkeypatch, livre=[{"url": "https://n8n.antigo/webhook", "events": ["message"]}])
    sup = _como(cliente, _usuario(conn, super_admin=True))
    base = f"/api/admin/clinicas/{clinica.id}/whatsapp"
    r = sup.put(base, json={"sessao": "livre"}).json()
    assert r["ligado"] and r["reiniciando"] is True and r["webhook_ok"] is True
    assert r["conexao"]["webhook_exclusivo"] and "/webhooks/waha/" in r["conexao"]["webhook_url"]
    assert WahaMemoria.sessoes["livre"]["webhooks"][0]["url"] == r["conexao"]["webhook_url"]
    # ligar de novo a mesma sessão, já alinhada: não reinicia
    WahaMemoria.reinicios.clear()
    assert sup.put(base, json={"sessao": "livre"}).json()["reiniciando"] is False and not WahaMemoria.reinicios


def test_desligar_guarda_servidor_e_webhook_e_pode_tirar_do_waha(cliente, conn, clinica, monkeypatch):  # noqa: F811
    _waha_memoria(monkeypatch, livre=[])
    sup = _como(cliente, _usuario(conn, super_admin=True))
    base = f"/api/admin/clinicas/{clinica.id}/whatsapp"
    assert sup.put(f"{base}/conexao", json={"numero": "16991122235", "url": "https://waha.clinica.com", "chave": "k-123456"}).status_code == 200
    url = sup.put(base, json={"sessao": "livre"}).json()["conexao"]["webhook_url"]
    r = sup.delete(f"{base}?tirar_webhook=true").json()
    assert r["ligado"] is False and WahaMemoria.sessoes["livre"]["webhooks"] == []
    c = r["conexao"]
    assert c["servidor_proprio"] and c["chave_final"] == "3456" and c["webhook_url"] == url  # nada se perdeu
    # religar usa o MESMO endereço exclusivo
    assert sup.put(base, json={"sessao": "livre"}).json()["conexao"]["webhook_url"] == url
    # trocar de servidor com a sessão ligada é recusado
    assert sup.put(f"{base}/conexao", json={"url": "https://outro.waha.com", "chave": "x"}).status_code == 422


def test_servidor_antes_de_ligar_e_sessoes_do_servidor_da_clinica(cliente, conn, clinica, monkeypatch):  # noqa: F811
    _waha_memoria(monkeypatch, propria=[])
    sup = _como(cliente, _usuario(conn, super_admin=True))
    base = f"/api/admin/clinicas/{clinica.id}/whatsapp"
    assert sup.get(base).json() == {"ligado": False, "provedor": "waha", "conexao": {"numero_cadastrado": None, "servidor_proprio": False,
                                                                  "servidor_url": None, "chave_final": None}}
    r = sup.put(f"{base}/conexao", json={"url": "https://waha.clinica.com", "chave": "chave-9999"})
    assert r.status_code == 200 and r.json()["servidor_proprio"]
    assert [s["sessao"] for s in sup.get(f"{base}/sessoes").json()] == ["propria"]


def test_webhook_antigo_de_clinica_desligada_e_ignorado(conn, clinica):
    conexao.garantir_webhook(conn, clinica.id)  # clínica com webhook, mas sem sessão ligada
    url, _ = conexao.webhook_da_clinica(conn, clinica.id)
    _, sessao, _ = conexao.por_token(conn, url.rsplit("/", 1)[1])
    assert sessao is None  # o endpoint compara a sessão do evento com None → ignora (sem 404, o WAHA não insiste)
