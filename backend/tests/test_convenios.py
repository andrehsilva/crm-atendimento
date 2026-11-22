"""Etapa 22 — convênios (RN-CV, D92–D95)."""

import json

from app import convenios as C
from app import tratamentos as T
from app.agenda import servico as S
from app.agent import contexto
from tests.conftest import AGORA
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada
from tests.test_ferramentas_isis import _paciente_responde, _sessao


def _lista(conn, clinica, *nomes):
    for n in nomes:
        C.criar(conn, clinica.id, n)


def test_so_pergunta_no_primeiro_contato(conn, clinica):
    cl = S.carregar_clinica(conn, clinica.id)
    p = S.obter_ou_criar_paciente(conn, clinica.id, "+5511900001111", "Novo Silva", "web")
    assert C.precisa_perguntar(conn, cl, p)
    conn.execute("""insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at, status)
                    values (%s, %s, %s, %s, '2026-01-10 10:00-03', '2026-01-10 11:00-03', 'realizada')""",
                 (clinica.id, p["id"], clinica.prof_a, clinica.servico))
    assert not C.precisa_perguntar(conn, cl, p)  # já veio: não é primeiro contato
    novo = S.obter_ou_criar_paciente(conn, clinica.id, "+5511900002222", "Outro", "web")
    conn.execute("""update clinics set settings = settings || '{"perguntar_convenio": false}' where id = %s""", (clinica.id,))
    assert not C.precisa_perguntar(conn, S.carregar_clinica(conn, clinica.id), novo)  # clínica só particular


def test_confere_contra_a_lista(conn, clinica):
    _lista(conn, clinica, "Unimed Nacional", "Bradesco Saúde", "Bradesco Dental")
    p = S.obter_ou_criar_paciente(conn, clinica.id, "+5511900001111", "Novo Silva", "web")
    assert C.registrar(conn, clinica.id, p["id"], "convenio", "unimed")["rotulo"] == "Unimed Nacional"  # sem maiúscula/acento
    assert C.registrar(conn, clinica.id, p["id"], "convenio", "Amil")["motivo"] == "nao_atende"
    assert C.registrar(conn, clinica.id, p["id"], "convenio", "bradesco")["motivo"] == "mais_de_um"
    assert C.registrar(conn, clinica.id, p["id"], "convenio", None)["motivo"] == "qual_convenio"
    p = S.obter_ou_criar_paciente(conn, clinica.id, "+5511900001111", None, "web")
    assert C.rotulo(conn, p) == "Unimed Nacional"  # as recusas não apagaram o que já estava registrado


def test_sem_lista_registra_so_convenio(conn, clinica):
    p = S.obter_ou_criar_paciente(conn, clinica.id, "+5511900001111", "Novo Silva", "web")
    assert C.registrar(conn, clinica.id, p["id"], "convenio", "Qualquer um")["rotulo"] == "Convênio"
    assert [t["rotulo"] for t in T.tags(conn, clinica.id, [p["id"]])[p["id"]]] == ["Novo", "Convênio"]


def test_isis_pergunta_antes_de_marcar(conn, clinica):
    _lista(conn, clinica, "Unimed")
    s, f = _sessao(conn, clinica, convenio=None)
    assert "ainda não perguntado" in contexto.instrucoes(conn, s.clinica, s.paciente, AGORA)
    r = json.loads(f["preparar_agendamento"]("Limpeza", "2026-11-23T09:00", "Dra. A"))
    assert r["erro"] == "CONVENIO_PENDENTE"
    r = json.loads(f["registrar_convenio"]("convênio", "Amil"))
    assert not r["ok"] and r["convenios_atendidos"] == ["Unimed"] and "particular" in r["observacao"]
    assert json.loads(f["registrar_convenio"]("particular"))["registrado"] == "Particular"
    token = json.loads(f["preparar_agendamento"]("Limpeza", "2026-11-23T09:00", "Dra. A"))["token"]
    _paciente_responde(conn, s)
    assert json.loads(f["confirmar_acao"](token))["ok"]
    assert "Particular (já registrado" in contexto.instrucoes(conn, s.clinica, s.paciente, AGORA)


def test_config_e_cadastro(cliente, conn, clinica, outra_clinica):  # noqa: F811
    base = f"/api/clinics/{clinica.id}/config/convenios"
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    assert rec.post(base, json={"nome": "Unimed"}).status_code == 403  # só o administrador mexe na lista
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    r = adm.post(base, json={"nome": "Unimed"}).json()
    assert r["perguntar"] is True and [c["name"] for c in r["convenios"]] == ["Unimed"]
    assert adm.post(base, json={"nome": " unimed "}).status_code == 422  # repetido
    cid = r["convenios"][0]["id"]
    assert adm.patch(f"{base}/{cid}", json={"ativo": False}).json()["convenios"][0]["active"] is False
    assert adm.put(f"{base}/pergunta", json={"perguntar": False}).json()["perguntar"] is False
    # recepção edita o convênio no cadastro; convênio de outra clínica é recusado
    p = S.obter_ou_criar_paciente(conn, clinica.id, "+5511900001111", "Novo Silva", "web")
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    url = f"/api/clinics/{clinica.id}/patients/{p['id']}"
    assert rec.patch(url, json={"convenio": "convenio", "insurance_id": cid}).json()["insurance_id"] == cid
    C.criar(conn, outra_clinica.id, "Amil")
    alheio = C.listar(conn, outra_clinica.id)[0]["id"]
    assert rec.patch(url, json={"convenio": "convenio", "insurance_id": str(alheio)}).status_code == 422
