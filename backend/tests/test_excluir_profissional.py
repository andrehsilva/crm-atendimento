"""Etapa 28 — excluir profissional (D110, D111)."""

from app.agenda import servico as S
from tests.conftest import AGORA, as_
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada


def _url(clinica, pid, resto=""):
    return f"/api/clinics/{clinica.id}/config/profissionais/{pid}{resto}"


def _novo(adm, clinica, nome="Dra. Engano"):
    return adm.post(f"/api/clinics/{clinica.id}/config/profissionais",
                    json={"nome": nome, "procedimentos": [str(clinica.servico)]}).json()["id"]


def _corpo(nome, ativo):
    return {"nome": nome, "ativo": ativo, "procedimentos": []}


def test_sem_historico_apaga_de_vez(cliente, conn, clinica):  # noqa: F811
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    pid = _novo(adm, clinica)
    assert adm.get(_url(clinica, pid, "/exclusao")).json() == {"futuras": [], "tem_historico": False}
    assert adm.delete(_url(clinica, pid)).json() == {"resultado": "excluido"}
    assert conn.execute("select count(*) from professionals where id = %s", (pid,)).fetchone()[0] == 0


def test_com_consulta_marcada_bloqueia_excluir_e_desativar(cliente, conn, clinica):  # noqa: F811
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    S.marcar(conn, clinica.id, telefone="+5511944443333", nome="Rui Alves", professional_id=clinica.prof_b,
             service_id=clinica.servico, inicio=as_(25, 9), ator="recepcao", agora=AGORA)
    previa = adm.get(_url(clinica, clinica.prof_b, "/exclusao")).json()
    assert [f["paciente"] for f in previa["futuras"]] == ["Rui Alves"] and previa["tem_historico"]
    r = adm.delete(_url(clinica, clinica.prof_b))
    assert r.status_code == 409 and r.json()["codigo"] == "TEM_CONSULTAS_FUTURAS"
    r = adm.put(_url(clinica, clinica.prof_b), json=_corpo("Dr. B", False))
    assert r.status_code == 409 and r.json()["codigo"] == "TEM_CONSULTAS_FUTURAS"
    assert conn.execute("select active from professionals where id = %s", (clinica.prof_b,)).fetchone()[0]


def test_com_historico_arquiva_e_reativar_desarquiva(cliente, conn, clinica):  # noqa: F811
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    c = S.marcar(conn, clinica.id, telefone="+5511944443333", nome="Rui Alves", professional_id=clinica.prof_b,
                 service_id=clinica.servico, inicio=as_(25, 9), ator="recepcao", agora=AGORA)
    conn.execute("update appointments set status = 'cancelada' where id = %s", (c["id"],))  # só histórico
    assert adm.delete(_url(clinica, clinica.prof_b)).json() == {"resultado": "arquivado"}
    lista = {p["id"]: p for p in adm.get(f"/api/clinics/{clinica.id}/config/profissionais").json()["profissionais"]}
    assert lista[str(clinica.prof_b)]["arquivado"] and not lista[str(clinica.prof_b)]["ativo"]
    assert adm.put(_url(clinica, clinica.prof_b), json=_corpo("Dr. B", True)).status_code == 200
    lista = {p["id"]: p for p in adm.get(f"/api/clinics/{clinica.id}/config/profissionais").json()["profissionais"]}
    assert not lista[str(clinica.prof_b)]["arquivado"] and lista[str(clinica.prof_b)]["ativo"]


def test_recepcao_nao_exclui(cliente, conn, clinica):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    assert rec.delete(_url(clinica, clinica.prof_a)).status_code == 403
