"""Etapa 27 — remarcar arrastando na agenda, com ou sem aviso ao paciente (D108, D109)."""

from app.agenda import servico as S
from tests.conftest import AGORA, as_

TEL = "+5511955554444"


def _fila(conn, clinica, kind, appointment_id):
    return conn.execute(
        "select count(*) from outbound_messages where clinic_id = %s and appointment_id = %s and kind = %s and status = 'agendada'",
        (clinica.id, appointment_id, kind)).fetchone()[0]


def _consulta(conn, clinica):
    return S.marcar(conn, clinica.id, telefone=TEL, nome="Davi Lopes", professional_id=clinica.prof_a,
                    service_id=clinica.servico, inicio=as_(25, 9), ator="recepcao", agora=AGORA)


def test_sem_aviso_nao_manda_remarcacao_mas_mantem_lembrete(conn, clinica):
    c = _consulta(conn, clinica)
    assert _fila(conn, clinica, "lembrete", c["id"]) == 1
    r = S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao", novo_inicio=as_(26, 10),
                   professional_id=clinica.prof_b, agora=AGORA, avisar_paciente=False)
    nova = r["consulta"]
    assert nova["professional_id"] == clinica.prof_b
    assert _fila(conn, clinica, "remarcacao", nova["id"]) == 0
    assert _fila(conn, clinica, "lembrete", c["id"]) == 0 and _fila(conn, clinica, "lembrete", nova["id"]) == 1


def test_com_aviso_manda_remarcacao(conn, clinica):
    c = _consulta(conn, clinica)
    r = S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao", novo_inicio=as_(26, 10),
                   agora=AGORA)
    assert _fila(conn, clinica, "remarcacao", r["consulta"]["id"]) == 1
