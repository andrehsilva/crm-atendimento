"""Etapa 29 — arquivar ou excluir contato (D112–D115)."""

from app.agenda import servico as S
from app.painel import chat
from tests.conftest import AGORA, as_
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada

TEL = "+5516991122245"


def _contato(conn, clinica):
    return S.obter_ou_criar_paciente(conn, clinica.id, TEL, None, "whatsapp")["id"]


def _ids(r):
    return {x["id"] for x in r.json()}


def test_arquivar_tira_das_listas_e_volta_se_escrever(cliente, conn, clinica):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    pid = str(_contato(conn, clinica))
    base = f"/api/clinics/{clinica.id}"
    assert pid in _ids(rec.get(f"{base}/patients"))
    assert rec.post(f"{base}/patients/{pid}/arquivar").status_code == 200  # recepção pode arquivar (D114)
    assert pid not in _ids(rec.get(f"{base}/patients"))
    assert pid in _ids(rec.get(f"{base}/patients?arquivados=true"))
    assert pid not in {c["id"] for c in rec.get(f"{base}/kanban").json()["cards"]}
    # escreveu de novo: volta sozinho como Novo Contato (D113)
    conn.execute("update patients set crm_stage = 'cancelado' where id = %s", (pid,))
    chat.receber(conn, "teste-a", TEL, "oi, ainda dá para marcar?", responder=False)
    assert conn.execute("select archived_at is null, crm_stage from patients where id = %s", (pid,)).fetchone() == (True, "novo_contato")


def test_desarquivar(cliente, conn, clinica):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    pid = str(_contato(conn, clinica))
    base = f"/api/clinics/{clinica.id}"
    rec.post(f"{base}/patients/{pid}/arquivar")
    assert rec.post(f"{base}/patients/{pid}/desarquivar").status_code == 200
    assert pid in _ids(rec.get(f"{base}/patients"))


def test_nao_arquiva_quem_tem_consulta_marcada(cliente, conn, clinica):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    c = S.marcar(conn, clinica.id, telefone=TEL, nome="Ana Teste", professional_id=clinica.prof_a,
                 service_id=clinica.servico, inicio=as_(25, 9), ator="recepcao", agora=AGORA)
    r = rec.post(f"/api/clinics/{clinica.id}/patients/{c['patient_id']}/arquivar")
    assert r.status_code == 409 and r.json()["codigo"] == "TEM_CONSULTAS_FUTURAS"


def test_excluir_so_admin_e_so_sem_consultas(cliente, conn, clinica):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    pid = _contato(conn, clinica)
    chat.receber(conn, "teste-a", TEL, "oi", responder=False)
    base = f"/api/clinics/{clinica.id}/patients"
    assert rec.delete(f"{base}/{pid}").status_code == 403
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    assert adm.delete(f"{base}/{pid}").status_code == 200
    assert conn.execute("select count(*) from patients where id = %s", (pid,)).fetchone()[0] == 0
    assert conn.execute("select count(*) from conversations where patient_id = %s", (pid,)).fetchone()[0] == 0
    # quem já teve consulta não é excluído
    c = S.marcar(conn, clinica.id, telefone="+5511900001111", nome="Bia Teste", professional_id=clinica.prof_a,
                 service_id=clinica.servico, inicio=as_(25, 9), ator="recepcao", agora=AGORA)
    conn.execute("update appointments set status = 'cancelada' where id = %s", (c["id"],))
    assert adm.delete(f"{base}/{c['patient_id']}").status_code == 409
