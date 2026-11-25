"""Etapa 21A — tratamentos em andamento (RN-TR, D87–D90)."""

import json
from datetime import date, timedelta
from uuid import uuid4

import pytest

from app import notificacoes as N
from app import relatorios as R
from app import tratamentos as T
from app.agenda import servico as S
from app.agenda.erros import AgendaError
from app.agent import contexto
from tests.conftest import AGORA, as_
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada
from tests.test_ferramentas_isis import _sessao
from tests.test_relatorios import _abrir, _consulta

TEL = "+5511977776666"


@pytest.fixture
def canal(conn, clinica):
    """Procedimento de tratamento (a Ísis pode marcar), feito pela Dra. A."""
    sid = conn.execute("insert into services (clinic_id, name, duration_min) values (%s, 'Prótese', 60) returning id",
                       (clinica.id,)).fetchone()[0]
    conn.execute("insert into professional_services (clinic_id, professional_id, service_id) values (%s, %s, %s)",
                 (clinica.id, clinica.prof_a, sid))
    return sid


def _paciente(conn, clinica, tel=TEL, nome="Paciente Ísis"):
    return S.obter_ou_criar_paciente(conn, clinica.id, tel, nome, "web")


def _marcar(conn, clinica, servico, inicio, ator="isis", tel=TEL):
    return S.marcar(conn, clinica.id, telefone=tel, nome="Paciente Ísis", professional_id=clinica.prof_a,
                    service_id=servico, inicio=inicio, ator=ator, agora=AGORA)


def _tratamento(conn, clinica, canal, tel=TEL, **kw):
    p = _paciente(conn, clinica, tel)
    return T.criar(conn, clinica.id, p["id"], service_id=canal, professional_id=clinica.prof_a,
                   sessoes_previstas=kw.get("sessoes", 4), intervalo_dias=7, orientacao=kw.get("orientacao"))


def test_aguardando_isis_nao_marca_a_sessao_mas_marca_outro_procedimento(conn, clinica, canal):
    t = _tratamento(conn, clinica, canal)
    T.aguardar(conn, clinica.id, t["id"], motivo_espera="protetico", motivo_texto=None, previsao=None)
    with pytest.raises(AgendaError) as e:
        _marcar(conn, clinica, canal, as_(24, 9))
    assert e.value.codigo == "TRATAMENTO_AGUARDANDO" and "protético" in e.value.mensagem
    assert _marcar(conn, clinica, clinica.servico, as_(24, 10))["procedimento"] == "Limpeza"  # D87: outro procedimento pode
    assert _marcar(conn, clinica, canal, as_(25, 9), ator="recepcao")  # a recepção decide


def test_sessoes_de_tratamento_nao_contam_no_limite(conn, clinica, canal):
    _tratamento(conn, clinica, canal)
    _marcar(conn, clinica, clinica.servico, as_(23, 9))
    _marcar(conn, clinica, clinica.servico, as_(23, 10))  # limite de 2 atingido com consultas comuns
    for dia in (24, 25, 26):  # mas as sessões do tratamento seguem (RN-TR-08)
        assert _marcar(conn, clinica, canal, as_(dia, 9))
    with pytest.raises(AgendaError) as e:  # uma 3ª consulta comum continua barrada
        _marcar(conn, clinica, clinica.servico, as_(27, 9))
    assert e.value.codigo == "LIMITE_CONSULTAS"
    ligadas = conn.execute("select count(*) from appointments where clinic_id = %s and treatment_id is not null", (clinica.id,)).fetchone()[0]
    assert ligadas == 3


def test_abrir_tratamento_liga_as_consultas_ja_marcadas_e_so_um_aberto_por_procedimento(conn, clinica, canal):
    c = _marcar(conn, clinica, canal, as_(24, 9))
    t = _tratamento(conn, clinica, canal)
    assert t["marcadas"] == 1 and conn.execute("select treatment_id from appointments where id = %s", (c["id"],)).fetchone()[0] == t["id"]
    with pytest.raises(AgendaError):
        _tratamento(conn, clinica, canal)


def test_retomar_chama_o_paciente(conn, clinica, canal):
    t = _tratamento(conn, clinica, canal)
    cl = S.carregar_clinica(conn, clinica.id)
    with pytest.raises(AgendaError):  # só retoma o que está aguardando
        T.retomar(conn, cl, t["id"], texto=None)
    T.aguardar(conn, clinica.id, t["id"], motivo_espera="outro", motivo_texto="Aguardando laudo", previsao=date(2026, 11, 30))
    r = T.retomar(conn, cl, t["id"], texto=None)
    assert r["status"] == "em_andamento" and r["previsao"] is None
    corpo = conn.execute("select body from outbound_messages where clinic_id = %s and kind = 'tratamento'", (clinica.id,)).fetchone()[0]
    assert corpo.startswith("Olá, Paciente!") and "Prótese" in corpo and "Clínica Teste A" in corpo
    assert _marcar(conn, clinica, canal, as_(24, 9))  # retomado: a Ísis volta a marcar


def test_tags_automaticas(conn, clinica, canal):
    novo = _paciente(conn, clinica, "+5511900001111", "Novo Silva")
    _consulta(conn, clinica, "2026-01-10 10:00-03", "realizada", "Recorrente Souza", "+5511900002222")
    _consulta(conn, clinica, "2026-03-10 10:00-03", "realizada", "Recorrente Souza", "+5511900002222")
    rec = _paciente(conn, clinica, "+5511900002222")
    t = _tratamento(conn, clinica, canal, tel="+5511900003333")
    T.aguardar(conn, clinica.id, t["id"], motivo_espera="protetico", motivo_texto=None, previsao=None)
    tags = T.tags(conn, clinica.id, [novo["id"], rec["id"], t["patient_id"]])
    assert [x["codigo"] for x in tags[novo["id"]]] == ["novo"]
    assert [x["codigo"] for x in tags[rec["id"]]] == ["recorrente"]
    assert [x["rotulo"] for x in tags[t["patient_id"]]] == ["Novo", "Aguardando protético"]


def test_recall_respeita_tratamento_e_volta_em(conn, clinica, canal):
    hoje = date.today()
    _consulta(conn, clinica, "2025-01-10 10:00-03", "realizada", "Em Tratamento", "+5511955550001")  # sumiu, mas está em tratamento
    _tratamento(conn, clinica, canal, tel="+5511955550001")
    _consulta(conn, clinica, "2025-01-10 10:00-03", "realizada", "Volta Depois", "+5511955550002")  # sumiu, volta só no futuro
    t2 = _tratamento(conn, clinica, canal, tel="+5511955550002")
    T.encerrar(conn, clinica.id, t2["id"], status="concluido", volta_em=hoje + timedelta(days=30))
    recente = (hoje - timedelta(days=20)).isoformat() + " 10:00-03"
    _consulta(conn, clinica, recente, "realizada", "Volta Agora", "+5511955550003")  # veio há pouco, mas a volta já venceu
    t3 = _tratamento(conn, clinica, canal, tel="+5511955550003")
    T.encerrar(conn, clinica.id, t3["id"], status="concluido", volta_em=hoje - timedelta(days=1))
    wb = _abrir(R.gerar(conn, clinica.id, "recall", de=hoje, ate=hoje, prof=None, meses=6)[0])
    assert [r[0] for r in wb["Chamar de volta"].iter_rows(min_row=2, values_only=True)] == ["Volta Agora"]


def test_contexto_da_isis_e_ferramenta(conn, clinica, canal):
    s, f = _sessao(conn, clinica)
    t = T.criar(conn, clinica.id, s.paciente["id"], service_id=canal, professional_id=clinica.prof_a, sessoes_previstas=4,
                intervalo_dias=7, orientacao="Não marcar antes de 10 dias da extração")
    texto = contexto._tratamentos(conn, s.clinica, s.paciente, s.tz)
    assert "EM ANDAMENTO" in texto and "0 de 4" in texto and "10 dias da extração" in texto
    T.aguardar(conn, clinica.id, t["id"], motivo_espera="protetico", motivo_texto=None, previsao=date(2026, 11, 28))
    assert "AGUARDANDO protético (previsão: 28/11)" in contexto._tratamentos(conn, s.clinica, s.paciente, s.tz)
    r = json.loads(f["horarios_livres"]("Prótese", "2026-11-24"))
    assert r["erro"] == "TRATAMENTO_AGUARDANDO"
    assert json.loads(f["horarios_livres"]("Limpeza", "2026-11-24"))["ok"]  # outro procedimento segue
    # o pedido vira aviso no sino
    itens = N.listar(conn, clinica.id, uuid4())["itens"]
    pedido = next(i for i in itens if i["tipo"] == "tratamento_pedido")
    assert pedido["titulo"] == "Paciente Ísis quer marcar Prótese" and "previsão 28/11" in pedido["texto"]


def test_sino_previsao_vencida_e_falta(conn, clinica, canal):
    t = _tratamento(conn, clinica, canal)
    a = conn.execute(
        """insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at, treatment_id)
           values (%s, %s, %s, %s, %s, %s, %s) returning id""",
        (clinica.id, t["patient_id"], clinica.prof_a, canal, AGORA - timedelta(days=2),
         AGORA - timedelta(days=2, hours=-1), t["id"])).fetchone()[0]
    S.mudar_status(conn, clinica.id, appointment_id=a, novo="faltou", ator="recepcao")
    T.aguardar(conn, clinica.id, t["id"], motivo_espera="exame", motivo_texto=None, previsao=AGORA.date() - timedelta(days=1))
    itens = {i["tipo"]: i for i in N.listar(conn, clinica.id, uuid4())["itens"]}
    assert itens["faltou_sessao"]["titulo"] == "Paciente Ísis faltou à sessão 1 de 4"
    assert itens["tratamento_previsao"]["titulo"].startswith("Prótese de Paciente Ísis: a previsão era")


def test_rotas_e_isolamento(cliente, conn, clinica, outra_clinica, canal):  # noqa: F811
    p = _paciente(conn, clinica)
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    r = rec.post(f"/api/clinics/{clinica.id}/patients/{p['id']}/tratamentos",
                 json={"service_id": str(canal), "sessoes_previstas": 4, "intervalo_dias": 7})
    assert r.status_code == 201 and r.json()["tratamentos"][0]["status"] == "em_andamento"
    tid = r.json()["tratamentos"][0]["id"]
    r = rec.post(f"/api/clinics/{clinica.id}/tratamentos/{tid}/aguardar", json={"motivo": "protetico"})
    assert r.json()["tags"][-1]["codigo"] == "aguardando"
    assert "Prótese" in rec.get(f"/api/clinics/{clinica.id}/tratamentos/{tid}/retomar").json()["texto"]
    # outra clínica não enxerga nem mexe
    estranho = _como(cliente, _usuario(conn, clinic_id=outra_clinica.id, papel="clinic_admin"))
    assert estranho.get(f"/api/clinics/{clinica.id}/patients/{p['id']}/tratamentos").status_code == 403
    assert estranho.post(f"/api/clinics/{outra_clinica.id}/tratamentos/{tid}/retomar", json={}).status_code == 422
    assert estranho.get(f"/api/clinics/{outra_clinica.id}/patients/{p['id']}/tratamentos").status_code == 422


def test_ferramenta_avisa_a_equipe_sem_marcar(conn, clinica, canal):
    s, f = _sessao(conn, clinica)
    t = T.criar(conn, clinica.id, s.paciente["id"], service_id=canal, professional_id=clinica.prof_a, sessoes_previstas=None,
                intervalo_dias=None, orientacao=None)
    assert json.loads(f["avisar_pedido_tratamento"]("Prótese"))["ok"] is False  # em andamento: não é caso de aviso
    T.aguardar(conn, clinica.id, t["id"], motivo_espera="protetico", motivo_texto=None, previsao=None)
    assert json.loads(f["avisar_pedido_tratamento"]("prótese"))["ok"]
    assert conn.execute("select perguntou_em is not null from treatments where id = %s", (t["id"],)).fetchone()[0]


def test_profissional_do_tratamento_precisa_fazer_o_procedimento(conn, clinica, canal):
    p = _paciente(conn, clinica)
    with pytest.raises(AgendaError) as e:  # o Dr. B não faz Prótese
        T.criar(conn, clinica.id, p["id"], service_id=canal, professional_id=clinica.prof_b, sessoes_previstas=None,
                intervalo_dias=None, orientacao=None)
    assert e.value.codigo == "PROFISSIONAL_NAO_FAZ"
