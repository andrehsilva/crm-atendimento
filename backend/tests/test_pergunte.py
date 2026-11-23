"""Etapa 30 (D117–D120): "Pergunte à assistente" — só leitura e só a clínica de quem pergunta."""

import psycopg
import pytest

from app.config import get_settings
from app.consulta_equipe import leitura
from app.consulta_equipe.leitura import ConsultaRecusada
from tests.conftest import as_
from tests.test_acesso import (  # noqa: F401 — fixture reaproveitada
    _como,
    _usuario,
    cliente,
)


def _paciente(conn, clinica, nome, fone):
    return conn.execute("insert into patients (clinic_id, name, phone) values (%s, %s, %s) returning id",
                        (clinica.id, nome, fone)).fetchone()[0]


def _consulta(conn, clinica, pac, dia, status="realizada"):
    conn.execute(
        """insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at, status, source)
           values (%s, %s, %s, %s, %s, %s, %s, 'recepcao')""",
        (clinica.id, pac, clinica.prof_a, clinica.servico, as_(dia, 9), as_(dia, 10), status))


def test_so_ve_a_propria_clinica(conn, clinica, outra_clinica):
    andre = _paciente(conn, clinica, "André Souza", "+5516990000001")
    _paciente(conn, outra_clinica, "André Lima", "+5516990000002")
    _consulta(conn, clinica, andre, 10)
    _consulta(conn, clinica, andre, 12)
    r = leitura.executar(conn, clinica.id, "select nome from pacientes where nome ilike 'andré%'")
    assert r["linhas"] == [["André Souza"]]
    r = leitura.executar(conn, clinica.id, "select count(*) as vezes from consultas where paciente ilike 'andré%' and situacao = 'realizada'")
    assert r["colunas"] == ["vezes"] and r["linhas"] == [[2]]
    # a outra clínica não enxerga nada da primeira
    r = leitura.executar(conn, outra_clinica.id, "select count(*) from consultas")
    assert r["linhas"] == [[0]]


def test_trocar_a_clinica_pela_consulta_nao_funciona(conn, clinica, outra_clinica):
    """A clínica fica numa tabela temporária que o papel de leitura não lê nem escreve."""
    _paciente(conn, outra_clinica, "Outra", "+5516990000003")
    for sql in ("select * from pg_temp._isis_clinica",
                f"select count(*) from pacientes, (select set_config('isis.clinica', '{outra_clinica.id}', true)) x"):
        try:
            r = leitura.executar(conn, clinica.id, sql)
            assert r["linhas"] == [[0]]
        except ConsultaRecusada:
            pass


@pytest.mark.parametrize("sql", [
    "delete from pacientes",
    "update patients set name = 'x'",
    "insert into patients (clinic_id, name, phone) values (gen_random_uuid(), 'x', '+5516990000009')",
    "drop table patients",
    "select 1; delete from patients",
    "select 1 -- comentário",
    "select * from public.patients",
    "select * from public.clinic_ai",
    "select * from public.app_users",
    "select * from vault.decrypted_secrets",
    "select pg_sleep(10)",
    "with x as (delete from patients returning *) select * from x",
    "select * from pg_temp._isis_clinica",
    "select * from query_to_xml('select * from public.patients', true, false, '')",
])
def test_recusa_escrita_e_tabelas_de_fora(conn, clinica, sql):
    with pytest.raises(ConsultaRecusada):
        leitura.executar(conn, clinica.id, sql)
    # a conexão continua usável e com o papel normal depois da recusa
    assert conn.execute("select current_user").fetchone()[0] != "isis_leitura"


def test_limite_de_linhas(conn, clinica):
    r = leitura.executar(conn, clinica.id, "select g from generate_series(1, 500) g")
    assert len(r["linhas"]) == leitura.LIMITE and r["truncado"]


def test_sem_clinica_marcada_nao_ve_nada(conn, clinica):
    _paciente(conn, clinica, "Fulano", "+5516990000004")
    with conn.transaction():
        conn.execute("set local role isis_leitura")
        assert conn.execute("select count(*) from leitura.pacientes").fetchone()[0] == 0


def test_conexao_limpa_fica_so_leitura():
    """Na rota a conexão é separada: a transação inteira é só-leitura (trava extra além do papel)."""
    url = get_settings().database_url
    if not url:
        pytest.skip("DATABASE_URL não configurada")
    with psycopg.connect(url) as c:
        cid = c.execute("select id from clinics limit 1").fetchone()[0]
        c.rollback()
        r = leitura.executar(c, cid, "select count(*) from pacientes")
        assert isinstance(r["linhas"][0][0], int)
        with pytest.raises(ConsultaRecusada):
            leitura.executar(c, cid, "select * from patients")
        assert c.execute("select current_user").fetchone()[0] == "postgres"
        c.rollback()


# --- rota e agente (IA falsa: chama a ferramenta e responde com o resultado) ---------------------------------


class _IAQueConsulta:
    def __init__(self, tools, **_):
        self.tools = {f.__name__: f for f in tools}

    def run(self, _entrada):
        r = self.tools["consultar"]("select count(*) as n from consultas where situacao = 'realizada'")
        self.tools["consultar"]("delete from pacientes")  # tentativa de escrita: só volta erro
        return type("R", (), {"content": f"Resultado: {r}"})()


@pytest.fixture
def leitura_no_teste(conn, clinica):
    from app.api import pergunte

    conn.execute("update clinics set pergunte_liberado = true where id = %s", (clinica.id,))
    from app.main import app

    app.dependency_overrides[pergunte.conexao_leitura] = lambda: conn
    yield
    app.dependency_overrides.pop(pergunte.conexao_leitura, None)


def test_rota_responde_e_registra_gasto(cliente, conn, clinica, monkeypatch, leitura_no_teste):  # noqa: F811
    from app.consulta_equipe import agente

    monkeypatch.setattr(agente, "Agent", _IAQueConsulta)
    andre = _paciente(conn, clinica, "André", "+5516990000005")
    _consulta(conn, clinica, andre, 10)
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    r = rec.post(f"/api/clinics/{clinica.id}/pergunte", json={"mensagens": [{"autor": "equipe", "texto": "quantas consultas?"}]})
    assert r.status_code == 200 and '"linhas": [[1]]' in r.json()["resposta"]
    assert conn.execute("select count(*) from patients where id = %s", (andre,)).fetchone()[0] == 1
    tipo, conversa, tools = conn.execute(
        "select tipo, conversation_id, tools from agent_runs where clinic_id = %s order by created_at desc limit 1", (clinica.id,)).fetchone()
    assert tipo == "equipe" and conversa is None
    assert tools[0]["linhas"] == 1 and "erro" in tools[1]


def test_sem_ia_nao_chama_o_modelo(cliente, conn, clinica, monkeypatch, leitura_no_teste):  # noqa: F811
    from app.consulta_equipe import agente

    conn.execute("update clinic_ai set usa_plataforma = false where clinic_id = %s", (clinica.id,))
    monkeypatch.setattr(agente, "Agent", lambda *a, **k: pytest.fail("não devia chamar a IA"))
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    r = rec.post(f"/api/clinics/{clinica.id}/pergunte", json={"mensagens": [{"autor": "equipe", "texto": "oi"}]})
    assert r.json()["resposta"] == agente.MSG_SEM_IA


def test_outra_clinica_nao_pode_perguntar(cliente, conn, clinica, outra_clinica, leitura_no_teste):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=outra_clinica.id, papel="clinic_admin"))
    r = rec.post(f"/api/clinics/{clinica.id}/pergunte", json={"mensagens": [{"autor": "equipe", "texto": "oi"}]})
    assert r.status_code == 403


def test_bloqueado_pelo_admin_geral(cliente, conn, clinica, leitura_no_teste):  # noqa: F811
    conn.execute("update clinics set pergunte_liberado = false where id = %s", (clinica.id,))
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    r = rec.post(f"/api/clinics/{clinica.id}/pergunte", json={"mensagens": [{"autor": "equipe", "texto": "oi"}]})
    assert r.status_code == 403
    assert rec.get(f"/api/clinics/{clinica.id}").json()["pergunte_liberado"] is False
