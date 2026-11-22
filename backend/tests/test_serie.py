"""Etapa 21B — marcar série de sessões (RN-TR-07, D89)."""

from app import tratamentos as T
from app.agenda import servico as S
from tests.conftest import AGORA, as_
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada

TEL = "+5511977778888"


def _serie(conn, clinica, inicio, sessoes=4, tel=TEL, intervalo=7):
    return S.marcar_serie(conn, clinica.id, telefone=tel, nome="Rita Moura", professional_id=clinica.prof_a,
                          service_id=clinica.servico, inicio=inicio, sessoes=sessoes, intervalo_dias=intervalo, agora=AGORA)


def _fila(conn, clinica, kind):
    return conn.execute(
        """select count(*) from outbound_messages o join patients p on p.id = o.patient_id
           where o.clinic_id = %s and p.phone = %s and o.kind = %s and o.status = 'agendada'""",
        (clinica.id, TEL, kind)).fetchone()[0]


def test_marca_o_que_cabe_e_mostra_o_que_nao_coube(conn, clinica):
    # alguém já ocupa a 3ª semana (segunda 07/12 às 09:00 com a Dra. A)
    S.marcar(conn, clinica.id, telefone="+5511900005555", nome="Outra Pessoa", professional_id=clinica.prof_a,
             service_id=clinica.servico, inicio=as_(23, 9) + (as_(30, 9) - as_(23, 9)) * 2, ator="recepcao", agora=AGORA)
    r = _serie(conn, clinica, as_(23, 9))
    assert len(r["marcadas"]) == 3 and r["tratamento_aberto"]
    assert [f["codigo"] for f in r["falhas"]] == ["HORARIO_OCUPADO"] and r["falhas"][0]["inicio"].day == 7
    # sessões ligadas ao tratamento aberto automaticamente (4 previstas, semanal)
    t = T.do_paciente(conn, clinica.id, r["marcadas"][0]["patient_id"])[0]
    assert (t["sessoes_previstas"], t["intervalo_dias"], t["marcadas"]) == (4, 7, 3)
    # uma confirmação só, com todas as datas; um lembrete por sessão — menos a de 23/11, cujo lembrete seria
    # sex 20/11 09:00, antes do "agora" do teste (RN-MS-03: a confirmação já cobre)
    assert _fila(conn, clinica, "confirmacao") == 1 and _fila(conn, clinica, "lembrete") == 2
    corpo = conn.execute("select body from outbound_messages where clinic_id = %s and kind = 'confirmacao' and body like 'Olá, Rita%%'",
                         (clinica.id,)).fetchone()[0]
    assert "Suas 3 consultas" in corpo and corpo.count("📅") == 3 and "30/11" in corpo and "14/12" in corpo


def test_serie_passa_do_limite_de_consultas(conn, clinica):
    for h in (14, 15):  # limite de 2 já cheio com consultas comuns (outro procedimento não existe: mesmo serviço, outro dia)
        S.marcar(conn, clinica.id, telefone=TEL, nome="Rita Moura", professional_id=clinica.prof_b,
                 service_id=clinica.servico, inicio=as_(24, h), ator="recepcao", agora=AGORA)
    r = _serie(conn, clinica, as_(25, 9), sessoes=3)
    # o tratamento aberto liga as 2 consultas já marcadas do procedimento; as 3 da série também passam
    assert len(r["marcadas"]) == 3 and r["falhas"] == []


def test_nada_coube_nao_deixa_tratamento_vazio(conn, clinica):
    r = _serie(conn, clinica, as_(22, 9), sessoes=2)  # domingos: clínica fechada
    assert r["marcadas"] == [] and len(r["falhas"]) == 2 and not r["tratamento_aberto"]
    pid = S.obter_ou_criar_paciente(conn, clinica.id, TEL, None, "manual")["id"]
    assert T.do_paciente(conn, clinica.id, pid) == [] and _fila(conn, clinica, "confirmacao") == 0


def test_reaproveita_o_tratamento_aberto(conn, clinica):
    p = S.obter_ou_criar_paciente(conn, clinica.id, TEL, "Rita Moura", "manual")
    t = T.criar(conn, clinica.id, p["id"], service_id=clinica.servico, professional_id=clinica.prof_a,
                sessoes_previstas=8, intervalo_dias=7, orientacao="Sempre com a Dra. A")
    r = _serie(conn, clinica, as_(23, 9), sessoes=2)
    assert not r["tratamento_aberto"] and len(T.do_paciente(conn, clinica.id, p["id"])) == 1
    assert all(c["id"] for c in r["marcadas"]) and T.obter(conn, clinica.id, t["id"])["marcadas"] == 2


def test_rota(cliente, conn, clinica):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    corpo = {"telefone": TEL, "nome": "Rita Moura", "professional_id": str(clinica.prof_a), "service_id": str(clinica.servico),
             "inicio": "2099-03-02T09:00:00-03:00", "sessoes": 1}
    assert rec.post(f"/api/clinics/{clinica.id}/appointments/serie", json=corpo).status_code == 422  # mínimo 2
