"""Etapa 7C — Configurações da clínica (Perfil, Horários, Procedimentos, Profissionais, Assistente, Usuários)."""

from datetime import datetime, timedelta

import pytest

from app.agenda import servico as S
from tests.conftest import TZ
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada


@pytest.fixture
def admin_c(cliente, conn, clinica):  # noqa: F811
    return _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))


def _url(clinica, resto):
    return f"/api/clinics/{clinica.id}/config/{resto}"


def _proxima_segunda_10h() -> datetime:
    agora = datetime.now(TZ)
    d = agora.date() + timedelta(days=3)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return datetime.combine(d, datetime.min.time(), tzinfo=TZ).replace(hour=10)


def test_recepcao_ve_mas_nao_muda(cliente, conn, clinica):  # noqa: F811
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    assert c.get(_url(clinica, "perfil")).status_code == 200
    assert c.put(_url(clinica, "perfil"), json={"nome": "Outro nome"}).status_code == 403


def test_perfil(admin_c, conn, clinica):
    r = admin_c.put(_url(clinica, "perfil"), json={"nome": "Clínica Nova", "endereco": "Rua A, 1",
                                                   "telefone_urgencia": "(11) 98888-7777", "sobre": "Aceitamos acompanhantes."})
    assert r.status_code == 200 and r.json()["telefone_urgencia"] == "+5511988887777"
    from app.agent.contexto import dados_clinica
    assert dados_clinica(conn, S.carregar_clinica(conn, clinica.id))["sobre_a_clinica"] == "Aceitamos acompanhantes."


def test_horario_invalido_e_recusado(admin_c, clinica):
    assert admin_c.put(_url(clinica, "horarios/0"), json={"ativo": True, "inicio": "18:00", "fim": "08:00"}).status_code == 422
    r = admin_c.put(_url(clinica, "horarios/0"), json={"ativo": True, "inicio": "08:00", "fim": "12:00",
                                                       "pausas": [{"inicio": "11:00", "fim": "13:00"}]})
    assert r.status_code == 422  # pausa fora do expediente


def test_desligar_dia_avisa_consultas_e_some_da_agenda(admin_c, conn, clinica):
    inicio = _proxima_segunda_10h()
    S.marcar(conn, clinica.id, telefone="+5511955554444", nome="Bia Lopes", professional_id=clinica.prof_a,
             service_id=clinica.servico, inicio=inicio, ator="recepcao")
    imp = admin_c.post(_url(clinica, "horarios/0/impacto"), json={"ativo": False}).json()
    assert [a["paciente"] for a in imp["afetadas"]] == ["Bia Lopes"]
    assert admin_c.put(_url(clinica, "horarios/0"), json={"ativo": False}).json()["afetadas"]
    # a consulta continua marcada (regra da spec 07), mas a segunda não oferece mais horários novos
    assert S.horarios_livres(conn, clinica.id, clinica.servico, inicio.date(), inicio.date()) == []
    dias = {d["weekday"]: d for d in admin_c.get(_url(clinica, "horarios")).json()["dias"]}
    assert dias[0]["ativo"] is False and dias[1]["ativo"] is True and len(dias) == 7


def test_pausa_nova_tira_horarios(admin_c, conn, clinica):
    dia = _proxima_segunda_10h().date()
    admin_c.put(_url(clinica, "horarios/0"), json={"ativo": True, "inicio": "08:00", "fim": "18:00",
                                                   "pausas": [{"inicio": "09:00", "fim": "11:00"}]})
    horas = {s["starts_at"].astimezone(TZ).hour for s in S.horarios_livres(conn, clinica.id, clinica.servico, dia, dia)}
    assert 8 in horas and 9 not in horas and 10 not in horas


def test_procedimentos(admin_c, conn, clinica, outra_clinica):
    novo = {"nome": "Canal", "duracao_min": 90, "ia_pode_marcar": False, "profissionais": [str(clinica.prof_a)]}
    r = admin_c.post(_url(clinica, "procedimentos"), json=novo)
    assert r.status_code == 201
    sid = r.json()["id"]
    assert admin_c.post(_url(clinica, "procedimentos"), json=novo).status_code == 422  # nome repetido
    outro = {**novo, "nome": "Implante", "profissionais": [str(outra_clinica.prof_a)]}
    assert admin_c.post(_url(clinica, "procedimentos"), json=outro).status_code == 422  # dentista de outra clínica
    lista = {p["nome"]: p for p in admin_c.get(_url(clinica, "procedimentos")).json()}
    assert lista["Canal"]["duracao_min"] == 90 and lista["Canal"]["profissionais"] == [str(clinica.prof_a)]
    assert admin_c.delete(_url(clinica, f"procedimentos/{sid}")).json()["resultado"] == "excluido"


def test_procedimento_usado_so_desliga(admin_c, conn, clinica):
    S.marcar(conn, clinica.id, telefone="+5511955554444", nome="Bia Lopes", professional_id=clinica.prof_a,
             service_id=clinica.servico, inicio=_proxima_segunda_10h(), ator="recepcao")
    assert admin_c.delete(_url(clinica, f"procedimentos/{clinica.servico}")).json()["resultado"] == "desligado"


def test_profissional_e_folga(admin_c, conn, clinica):
    r = admin_c.post(_url(clinica, "profissionais"), json={"nome": "Dra. Nova", "cor": "#2F80C9",
                                                           "procedimentos": [str(clinica.servico)]})
    pid = r.json()["id"]
    dia = _proxima_segunda_10h().date()
    livres = lambda: {s["professional_id"] for s in S.horarios_livres(conn, clinica.id, clinica.servico, dia, dia)}  # noqa: E731
    assert pid in {str(x) for x in livres()}
    f = admin_c.post(_url(clinica, f"profissionais/{pid}/folgas"),
                     json={"inicio": f"{dia}T00:00:00-03:00", "fim": f"{dia}T23:59:00-03:00", "motivo": "Férias"})
    assert f.status_code == 201
    assert pid not in {str(x) for x in livres()}
    admin_c.put(_url(clinica, f"profissionais/{clinica.prof_b}"), json={"nome": "Dr. B", "ativo": False, "procedimentos": []})
    assert clinica.prof_b not in livres()
    assert admin_c.post(_url(clinica, "profissionais"), json={"nome": "X", "cor": "vermelho"}).status_code == 422


def test_assistente_muda_regras_da_agenda(admin_c, conn, clinica):
    corpo = {"nome_assistente": "Luna", "tratamento": "senhor(a)", "mostrar_precos": True, "antecedencia_min_horas": 24,
             "horizonte_dias": 30, "aviso_cancelamento_horas": 12, "limite_consultas_futuras": 3, "lembrete_hora": "10:00"}
    assert admin_c.put(_url(clinica, "assistente"), json=corpo).status_code == 200
    c = S.carregar_clinica(conn, clinica.id)
    assert c["regras"].antecedencia_min_horas == 24 and c["regras"].lembrete_hora == "10:00"
    assert c["settings"]["nome_assistente"] == "Luna"
    assert admin_c.put(_url(clinica, "assistente"), json={**corpo, "limite_consultas_futuras": 0}).status_code == 422


def test_admin_nao_desativa_a_si_mesmo(cliente, conn, clinica):  # noqa: F811
    uid = _usuario(conn, clinic_id=clinica.id, papel="clinic_admin")
    c = _como(cliente, uid)
    r = c.patch(_url(clinica, f"usuarios/{uid}"), json={"ativo": False})
    assert r.status_code == 422
    outro = _usuario(conn, clinic_id=clinica.id, papel="reception")
    assert c.patch(_url(clinica, f"usuarios/{outro}"), json={"ativo": False}).status_code == 200
    assert _como(cliente, _usuario(conn, clinic_id=clinica.id)).get(_url(clinica, "usuarios")).status_code == 403
