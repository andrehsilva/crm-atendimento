"""Etapa 20 — "entregue/lida" vindo do WhatsApp (D85, D86)."""

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.agenda import servico as S
from app.api import webhooks
from app.canais import waha
from app.canais.whatsapp import registrar_entrega
from app.config import Settings, get_settings
from app.main import app
from app.painel import chat

TEL = "+5511977771234"
ID = "true_5511977771234@c.us_3EB0AAA"


def _ack(ack=None, nome=None, from_me=True, evento="message.ack", sessao="clinica_a", i=ID):
    p = {"id": i, "fromMe": from_me}
    if ack is not None:
        p["ack"] = ack
    if nome:
        p["ackName"] = nome
    return {"event": evento, "session": sessao, "payload": p}


def test_interpretar_aviso():
    assert waha.interpretar_ack(_ack(2)) == (ID, 2)
    assert waha.interpretar_ack(_ack(nome="READ")) == (ID, 3)
    assert waha.interpretar_ack(_ack(3, i={"_serialized": ID})) == (ID, 3)
    assert waha.interpretar_ack(_ack(3, from_me=False)) is None  # aviso de mensagem que o paciente mandou
    assert waha.interpretar_ack(_ack(3, evento="message")) is None
    assert "message.ack" in waha.ClienteWaha._webhook("https://x/webhooks/waha", "k")["events"]


def _conversa_com_resposta(conn, clinica, external_id=ID):
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, 'clinica_a')", (clinica.id,))
    p = S.obter_ou_criar_paciente(conn, clinica.id, TEL, "Carla Dias", "whatsapp")
    cv = chat._conversa(conn, clinica.id, p["id"], "whatsapp")
    chat._gravar(conn, clinica.id, cv["id"], "in", "paciente", "Oi")
    m = chat._gravar(conn, clinica.id, cv["id"], "out", "isis", "Olá! Como posso ajudar?", external_id)
    return cv, m


def _entrega(conn, mid):
    return conn.execute("select entrega from messages where id = %s", (mid,)).fetchone()[0]


def test_so_avanca_nunca_volta(conn, clinica):
    cv, m = _conversa_com_resposta(conn, clinica)
    assert [x["entrega"] for x in chat.historico(conn, cv["id"])] == [None, "enviada"]  # recebida não tem tracinho
    assert registrar_entrega(conn, "clinica_a", ID, 1) is False  # "chegou ao servidor" = já é enviada
    assert registrar_entrega(conn, "clinica_a", ID, 2) and _entrega(conn, m["id"]) == "entregue"
    assert registrar_entrega(conn, "clinica_a", ID, 3) and _entrega(conn, m["id"]) == "lida"
    assert registrar_entrega(conn, "clinica_a", ID, 2) is False and _entrega(conn, m["id"]) == "lida"  # atrasado
    assert chat.historico(conn, cv["id"])[-1]["entrega"] == "lida"


def test_sessao_de_outra_clinica_nao_mexe(conn, clinica, outra_clinica):
    _, m = _conversa_com_resposta(conn, clinica)
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, 'clinica_b')", (outra_clinica.id,))
    assert registrar_entrega(conn, "clinica_b", ID, 3) is False
    assert registrar_entrega(conn, "sessao_desconhecida", ID, 3) is False
    assert _entrega(conn, m["id"]) is None


def test_mensagem_automatica_vira_entregue_e_lida(conn, clinica):
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, 'clinica_a')", (clinica.id,))
    from tests.conftest import AGORA, as_
    c = S.marcar(conn, clinica.id, telefone=TEL, nome="Carla Dias", professional_id=clinica.prof_a,
                 service_id=clinica.servico, inicio=as_(24, 9), ator="recepcao", agora=AGORA)
    conn.execute("update outbound_messages set status = 'enviada', external_id = %s where appointment_id = %s and kind = 'confirmacao'",
                 (ID, c["id"]))
    status = lambda: conn.execute("select status from outbound_messages where appointment_id = %s and kind = 'confirmacao'",  # noqa: E731
                                  (c["id"],)).fetchone()[0]
    registrar_entrega(conn, "clinica_a", ID, 2)
    assert status() == "entregue"
    registrar_entrega(conn, "clinica_a", ID, 4)  # áudio ouvido também conta como lida
    assert status() == "lida"


def test_mensagem_que_falhou_nao_vira_entregue(conn, clinica):
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, 'clinica_a')", (clinica.id,))
    p = S.obter_ou_criar_paciente(conn, clinica.id, TEL, "Carla Dias", "whatsapp")
    oid = conn.execute("""insert into outbound_messages (clinic_id, patient_id, kind, body, status, external_id)
                          values (%s, %s, 'aniversario', 'Parabéns!', 'falhou', %s) returning id""", (clinica.id, p["id"], ID)).fetchone()[0]
    assert registrar_entrega(conn, "clinica_a", ID, 3) is False
    assert conn.execute("select status from outbound_messages where id = %s", (oid,)).fetchone()[0] == "falhou"


def test_webhook_passa_o_aviso_para_tras(monkeypatch):
    monkeypatch.setattr(get_settings(), "waha_webhook_hmac_key", "segredo-teste")
    recebidos = []
    monkeypatch.setattr(webhooks.whatsapp, "processar_entrega", lambda *a: recebidos.append(a))
    corpo = json.dumps(_ack(3)).encode()
    assinatura = hmac.new(b"segredo-teste", corpo, hashlib.sha512).hexdigest()
    r = TestClient(app).post("/webhooks/waha", content=corpo, headers={"X-Webhook-Hmac": assinatura})
    assert r.json() == {"ok": True} and recebidos == [("clinica_a", ID, 3)]


class _WahaGravador(waha.ClienteWaha):
    """Cliente de verdade, mas sem rede: devolve a sessão dada e guarda o que seria enviado."""

    def __init__(self, ganchos):
        super().__init__(Settings(_env_file=None, waha_api_url="http://waha", waha_api_key="x"))
        self.ganchos, self.enviado = ganchos, None

    def sessao(self, sessao):
        return {"name": sessao, "config": {"webhooks": self.ganchos, "ignore": {"groups": True}}}

    def _req(self, metodo, caminho, **kw):
        self.enviado = (metodo, caminho, kw.get("json"))


def test_atualiza_so_o_webhook_deste_sistema():
    nosso = "https://isis.exemplo.com/webhooks/waha"
    outro = {"url": "https://n8n.exemplo.com/hook", "events": ["message"]}
    w = _WahaGravador([{"url": nosso, "events": ["message", "session.status"]}, outro])
    assert w.atualizar_eventos_do_webhook("clinica_a", nosso, "segredo") is True
    _, caminho, corpo = w.enviado
    ganchos = corpo["config"]["webhooks"]
    assert caminho == "/api/sessions/clinica_a" and corpo["config"]["ignore"] == {"groups": True}
    assert "message.ack" in ganchos[0]["events"] and ganchos[0]["hmac"] == {"key": "segredo"}
    assert ganchos[1] == outro  # o webhook de outro sistema fica intacto

    w = _WahaGravador([outro])  # sessão que não manda para nós: não toca
    assert w.atualizar_eventos_do_webhook("clinica_a", nosso, "segredo") is False and w.enviado is None
    w = _WahaGravador([waha.ClienteWaha._webhook(nosso, "segredo")])  # já atualizado: não mexe de novo
    assert w.atualizar_eventos_do_webhook("clinica_a", nosso, "segredo") is False and w.enviado is None
