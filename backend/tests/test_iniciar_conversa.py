"""Equipe inicia a conversa pelo WhatsApp com quem ainda não escreveu (a Ísis só responde)."""

from app.agenda import servico as S
from app.api import painel
from app.config import Settings
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada

TEL = "+5511977779090"


def test_inicia_em_atendimento_manual_e_respeita_modo_de_teste(cliente, conn, clinica, monkeypatch):  # noqa: F811
    p = S.obter_ou_criar_paciente(conn, clinica.id, TEL, "Carla Souza", "manual")
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    url = f"/api/clinics/{clinica.id}/patients/{p['id']}/conversation/start"
    monkeypatch.setattr(painel, "get_settings", lambda: Settings(_env_file=None, env="dev", envio_somente_para="+5511900000000"))
    r = rec.post(url, json={"texto": "Oi, Carla!"})
    assert r.status_code == 422 and "Modo de teste" in r.json()["mensagem"]  # número fora da lista: não sai
    monkeypatch.setattr(painel, "get_settings", lambda: Settings(_env_file=None, env="prod"))
    enviados = []
    monkeypatch.setattr(painel.whatsapp, "enviar_da_equipe", lambda conn, cid, c, t: enviados.append((c["external_chat_id"], t)) or "id1")
    assert rec.post(url, json={"texto": "Oi, Carla!"}).json()["author"] == "recepcao"
    assert enviados == [("5511977779090@c.us", "Oi, Carla!")]
    assert conn.execute("select status, channel from conversations where patient_id = %s", (p["id"],)).fetchone() == ("humano", "whatsapp")
