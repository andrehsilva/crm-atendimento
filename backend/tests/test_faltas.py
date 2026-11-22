"""RN-AG-16 (D91): com 2 faltas em 45 dias, a assistente não marca e passa para a recepção."""

import json

import pytest

from app.agenda import servico as S
from app.agenda.erros import AgendaError
from app.agent import contexto
from tests.conftest import AGORA, as_
from tests.test_ferramentas_isis import TEL, _sessao


def _falta(conn, clinica, dia, mes=11, tel=TEL):
    p = S.obter_ou_criar_paciente(conn, clinica.id, tel, "Paciente Ísis", "web")
    conn.execute(
        """insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at, status)
           values (%s, %s, %s, %s, %s, %s, 'faltou')""",
        (clinica.id, p["id"], clinica.prof_a, clinica.servico,
         as_(dia, 9).replace(month=mes), as_(dia, 10).replace(month=mes)))


def _marcar(conn, clinica, inicio, ator="isis"):
    return S.marcar(conn, clinica.id, telefone=TEL, nome="Paciente Ísis", professional_id=clinica.prof_a,
                    service_id=clinica.servico, inicio=inicio, ator=ator, agora=AGORA)


def test_duas_faltas_em_45_dias_so_a_recepcao_marca(conn, clinica):
    _falta(conn, clinica, 3)
    _marcar(conn, clinica, as_(24, 9))  # 1 falta: segue normal
    _falta(conn, clinica, 10)
    with pytest.raises(AgendaError) as e:
        _marcar(conn, clinica, as_(25, 9))
    assert e.value.codigo == "FALTAS_REPETIDAS" and "faltou 2 vezes nos últimos 45 dias" in e.value.mensagem
    assert _marcar(conn, clinica, as_(25, 9), ator="recepcao")  # a recepção decide


def test_falta_antiga_nao_conta_e_zero_desliga(conn, clinica):
    _falta(conn, clinica, 1, mes=9)  # 01/09: fora dos 45 dias antes de 20/11
    _falta(conn, clinica, 10)
    assert _marcar(conn, clinica, as_(24, 9))
    _falta(conn, clinica, 12)
    conn.execute("""update clinics set settings = settings || '{"faltas_limite": 0}' where id = %s""", (clinica.id,))
    assert _marcar(conn, clinica, as_(25, 9))  # 0 = regra desligada


def test_remarcar_o_que_ja_existe_continua_valendo(conn, clinica):
    c = _marcar(conn, clinica, as_(24, 9))
    _falta(conn, clinica, 3)
    _falta(conn, clinica, 10)
    r = S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=TEL, ator="isis", novo_inicio=as_(26, 9), agora=AGORA)
    assert r["consulta"]["status"] == "agendada"


def test_assistente_passa_para_a_recepcao_no_codigo(conn, clinica):
    _falta(conn, clinica, 3)
    _falta(conn, clinica, 10)
    s, f = _sessao(conn, clinica)
    assert "Faltou 2 vezes nos últimos 45 dias" in contexto.instrucoes(conn, s.clinica, s.paciente, AGORA)
    r = json.loads(f["horarios_livres"]("Limpeza", "2026-11-24"))
    assert r["erro"] == "FALTAS_REPETIDAS"
    assert s.conversa["status"] == "humano" and any(c["ferramenta"] == "chamar_humano" for c in s.chamadas)
    assert conn.execute("select status from conversations where id = %s", (s.conversa["id"],)).fetchone()[0] == "humano"
