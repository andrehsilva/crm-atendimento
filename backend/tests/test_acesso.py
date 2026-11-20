"""Etapa 7A — login e isolamento entre clínicas (cenário C16, RN-MT-03).

O Supabase é simulado: o "crachá" de teste é "tok-<id do usuário>". O banco é o de verdade, dentro
da transação do teste (desfeita no fim).
"""

import re
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.agenda.erros import AgendaError
from app.api.auth import validar_senha
from app.auth import supabase as sb
from app.auth.usuarios import senha_provisoria
from app.db import get_conn
from app.main import app


@pytest.fixture
def cliente(conn, monkeypatch):
    def conferir(token):
        if not token.startswith("tok-"):
            raise sb.AuthErro("inválido", 401)
        return {"sub": token[4:]}

    monkeypatch.setattr(sb, "conferir_token", conferir)
    app.dependency_overrides[get_conn] = lambda: conn
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)


def _usuario(conn, *, clinic_id=None, papel="reception", super_admin=False, trocar=False) -> UUID:
    uid = uuid4()
    conn.execute("insert into app_users (user_id, email, must_change_password) values (%s, %s, %s)",
                 (uid, f"{uid}@teste.com", trocar))
    if clinic_id:
        conn.execute("insert into clinic_users (clinic_id, user_id, role) values (%s, %s, %s)", (clinic_id, uid, papel))
    if super_admin:
        conn.execute("insert into platform_admins (user_id) values (%s)", (uid,))
    return uid


def _como(cliente, uid):
    cliente.cookies.clear()
    cliente.cookies.set("isis_at", f"tok-{uid}")
    return cliente


def test_sem_login_nao_entra(cliente, clinica):
    r = cliente.get(f"/api/clinics/{clinica.id}/dashboard")
    assert r.status_code == 401 and r.json()["codigo"] == "NAO_AUTENTICADO"


def test_lista_so_as_clinicas_do_usuario(cliente, conn, clinica, outra_clinica):
    ids = {c["id"] for c in _como(cliente, _usuario(conn, clinic_id=clinica.id)).get("/api/clinics").json()}
    assert ids == {str(clinica.id)}


def test_super_admin_ve_todas(cliente, conn, clinica, outra_clinica):
    ids = {c["id"] for c in _como(cliente, _usuario(conn, super_admin=True)).get("/api/clinics").json()}
    assert {str(clinica.id), str(outra_clinica.id)} <= ids
    assert _como(cliente, _usuario(conn, super_admin=True)).get(f"/api/clinics/{outra_clinica.id}/dashboard").status_code == 200


# Logo na tela de entrar (antes do login): só a imagem, nada de nome/telefone/dados.
PUBLICAS = {"/api/auth/marca/{clinic_id}/logo"}


def _rotas_da_clinica():
    for caminho, metodos in app.openapi()["paths"].items():
        if "{clinic_id}" in caminho and caminho not in PUBLICAS:
            for metodo in sorted(metodos):
                yield metodo.upper(), caminho


def test_rotas_publicas_com_clinic_id_sao_so_estas():
    """Exceções da varredura C16: abertas de propósito e sem dado da clínica além da imagem."""
    assert PUBLICAS == {"/api/auth/marca/{clinic_id}/logo"}


def test_c16_nenhuma_rota_entrega_dado_de_outra_clinica(cliente, conn, clinica, outra_clinica):
    """Usuário da clínica A tenta TODAS as rotas com o id da clínica B: todas devem recusar (403)."""
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    rotas = list(_rotas_da_clinica())
    assert len(rotas) > 20  # garante que o teste está mesmo varrendo as rotas
    falhas = []
    for metodo, caminho in rotas:
        url = caminho.replace("{clinic_id}", str(outra_clinica.id))
        url = re.sub(r"\{[^}]+\}", str(uuid4()), url)  # demais parâmetros: qualquer id
        r = c.request(metodo, url, json={})
        if r.status_code != 403:
            falhas.append(f"{metodo} {caminho} → {r.status_code}")
    assert falhas == []


def test_clinic_id_na_consulta_tambem_e_conferido(cliente, conn, clinica, outra_clinica):
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id))
    assert c.get(f"/api/dev/relogio?clinic_id={outra_clinica.id}").status_code == 403
    assert c.get(f"/api/dev/relogio?clinic_id={clinica.id}").status_code == 200


def test_usuario_desativado_nao_entra(cliente, conn, clinica):
    uid = _usuario(conn, clinic_id=clinica.id)
    conn.execute("update app_users set active = false where user_id = %s", (uid,))
    assert _como(cliente, uid).get(f"/api/clinics/{clinica.id}/dashboard").status_code == 403


def test_senha_provisoria_obriga_troca(cliente, conn, clinica):
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id, trocar=True))
    r = c.get(f"/api/clinics/{clinica.id}/dashboard")
    assert r.status_code == 403 and r.json()["codigo"] == "TROCAR_SENHA"
    me = c.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["trocar_senha"] is True


def test_recepcao_nao_muda_configuracoes(cliente, conn, clinica):
    corpo = {"ativo": True, "texto": "Parabéns, {nome}!", "hora": "09:00"}
    r = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception")).put(
        f"/api/clinics/{clinica.id}/mensagens/aniversario", json=corpo)
    assert r.status_code == 403
    r = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin")).put(
        f"/api/clinics/{clinica.id}/mensagens/aniversario", json=corpo)
    assert r.status_code == 200


def test_reset_da_demo_so_super_admin(cliente, conn, clinica):
    assert _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin")).post("/api/dev/reset-demo").status_code == 403


def test_chat_web_de_teste_continua_aberto(cliente, clinica):
    cliente.cookies.clear()
    assert cliente.get("/api/web/teste-a/history", params={"telefone": "+5511911112222"}).status_code == 200


def test_cracha_falso_nao_entra(cliente, clinica):
    cliente.cookies.clear()
    cliente.cookies.set("isis_at", "inventado")
    assert cliente.get(f"/api/clinics/{clinica.id}/dashboard").status_code == 401


@pytest.mark.parametrize("senha", ["curta1", "semnumeroaqui", "12345678"])
def test_senha_fraca_e_recusada(senha):
    with pytest.raises(AgendaError):
        validar_senha(senha)


def test_senha_provisoria_tem_letras_e_numeros():
    for _ in range(20):
        s = senha_provisoria()
        validar_senha(s)
        assert not set(s) & set("0O1lI")
