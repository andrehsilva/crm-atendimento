"""Etapa 10A — IA de cada clínica: chave criptografada, provedor/modelo, testar conexão, desligada sem chave."""

from openai import AuthenticationError
import httpx

from app import ia
from app.agenda import servico as S
from app.painel import chat
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401

CHAVE = "sk-teste-0123456789-abcd"


def _url(clinica):
    return f"/api/clinics/{clinica.id}/config/ia"


def _sem_ia(conn, clinica):
    conn.execute("update clinic_ai set usa_plataforma = false, key_cipher = null, key_last4 = null, provider = null, "
                 "model = null where clinic_id = %s", (clinica.id,))


def test_chave_fica_criptografada_e_so_o_final_aparece(cliente, conn, clinica):  # noqa: F811
    admin = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    r = admin.put(_url(clinica), json={"provedor": "openai", "modelo": "gpt-x", "chave": f"  {CHAVE}  "})
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["tem_chave"] and e["chave_final"] == "abcd" and e["origem"] == "clinica" and e["provedor"] == "openai"
    assert CHAVE not in r.text
    cifra = conn.execute("select key_cipher from clinic_ai where clinic_id = %s", (clinica.id,)).fetchone()[0]
    assert CHAVE.encode() not in bytes(cifra) and ia.decifrar(cifra) == CHAVE
    cfg = ia.config_da_clinica(conn, clinica.id)
    assert cfg.api_key == CHAVE and cfg.base_url.startswith("https://api.openai.com") and cfg.estilo == "responses"
    # GET também nunca devolve a chave
    assert CHAVE not in admin.get(_url(clinica)).text


def test_trocar_modelo_mantem_chave_e_trocar_provedor_exige_chave_nova(cliente, conn, clinica):  # noqa: F811
    admin = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    admin.put(_url(clinica), json={"provedor": "openrouter", "modelo": "a/b", "chave": CHAVE})
    r = admin.put(_url(clinica), json={"provedor": "openrouter", "modelo": "c/d"})
    assert r.status_code == 200 and r.json()["modelo"] == "c/d" and ia.config_da_clinica(conn, clinica.id).api_key == CHAVE
    assert ia.config_da_clinica(conn, clinica.id).estilo == "chat"
    assert admin.put(_url(clinica), json={"provedor": "google", "modelo": "gemini-x"}).status_code == 422
    assert admin.put(_url(clinica), json={"provedor": "openai", "modelo": "com espaço", "chave": CHAVE}).status_code == 422
    assert admin.put(_url(clinica), json={"provedor": "outro", "modelo": "x", "chave": CHAVE}).status_code == 422


def test_recepcao_ve_mas_nao_muda_nem_testa(cliente, conn, clinica):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id))
    assert rec.get(_url(clinica)).status_code == 200
    assert rec.put(_url(clinica), json={"provedor": "openai", "modelo": "x", "chave": CHAVE}).status_code == 403
    assert rec.post(f"{_url(clinica)}/testar", json={}).status_code == 403
    assert rec.delete(f"{_url(clinica)}/chave").status_code == 403


def test_ordem_chave_da_clinica_depois_plataforma_depois_desligada(cliente, conn, clinica, monkeypatch):  # noqa: F811
    monkeypatch.setattr(ia, "da_plataforma", lambda: ia.ConfigIA("plataforma", "opencode-go", "m", "https://x", "responses", "k"))
    assert ia.config_da_clinica(conn, clinica.id).origem == "plataforma"  # fixture: usa_plataforma = true
    admin = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    admin.put(_url(clinica), json={"provedor": "google", "modelo": "gemini-x", "chave": CHAVE})
    assert ia.config_da_clinica(conn, clinica.id).origem == "clinica"
    e = admin.delete(f"{_url(clinica)}/chave").json()
    assert not e["tem_chave"] and e["origem"] == "plataforma"
    _sem_ia(conn, clinica)
    assert ia.config_da_clinica(conn, clinica.id) is None
    assert cliente.get(f"/api/clinics/{clinica.id}").json()["ia_ativa"] is False


def test_sem_ia_a_conversa_vai_para_a_equipe_sem_chamar_o_modelo(conn, clinica, monkeypatch):
    from app.agent import isis

    _sem_ia(conn, clinica)
    chamou = []
    monkeypatch.setattr(isis, "responder", lambda *a, **k: chamou.append(1) or "não devia")
    monkeypatch.setattr(conn, "commit", lambda: None)  # o teste roda numa transação desfeita no fim
    c = S.carregar_clinica(conn, clinica.id)
    slug = conn.execute("select slug from clinics where id = %s", (clinica.id,)).fetchone()[0]
    novas = chat.receber(conn, slug, "+5511955554444", "Oi, quero marcar")
    assert len(novas) == 1 and not chamou
    status = conn.execute("select status from conversations where clinic_id = %s", (c["id"],)).fetchone()[0]
    assert status == "humano"


def test_devolver_para_a_isis_recusado_sem_ia(cliente, conn, clinica):  # noqa: F811
    _sem_ia(conn, clinica)
    pid = conn.execute("insert into patients (clinic_id, phone) values (%s, '+5511955555555') returning id", (clinica.id,)).fetchone()[0]
    cid = conn.execute("insert into conversations (clinic_id, patient_id, channel, status) values (%s, %s, 'web', 'humano') returning id",
                       (clinica.id, pid)).fetchone()[0]
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id))
    r = c.post(f"/api/clinics/{clinica.id}/conversations/{cid}/release")
    assert r.status_code == 409 and r.json()["codigo"] == "IA_DESLIGADA"


def test_testar_conexao_nunca_repete_a_mensagem_do_provedor(cliente, conn, clinica, monkeypatch):  # noqa: F811
    def falha(_cfg, **_):
        resp = httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        raise AuthenticationError(f"Incorrect API key provided: {CHAVE[:10]}****", response=resp, body=None)

    monkeypatch.setattr(ia, "cliente", falha)
    admin = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    r = admin.post(f"{_url(clinica)}/testar", json={"provedor": "openai", "modelo": "gpt-x", "chave": CHAVE})
    assert r.status_code == 200 and r.json()["ok"] is False
    assert "recusou a chave" in r.json()["detalhe"] and CHAVE[:10] not in r.text


def test_admin_geral_liga_a_chave_da_plataforma(cliente, conn, clinica):  # noqa: F811
    _sem_ia(conn, clinica)
    url = f"/api/admin/clinicas/{clinica.id}/ia"
    assert _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin")).put(url, json={"usa_plataforma": True}).status_code == 403
    r = _como(cliente, _usuario(conn, super_admin=True)).put(url, json={"usa_plataforma": True})
    assert r.status_code == 200 and r.json()["usa_plataforma"] is True


def test_modelo_do_agno_segue_o_estilo_do_provedor():
    from agno.models.openai import OpenAIChat, OpenAIResponses

    base = dict(origem="clinica", modelo="m", api_key="k")
    g = ia.modelo_agno(ia.ConfigIA(provedor="google", base_url="https://g", estilo="chat", **base), "s")
    o = ia.modelo_agno(ia.ConfigIA(provedor="opencode", base_url="https://o", estilo="responses", **base), "s")
    assert isinstance(g, OpenAIChat) and not isinstance(g, OpenAIResponses) and "x-opencode-session" not in g.default_headers
    assert isinstance(o, OpenAIResponses) and o.store is False and o.default_headers["x-opencode-session"] == "s"
