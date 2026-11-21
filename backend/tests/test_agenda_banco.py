"""Regras RN-AG-* e RN-MT-* contra o banco real (transação desfeita no fim de cada teste)."""

from datetime import date

import pytest

from app.agenda import servico as S
from app.agenda.erros import AgendaError
from tests.conftest import AGORA, as_

TEL = "(11) 98888-7777"


def marcar(conn, c, inicio, tel=TEL, nome="Paciente Teste", prof=None, servico=None, ator="recepcao"):
    return S.marcar(conn, c.id, telefone=tel, nome=nome, professional_id=prof or c.prof_a,
                    service_id=servico or c.servico, inicio=inicio, ator=ator, agora=AGORA)


def codigo(exc_info) -> str:
    return exc_info.value.codigo


# --- marcar -------------------------------------------------------------------
def test_marca_e_grava_historico(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    assert c["status"] == "agendada" and c["paciente"] == "Paciente Teste" and c["telefone"] == "+5511988887777"
    eventos = conn.execute("select action from appointment_events where appointment_id = %s", (c["id"],)).fetchall()
    assert eventos == [("marcada",)]


def test_rn_ag_02_mesmo_horario_mesmo_dentista_recusa(conn, clinica):
    marcar(conn, clinica, as_(23, 9))
    with pytest.raises(AgendaError) as e:
        marcar(conn, clinica, as_(23, 9, 30), tel="11 97777-6666", nome="Outro")
    assert codigo(e) == "HORARIO_OCUPADO"


def test_rn_ag_02_mesmo_horario_outro_dentista_pode(conn, clinica):
    marcar(conn, clinica, as_(23, 9))
    assert marcar(conn, clinica, as_(23, 9), tel="11 97777-6666", nome="Outro", prof=clinica.prof_b)


def test_rn_ag_01_almoco_recusa(conn, clinica):
    with pytest.raises(AgendaError) as e:
        marcar(conn, clinica, as_(23, 11, 30))  # 11:30-12:30 invade o almoço
    assert codigo(e) == "FORA_DO_HORARIO"


def test_rn_ag_01_fim_de_semana_recusa(conn, clinica):
    with pytest.raises(AgendaError) as e:
        marcar(conn, clinica, as_(22, 9))  # domingo
    assert codigo(e) == "FORA_DO_HORARIO"


def test_rn_ag_01_bloqueio_recusa(conn, clinica):
    conn.execute("insert into schedule_blocks (clinic_id, starts_at, ends_at, reason) values (%s,%s,%s,'Feriado')",
                 (clinica.id, as_(23, 0), as_(24, 0)))
    with pytest.raises(AgendaError) as e:
        marcar(conn, clinica, as_(23, 9))
    assert codigo(e) == "FORA_DO_HORARIO"


def test_rn_ag_04_antecedencia_minima(conn, clinica):
    with pytest.raises(AgendaError) as e:
        marcar(conn, clinica, as_(20, 11))  # agora = 20/11 10:00; mínimo 2h
    assert codigo(e) == "ANTECEDENCIA"


def test_rn_ag_05_horizonte(conn, clinica):
    with pytest.raises(AgendaError) as e:
        S.marcar(conn, clinica.id, telefone=TEL, nome="X", professional_id=clinica.prof_a, service_id=clinica.servico,
                 inicio=as_(23, 9).replace(year=2027, month=2, day=1), ator="recepcao", agora=AGORA)
    assert codigo(e) == "HORIZONTE"


def test_rn_at_05_nome_obrigatorio_para_paciente_novo(conn, clinica):
    with pytest.raises(AgendaError) as e:
        marcar(conn, clinica, as_(23, 9), nome=None)
    assert codigo(e) == "NOME_OBRIGATORIO"
    assert S.buscar_paciente(conn, clinica.id, TEL) is None  # nada ficou gravado


def test_rn_ag_08_limite_de_consultas_futuras(conn, clinica):
    marcar(conn, clinica, as_(23, 9))
    marcar(conn, clinica, as_(24, 9))
    with pytest.raises(AgendaError) as e:
        marcar(conn, clinica, as_(25, 9))
    assert codigo(e) == "LIMITE_CONSULTAS"


def test_rn_ag_14_isis_nao_marca_procedimento_so_humano(conn, clinica):
    with pytest.raises(AgendaError) as e:
        marcar(conn, clinica, as_(23, 9), servico=clinica.urgencia, ator="isis")
    assert codigo(e) == "SO_HUMANO"
    assert marcar(conn, clinica, as_(23, 9), servico=clinica.urgencia, ator="recepcao")


# --- horários livres ----------------------------------------------------------
def test_horarios_livres_respeita_almoco_ocupacao_e_antecedencia(conn, clinica):
    marcar(conn, clinica, as_(23, 9))
    slots = S.horarios_livres(conn, clinica.id, clinica.servico, date(2026, 11, 20), date(2026, 11, 23),
                              professional_id=clinica.prof_a, agora=AGORA, limite=500)
    inicios = {s["starts_at"] for s in slots}
    assert as_(20, 11) not in inicios  # antes de agora + 2h
    assert as_(20, 12, 0) not in inicios and as_(20, 13) in inicios  # almoço
    assert as_(23, 9) not in inicios and as_(23, 8, 30) not in inicios and as_(23, 10) in inicios  # ocupado
    assert not any(s["starts_at"].weekday() >= 5 for s in slots)  # fim de semana fechado


def test_horarios_saem_no_fuso_da_clinica_e_em_ordem(conn, clinica):
    conn.execute("set time zone 'UTC'")  # simula o padrão do Supabase
    marcar(conn, clinica, as_(23, 9))
    slots = S.horarios_livres(conn, clinica.id, clinica.servico, date(2026, 11, 23), date(2026, 11, 23),
                              professional_id=clinica.prof_a, agora=AGORA, limite=500)
    inicios = [s["starts_at"] for s in slots]
    assert inicios == sorted(inicios)
    assert {i.utcoffset().total_seconds() for i in inicios} == {-3 * 3600}
    assert S.listar(conn, clinica.id, as_(23, 0), as_(24, 0))[0]["starts_at"].isoformat() == "2026-11-23T09:00:00-03:00"


# --- remarcar / cancelar (RN-AG-06, 07, 09) -------------------------------------
def test_rn_ag_06_paciente_nao_cancela_consulta_de_outro_telefone(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    with pytest.raises(AgendaError) as e:
        S.cancelar(conn, clinica.id, appointment_id=c["id"], telefone="11 91111-2222", ator="paciente", agora=AGORA)
    assert codigo(e) == "NAO_E_SUA"


def test_paciente_cancela_com_telefone_em_outro_formato(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    r = S.cancelar(conn, clinica.id, appointment_id=c["id"], telefone="+55 11 98888-7777", ator="paciente", agora=AGORA)
    assert r["consulta"]["status"] == "cancelada" and r["aviso_politica"] is False


def test_rn_ag_07_cancelar_em_cima_da_hora_avisa_politica(conn, clinica):
    c = marcar(conn, clinica, as_(20, 15))  # hoje 15h, agora 10h
    r = S.cancelar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao", agora=AGORA)
    assert r["aviso_politica"] is True


def test_rn_ag_09_remarcar_troca_em_transacao(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    r = S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=TEL, ator="paciente", novo_inicio=as_(24, 14), agora=AGORA)
    assert r["consulta"]["starts_at"] == as_(24, 14) and r["consulta"]["rescheduled_from_id"] == c["id"]
    assert S.detalhar(conn, clinica.id, c["id"])["status"] == "cancelada"


def test_rn_ag_09_remarcacao_que_falha_mantem_a_antiga(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    with pytest.raises(AgendaError):
        S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=TEL, ator="paciente", novo_inicio=as_(23, 12), agora=AGORA)
    assert S.detalhar(conn, clinica.id, c["id"])["status"] == "agendada"


def test_remarcar_para_horario_vizinho_do_mesmo_dentista(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    r = S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao", novo_inicio=as_(23, 9, 30), agora=AGORA)
    assert r["consulta"]["starts_at"] == as_(23, 9, 30)


def test_remarcar_com_limite_cheio_funciona(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    marcar(conn, clinica, as_(24, 9))
    assert S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao", novo_inicio=as_(25, 9), agora=AGORA)


# --- status e dentista de referência (RN-AG-12, RN-AG-15) ----------------------
def test_rn_ag_15_realizada_define_dentista_de_referencia(conn, clinica, monkeypatch):
    c = marcar(conn, clinica, as_(23, 9), prof=clinica.prof_b)
    monkeypatch.setattr(S.relogio, "agora", lambda: as_(23, 11))  # já é o dia do atendimento
    S.mudar_status(conn, clinica.id, appointment_id=c["id"], novo="realizada", ator="recepcao")
    assert S.buscar_paciente(conn, clinica.id, TEL)["preferred_professional_id"] == clinica.prof_b
    slots = S.horarios_livres(conn, clinica.id, clinica.servico, date(2026, 11, 24), date(2026, 11, 24), telefone=TEL, agora=AGORA)
    assert all(s["preferido"] == (s["professional_id"] == clinica.prof_b) for s in slots)


def test_rn_ag_12_transicoes_invalidas(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    S.cancelar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao", agora=AGORA)
    with pytest.raises(AgendaError) as e:
        S.mudar_status(conn, clinica.id, appointment_id=c["id"], novo="confirmada", ator="recepcao")
    assert codigo(e) == "STATUS_INVALIDO"


def test_paciente_nao_marca_presenca(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    with pytest.raises(AgendaError) as e:
        S.mudar_status(conn, clinica.id, appointment_id=c["id"], novo="realizada", ator="paciente", telefone=TEL)
    assert codigo(e) == "SO_HUMANO"


# --- multi-tenant (RN-MT-02, RN-MT-03 / cenário C16) ---------------------------
def test_mesmo_telefone_em_duas_clinicas_sao_pacientes_diferentes(conn, clinica, outra_clinica):
    a = marcar(conn, clinica, as_(23, 9))
    b = marcar(conn, outra_clinica, as_(23, 9))
    assert a["patient_id"] != b["patient_id"]
    assert [x["id"] for x in S.consultas_do_paciente(conn, clinica.id, TEL, agora=AGORA)] == [a["id"]]


def test_clinica_nao_enxerga_consulta_da_outra(conn, clinica, outra_clinica):
    b = marcar(conn, outra_clinica, as_(23, 9))
    with pytest.raises(AgendaError) as e:
        S.cancelar(conn, clinica.id, appointment_id=b["id"], telefone=None, ator="recepcao", agora=AGORA)
    assert codigo(e) == "CONSULTA_NAO_ENCONTRADA"
    assert S.listar(conn, clinica.id, as_(23, 0), as_(24, 0)) == []


def test_nao_marca_com_dentista_de_outra_clinica(conn, clinica, outra_clinica):
    with pytest.raises(AgendaError) as e:
        marcar(conn, clinica, as_(23, 9), prof=outra_clinica.prof_a)
    assert codigo(e) == "PROFISSIONAL_NAO_FAZ"


# --- CRM e fila de mensagens (RN-PN-09, RN-MS-01, D18) ----------------------------
def _etapa(conn, clinica):
    return conn.execute("select crm_stage, last_event from patients where clinic_id = %s and phone = '+5511988887777'",
                        (clinica.id,)).fetchone()


def _fila(conn, clinica):
    return [r[0] for r in conn.execute(
        "select kind from outbound_messages where clinic_id = %s order by created_at, kind", (clinica.id,))]


def test_marcar_move_card_e_enfileira_confirmacao(conn, clinica):
    marcar(conn, clinica, as_(23, 9))
    assert _etapa(conn, clinica) == ("agendado", "consulta_agendada")
    assert _fila(conn, clinica) == ["confirmacao"]


def test_confirmar_move_para_confirmado(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    S.mudar_status(conn, clinica.id, appointment_id=c["id"], novo="confirmada", ator="recepcao")
    assert _etapa(conn, clinica) == ("confirmado", "consulta_confirmada")


def test_cancelar_unica_consulta_vai_para_cancelados(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    S.cancelar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao", agora=AGORA)
    assert _etapa(conn, clinica) == ("cancelado", "consulta_cancelada")
    assert "cancelamento" in _fila(conn, clinica)


def test_cancelar_com_outra_consulta_continua_agendado(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    marcar(conn, clinica, as_(24, 9))
    S.cancelar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao", agora=AGORA)
    assert _etapa(conn, clinica)[0] == "agendado"


def test_remarcar_enfileira_uma_mensagem_de_remarcacao(conn, clinica):
    c = marcar(conn, clinica, as_(23, 9))
    S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao", novo_inicio=as_(24, 14), agora=AGORA)
    assert _fila(conn, clinica).count("remarcacao") == 1
    assert _fila(conn, clinica).count("confirmacao") == 1  # só a da marcação original
    texto = conn.execute("select body from outbound_messages where kind = 'remarcacao' and clinic_id = %s", (clinica.id,)).fetchone()[0]
    assert "segunda-feira, 23/11 às 09:00" in texto and "terça-feira, 24/11 às 14:00" in texto


def test_presenca_e_falta_so_a_partir_do_dia_do_atendimento(conn, clinica, monkeypatch):
    c = marcar(conn, clinica, as_(24, 9))
    monkeypatch.setattr(S.relogio, "agora", lambda: as_(23, 18))  # véspera
    for novo in ("realizada", "faltou"):
        with pytest.raises(AgendaError) as e:
            S.mudar_status(conn, clinica.id, appointment_id=c["id"], novo=novo, ator="recepcao")
        assert e.value.codigo == "STATUS_INVALIDO"
    S.mudar_status(conn, clinica.id, appointment_id=c["id"], novo="confirmada", ator="recepcao")  # confirmar continua livre
    monkeypatch.setattr(S.relogio, "agora", lambda: as_(24, 8))  # no dia, mesmo antes do horário
    assert S.mudar_status(conn, clinica.id, appointment_id=c["id"], novo="realizada", ator="recepcao")["status"] == "realizada"

