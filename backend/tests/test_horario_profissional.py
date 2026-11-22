"""Etapa 24 — horário de atendimento por profissional (RN-AG-01, D99)."""

import pytest

from app.agenda import servico as S
from app.agenda.erros import AgendaError
from app.agent import contexto
from tests.conftest import AGORA, as_
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada

SO_TERCA_E_QUINTA = {"proprio": True, "dias": [
    {"weekday": 1, "faixas": [{"inicio": "08:00", "fim": "12:00"}]},
    {"weekday": 3, "faixas": [{"inicio": "08:00", "fim": "12:00"}, {"inicio": "14:00", "fim": "18:00"}]},
]}


def _url(clinica, resto=""):
    return f"/api/clinics/{clinica.id}/config/profissionais/{clinica.prof_b}/horario{resto}"


def _marcar(conn, clinica, inicio, prof=None, ator="recepcao", tel="+5511977770000"):
    return S.marcar(conn, clinica.id, telefone=tel, nome="Paciente Teste", professional_id=prof or clinica.prof_b,
                    service_id=clinica.servico, inicio=inicio, ator=ator, agora=AGORA)


def test_horario_proprio_vale_na_agenda_e_para_a_isis(cliente, conn, clinica):  # noqa: F811
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    r = adm.put(_url(clinica), json=SO_TERCA_E_QUINTA).json()
    assert r["proprio"] and [d["weekday"] for d in r["dias"]] == [1, 3] and r["afetadas"] == []
    with pytest.raises(AgendaError) as e:  # segunda: o Dr. B não atende mais
        _marcar(conn, clinica, as_(23, 9))
    assert e.value.codigo == "FORA_DO_HORARIO"
    assert _marcar(conn, clinica, as_(24, 9))  # terça 09:00 cabe
    with pytest.raises(AgendaError):  # terça à tarde não
        _marcar(conn, clinica, as_(24, 15))
    assert _marcar(conn, clinica, as_(26, 15))  # quinta tem a 2ª faixa
    # a assistente sabe os dias dele
    cl = S.carregar_clinica(conn, clinica.id)
    p = S.obter_ou_criar_paciente(conn, clinica.id, "+5511977770000", None, "web")
    assert "atende só: ter 08:00–12:00; qui 08:00–12:00 e 14:00–18:00" in contexto.instrucoes(conn, cl, p, AGORA)
    # voltar a seguir a clínica
    assert adm.put(_url(clinica), json={"proprio": False}).json()["proprio"] is False
    assert _marcar(conn, clinica, as_(23, 9), tel="+5511977770001")  # segunda volta a valer (outro paciente: limite de 2)


def test_consultas_fora_do_novo_horario_continuam_e_sao_listadas(cliente, conn, clinica):  # noqa: F811
    c = _marcar(conn, clinica, as_(23, 9))  # segunda com o Dr. B
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    imp = adm.post(_url(clinica, "/impacto"), json=SO_TERCA_E_QUINTA).json()
    assert [a["id"] for a in imp["afetadas"]] == [str(c["id"])]
    r = adm.put(_url(clinica), json=SO_TERCA_E_QUINTA).json()
    assert [a["paciente"] for a in r["afetadas"]] == ["Paciente Teste"]
    assert S.detalhar(conn, clinica.id, c["id"])["status"] == "agendada"  # D99: continua marcada


def test_validacoes_e_permissao(cliente, conn, clinica):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    assert rec.put(_url(clinica), json=SO_TERCA_E_QUINTA).status_code == 403
    assert rec.get(_url(clinica)).json()["proprio"] is False  # toda a equipe vê
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))

    def erro(dias):
        r = adm.put(_url(clinica), json={"proprio": True, "dias": dias})
        assert r.status_code == 422, r.text
        return r.json()["mensagem"]

    assert "fora do horário da clínica" in erro([{"weekday": 0, "faixas": [{"inicio": "07:00", "fim": "12:00"}]}])
    assert "não abre sábado" in erro([{"weekday": 5, "faixas": [{"inicio": "08:00", "fim": "12:00"}]}])
    assert "se sobrepõem" in erro([{"weekday": 0, "faixas": [{"inicio": "08:00", "fim": "12:00"}, {"inicio": "11:00", "fim": "15:00"}]}])
    assert "ao menos um dia" in erro([])
