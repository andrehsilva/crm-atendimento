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
