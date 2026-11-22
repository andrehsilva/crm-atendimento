"""Configurações › Canais (D79, D80): status do WhatsApp para a equipe; QR, reiniciar e pausa só para o admin da clínica."""

import pytest

from app.agenda import servico as S
from app.api import canais as rotas
from app.canais.waha import WahaErro
from app.painel import chat
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada
from tests.test_lembretes import SemCommit  # o caminho normal da Ísis faz commit no meio: aqui nada é gravado

SESSAO = "clinica_a"


class WahaFalso:
    def __init__(self, status="WORKING", falhar=False):
        self.status, self.falhar, self.reiniciou = status, falhar, False

    def sessao(self, nome):
        if self.falhar:
            raise WahaErro("http://servidor-interno:3000 recusou a conexão")
        return {"name": nome, "status": self.status, "me": {"id": "5511944445555@c.us"} if self.status == "WORKING" else None}

    def qr_png(self, nome):
        return b"\x89PNG-falso"

    def reiniciar(self, nome):
        self.reiniciou = True


@pytest.fixture
def waha(monkeypatch):
    w = WahaFalso()
    monkeypatch.setattr(rotas, "cliente_da_clinica", lambda conn, cid: w)
    return w


@pytest.fixture
def ligada(conn, clinica):
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, %s)", (clinica.id, SESSAO))
    return clinica


def _url(clinica, resto=""):
    return f"/api/clinics/{clinica.id}/config/canais/whatsapp{resto}"


def test_recepcao_ve_status_mas_nao_mexe(cliente, conn, ligada, waha):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=ligada.id, papel="reception"))
    r = rec.get(_url(ligada)).json()
    assert r == {"isis_pausada": False, "ligado": True, "situacao": "conectado", "numero": "+5511944445555"}
    assert rec.get(_url(ligada, "/qr")).status_code == 403
    assert rec.post(_url(ligada, "/reiniciar")).status_code == 403
    assert rec.put(_url(ligada, "/pausa"), json={"pausada": True}).status_code == 403
    assert waha.reiniciou is False


def test_admin_da_clinica_ve_qr_e_reinicia(cliente, conn, ligada, waha):  # noqa: F811
    waha.status = "SCAN_QR_CODE"
    adm = _como(cliente, _usuario(conn, clinic_id=ligada.id, papel="clinic_admin"))
    assert adm.get(_url(ligada)).json()["situacao"] == "qr"
    qr = adm.get(_url(ligada, "/qr"))
    assert qr.status_code == 200 and qr.headers["content-type"] == "image/png"
    assert adm.post(_url(ligada, "/reiniciar")).json() == {"ok": True} and waha.reiniciou


def test_sem_whatsapp_e_servidor_fora_nao_vazam_detalhe(cliente, conn, clinica, monkeypatch):  # noqa: F811
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    assert adm.get(_url(clinica)).json()["situacao"] == "sem_whatsapp"
    assert adm.get(_url(clinica, "/qr")).status_code == 422
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, %s)", (clinica.id, SESSAO))
    monkeypatch.setattr(rotas, "cliente_da_clinica", lambda conn, cid: WahaFalso(falhar=True))
    r = adm.get(_url(clinica))
    assert r.json()["situacao"] == "sem_resposta" and "servidor-interno" not in r.text


def test_outra_clinica_nao_ve(cliente, conn, ligada, outra_clinica, waha):  # noqa: F811
    estranho = _como(cliente, _usuario(conn, clinic_id=outra_clinica.id, papel="clinic_admin"))
    assert estranho.get(_url(ligada)).status_code == 403
    assert estranho.put(_url(ligada, "/pausa"), json={"pausada": True}).status_code == 403


def test_pausa_manda_whatsapp_para_a_equipe_sem_ia(cliente, conn, ligada, waha, monkeypatch):  # noqa: F811
    adm = _como(cliente, _usuario(conn, clinic_id=ligada.id, papel="clinic_admin"))
    assert adm.put(_url(ligada, "/pausa"), json={"pausada": True}).json()["isis_pausada"] is True

    monkeypatch.setattr(chat, "config_da_clinica", lambda conn, cid: object())  # a clínica TEM IA
    monkeypatch.setattr(chat.isis, "responder", lambda *a, **k: pytest.fail("a Ísis não pode responder pausada"))
    cl = S.carregar_clinica(conn, ligada.id)
    p = S.obter_ou_criar_paciente(conn, ligada.id, "+5511977771234", None, "whatsapp")
    cv = chat._conversa(conn, ligada.id, p["id"], "whatsapp")
    novas = chat.processar(SemCommit(conn), cl, p, cv, "Oi, quero marcar")
    assert [m["author"] for m in novas] == ["paciente"]  # sem aviso ao paciente (D79)
    assert conn.execute("select status from conversations where id = %s", (cv["id"],)).fetchone()[0] == "humano"

    # enquanto durar a pausa, não dá para devolver a conversa do WhatsApp para a Ísis
    r = adm.post(f"/api/clinics/{ligada.id}/conversations/{cv['id']}/release")
    assert r.status_code == 409 and "Canais" in r.json()["mensagem"], r.json()

    # retomou: volta ao normal
    assert adm.put(_url(ligada, "/pausa"), json={"pausada": False}).json()["isis_pausada"] is False
    assert conn.execute("select count(*) from admin_audit where clinic_id = %s and action like '%%isis_whatsapp'",
                        (ligada.id,)).fetchone()[0] == 2


def test_pausa_no_whatsapp_nao_afeta_o_chat_do_site(conn, ligada, monkeypatch):
    conn.execute("""update clinics set settings = settings || '{"isis_pausada_whatsapp": true}' where id = %s""", (ligada.id,))
    monkeypatch.setattr(chat, "config_da_clinica", lambda conn, cid: object())
    monkeypatch.setattr(chat.isis, "responder", lambda *a, **k: "Olá! Posso ajudar.")
    monkeypatch.setattr(chat.uso_ia, "pausada", lambda conn, cid: False)
    cl = S.carregar_clinica(conn, ligada.id)
    p = S.obter_ou_criar_paciente(conn, ligada.id, "+5511977771234", None, "web")
    cv = chat._conversa(conn, ligada.id, p["id"], "web")
    assert [m["author"] for m in chat.processar(SemCommit(conn), cl, p, cv, "Oi")] == ["paciente", "isis"]
