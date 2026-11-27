"""Etapa 34 — RN-AG-19 (D129): marcada para menos de 24 h já entra confirmada, sem lembrete.

"Agora" dos testes: sexta 20/11/2026 10:00 (conftest). Clínica de teste abre seg–sex, 08h–18h.
"""

from psycopg.types.json import Jsonb

from app.agenda import servico as S
from tests.conftest import AGORA, as_

TEL = "+5511977775555"


def _marcar(conn, clinica, inicio, ator="recepcao"):
    return S.marcar(conn, clinica.id, telefone=TEL, nome="Rita Moraes", professional_id=clinica.prof_a,
                    service_id=clinica.servico, inicio=inicio, ator=ator, agora=AGORA)


def _mensagens(conn, clinica, consulta_id):
    return conn.execute(
        "select kind, body from outbound_messages where clinic_id = %s and appointment_id = %s and status <> 'cancelada' "
        "order by created_at", (clinica.id, consulta_id)).fetchall()


def _etapa(conn, patient_id):
    return conn.execute("select crm_stage from patients where id = %s", (patient_id,)).fetchone()[0]


def test_menos_de_24h_ja_entra_confirmada_sem_lembrete(conn, clinica):
    c = _marcar(conn, clinica, as_(20, 16))  # sexta 10h → sexta 16h (6 h)
    assert c["status"] == "confirmada"
    msgs = _mensagens(conn, clinica, c["id"])
    assert [k for k, _ in msgs] == ["confirmacao"]  # só o comprovante; nenhum lembrete
    assert "Já está confirmada, não precisa confirmar" in msgs[0][1]
    assert "Lembrete por aqui" not in msgs[0][1]
    assert _etapa(conn, c["patient_id"]) == "confirmado"


def test_mais_de_24h_continua_a_confirmar_com_lembrete(conn, clinica):
    c = _marcar(conn, clinica, as_(24, 9))  # terça: lembrete na segunda
    assert c["status"] == "agendada"
    msgs = _mensagens(conn, clinica, c["id"])
    assert sorted(k for k, _ in msgs) == ["confirmacao", "lembrete"]
    assert "não precisa confirmar" not in dict(msgs)["confirmacao"]
    assert _etapa(conn, c["patient_id"]) == "agendado"


def test_conta_horas_e_nao_dias(conn, clinica):
    assert _marcar(conn, clinica, as_(23, 9))["status"] == "agendada"  # segunda 9h = 71 h depois


def test_vale_para_a_isis(conn, clinica):
    c = _marcar(conn, clinica, as_(20, 15), ator="isis")
    assert c["status"] == "confirmada"


def test_remarcar_para_menos_de_24h_fica_confirmada(conn, clinica):
    c = _marcar(conn, clinica, as_(24, 9))
    r = S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao",
                   novo_inicio=as_(20, 17), agora=AGORA)
    nova = r["consulta"]
    assert nova["status"] == "confirmada"
    msgs = _mensagens(conn, clinica, nova["id"])
    assert [k for k, _ in msgs] == ["remarcacao"]
    assert "não precisa confirmar" in msgs[0][1]
    assert _etapa(conn, nova["patient_id"]) == "confirmado"
    # o lembrete da data antiga foi cancelado (RN-MS-07)
    assert all(k != "lembrete" for k, _ in _mensagens(conn, clinica, c["id"]))


def test_remarcar_para_mais_de_24h_volta_a_confirmar(conn, clinica):
    c = _marcar(conn, clinica, as_(20, 16))
    nova = S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao",
                      novo_inicio=as_(25, 9), agora=AGORA)["consulta"]
    assert nova["status"] == "agendada"
    assert _etapa(conn, nova["patient_id"]) == "agendado"


def test_clinica_pode_desligar_ou_mudar_o_prazo(conn, clinica):
    conn.execute("update clinics set settings = coalesce(settings, '{}'::jsonb) || %s where id = %s",
                 (Jsonb({"confirmar_automatico_horas": 0}), clinica.id))
    assert _marcar(conn, clinica, as_(20, 16))["status"] == "agendada"

    conn.execute("update clinics set settings = settings || %s where id = %s",
                 (Jsonb({"confirmar_automatico_horas": 96}), clinica.id))
    c2 = S.marcar(conn, clinica.id, telefone="+5511977775556", nome="Davi Souza", professional_id=clinica.prof_a,
                  service_id=clinica.servico, inicio=as_(23, 9), agora=AGORA, ator="recepcao")
    assert c2["status"] == "confirmada"  # 71 h < 96 h
