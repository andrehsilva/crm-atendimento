"""Etapa 14A — campanhas (D69, D71, D72) e envio espaçado das mensagens em massa (D70)."""

from datetime import timedelta

import pytest

from app.agenda.erros import AgendaError
from app.mensagens import campanhas as C
from app.mensagens import envio
from tests.conftest import as_
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401
from tests.test_lembretes import SemCommit, WahaFalso, _cfg, ligada  # noqa: F401


def _paciente(conn, clinica, tel, nome="Maria Souza", optout=False):
    return conn.execute("insert into patients (clinic_id, phone, name, optout_disparos) values (%s, %s, %s, %s) returning id",
                        (clinica.id, tel, nome, optout)).fetchone()[0]


def test_texto_troca_nome_e_clinica():
    assert C.montar_texto("Olá, {nome}! A {clinica} deseja…", "Maria Souza", "Clínica A") == "Olá, Maria! A Clínica A deseja…"
    assert C.montar_texto("Olá, {nome}! Boas festas.", None, "Clínica A") == "Olá! Boas festas."


def test_publico_nunca_inclui_quem_pediu_parar(conn, clinica):
    _paciente(conn, clinica, "+5511955550001")
    _paciente(conn, clinica, "+5511955550002", optout=True)
    assert C.previa(conn, clinica.id, "todos")["total"] == 1
    assert C.previa(conn, clinica.id, "com_consulta")["total"] == 0


def test_criar_poe_na_fila_e_cancelar_tira(conn, clinica):
    _paciente(conn, clinica, "+5511955550001", "Ana Lima")
    _paciente(conn, clinica, "+5511955550002", "Bia")
    r = C.criar(conn, clinica.id, titulo="Natal", texto="Olá, {nome}! Feliz Natal da {clinica}.", publico="todos",
                enviar_em=as_(24, 10), autor=None, agora=as_(20, 10))
    corpos = sorted(x[0] for x in conn.execute("select body from outbound_messages where campaign_id = %s", (r["id"],)).fetchall())
    assert r["total"] == 2 and corpos == ["Olá, Ana! Feliz Natal da Clínica Teste A.", "Olá, Bia! Feliz Natal da Clínica Teste A."]
    assert C.cancelar(conn, clinica.id, r["id"]) == 2
    with pytest.raises(AgendaError):
        C.criar(conn, clinica.id, titulo="x", texto="x", publico="todos", enviar_em=as_(19, 10), autor=None, agora=as_(20, 10))


def test_massa_sai_espacada_e_lembrete_passa_na_frente(conn, ligada):
    for i in range(3):
        _paciente(conn, ligada, f"+551195555000{i}", f"Pessoa {i}")
    C.criar(conn, ligada.id, titulo="Natal", texto="Feliz Natal, {nome}!", publico="todos",
            enviar_em=as_(23, 10), autor=None, agora=as_(20, 10))
    w, c, cfg = WahaFalso(), SemCommit(conn), _cfg(lista="", env="prod")
    t = as_(23, 10, 0)
    assert envio.enviar_pendentes(c, t, w, s=cfg) == 1  # só uma campanha por vez
    assert envio.enviar_pendentes(c, t + timedelta(seconds=10), w, s=cfg) == 0  # ainda dentro do intervalo
    assert envio.enviar_pendentes(c, t + timedelta(seconds=46), w, s=cfg) == 1  # passou o intervalo (máx. 45 s)
    assert 20 <= envio.intervalo_massa("0000-00ff") <= 45


def test_so_admin_cria_e_a_equipe_ve(cliente, conn, clinica):  # noqa: F811
    _paciente(conn, clinica, "+5511955550001")
    base = f"/api/clinics/{clinica.id}/campanhas"
    rec = _usuario(conn, clinic_id=clinica.id)
    adm = _usuario(conn, clinic_id=clinica.id, papel="clinic_admin")
    corpo = {"titulo": "Férias", "texto": "Olá, {nome}!", "publico": "todos", "enviar_em": "2099-12-20T10:00:00-03:00"}
    assert _como(cliente, rec).post(base, json=corpo).status_code == 403
    assert _como(cliente, adm).post(base, json=corpo).status_code == 201
    lista = _como(cliente, rec).get(base).json()
    assert lista["campanhas"][0]["total"] == 1 and len(lista["modelos"]) == 3
    assert _como(cliente, rec).post(f"{base}/previa", json={"publico": "todos"}).json()["total"] == 1
