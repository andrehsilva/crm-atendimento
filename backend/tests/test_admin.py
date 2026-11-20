"""Etapa 7B — painel de admin geral. Supabase e WAHA simulados; banco de verdade na transação do teste."""

from uuid import uuid4

import pytest

from app.admin.servico import slug_de
from app.api import admin as rotas_admin
from app.auth import supabase as sb
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada

NOVA = {"nome": "Clínica Sorriso Feliz", "telefone": "(11) 3333-4444", "nome_assistente": "Luna",
        "admin_email": "dona@sorriso.com", "admin_nome": "Dona Sorriso", "profissional": "Dr. Caio"}


@pytest.fixture
def supabase_falso(monkeypatch):
    criados = []
    monkeypatch.setattr(sb, "buscar_usuario_por_email", lambda email: None)

    def criar(email, senha, nome=None):
        criados.append((email, senha))
        return str(uuid4())

    monkeypatch.setattr(sb, "criar_usuario", criar)
    return criados


@pytest.fixture
def admin(cliente, conn):  # noqa: F811
    return _como(cliente, _usuario(conn, super_admin=True))


def test_so_super_admin_entra_no_admin_geral(cliente, conn, clinica):  # noqa: F811
    assert _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin")).get("/api/admin/clinicas").status_code == 403
    assert _como(cliente, _usuario(conn, super_admin=True)).get("/api/admin/clinicas").status_code == 200


def test_criar_clinica_pronta_para_usar(admin, conn, supabase_falso):
    r = admin.post("/api/admin/clinicas", json=NOVA)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["slug"] == "sorriso-feliz" and d["senha_provisoria"] and supabase_falso[0][0] == "dona@sorriso.com"
    cid = d["id"]
    phone, settings = conn.execute("select phone, settings from clinics where id = %s", (cid,)).fetchone()
    assert phone == "+551133334444" and settings["nome_assistente"] == "Luna"
    conta = lambda tabela: conn.execute(f"select count(*) from {tabela} where clinic_id = %s", (cid,)).fetchone()[0]  # noqa: E731,S608
    assert conta("clinic_hours") == 6 and conta("services") >= 5 and conta("professionals") == 1
    assert conta("professional_services") == conta("services")
    papel, trocar = conn.execute(
        """select cu.role, u.must_change_password from clinic_users cu join app_users u on u.user_id = cu.user_id
           where cu.clinic_id = %s""", (cid,)).fetchone()
    assert papel == "clinic_admin" and trocar is True
    assert conn.execute("select action from admin_audit where clinic_id = %s", (cid,)).fetchone()[0] == "criar_clinica"


def test_telefone_repetido_e_recusado(admin, clinica, supabase_falso):
    r = admin.post("/api/admin/clinicas", json={**NOVA, "telefone": "+5511900000001"})  # telefone da clínica de teste
    assert r.status_code == 422


def test_suspender_tira_o_acesso_da_clinica(admin, cliente, conn, clinica):  # noqa: F811
    recepcao = _usuario(conn, clinic_id=clinica.id)
    assert admin.patch(f"/api/admin/clinicas/{clinica.id}", json={"status": "suspensa"}).status_code == 200
    assert _como(cliente, recepcao).get("/api/clinics").json() == []
    assert conn.execute("select action from admin_audit where clinic_id = %s", (clinica.id,)).fetchone()[0] == "suspender"


def test_entrar_como_fica_registrado(admin, conn, clinica):
    assert admin.post(f"/api/admin/clinicas/{clinica.id}/entrar").status_code == 200
    assert conn.execute("select count(*) from admin_audit where clinic_id = %s and action = 'entrar_como'",
                        (clinica.id,)).fetchone()[0] == 1


def test_criar_e_desativar_usuario_da_clinica(admin, cliente, conn, clinica, supabase_falso):  # noqa: F811
    r = admin.post(f"/api/admin/clinicas/{clinica.id}/usuarios", json={"email": "Recep@Clinica.com", "papel": "reception"})
    assert r.status_code == 201 and r.json()["senha_provisoria"] and r.json()["email"] == "recep@clinica.com"
    uid = r.json()["id"]
    lista = admin.get(f"/api/admin/clinicas/{clinica.id}/usuarios").json()
    assert [u["papel"] for u in lista] == ["reception"] and lista[0]["senha_provisoria"] is True
    assert admin.patch(f"/api/admin/clinicas/{clinica.id}/usuarios/{uid}", json={"ativo": False}).status_code == 200
    assert admin.get(f"/api/admin/clinicas/{clinica.id}/usuarios").json()[0]["ativo"] is False


class WahaFalso:
    def __init__(self, *a, **k):
        pass

    def sessao(self, nome):
        return {"name": nome, "status": "WORKING", "me": {"id": "5511944445555@c.us"}, "config": {"webhooks": []}}

    def criar_sessao(self, nome, url, chave):
        return {"name": nome, "status": "STARTING"}

    def listar_sessoes(self):
        return [self.sessao("livre"), self.sessao("ocupada")]


def test_whatsapp_uma_sessao_por_clinica(admin, conn, clinica, outra_clinica, monkeypatch):
    monkeypatch.setattr(rotas_admin, "ClienteWaha", WahaFalso)
    assert admin.put(f"/api/admin/clinicas/{clinica.id}/whatsapp", json={"sessao": "ocupada"}).status_code == 200
    r = admin.put(f"/api/admin/clinicas/{outra_clinica.id}/whatsapp", json={"sessao": "ocupada"})
    assert r.status_code == 422 and "outra clínica" in r.json()["mensagem"]
    sessoes = {s["sessao"]: s["clinica"] for s in admin.get("/api/admin/whatsapp/sessoes").json()}
    assert sessoes["ocupada"] == "Clínica Teste A" and sessoes["livre"] is None


def test_nome_de_sessao_invalido(admin, clinica, monkeypatch):
    monkeypatch.setattr(rotas_admin, "ClienteWaha", WahaFalso)
    assert admin.put(f"/api/admin/clinicas/{clinica.id}/whatsapp", json={"sessao": "com espaço"}).status_code == 422


def test_plataforma_nao_mostra_chaves(admin):
    texto = admin.get("/api/admin/plataforma").text
    assert "sb_secret" not in texto and "sb_publishable" not in texto and "oc_sk" not in texto


@pytest.mark.parametrize(("nome", "slug"), [("Clínica Dental Ômega", "dental-omega"), ("Odonto & Cia", "odonto-cia")])
def test_slug(nome, slug):
    assert slug_de(nome) == slug
