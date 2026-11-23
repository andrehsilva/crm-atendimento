"""Etapa 26 — horário fixo ao abrir o tratamento e lembrete ligado/desligado (D105–D107, RN-TR-12/13)."""

from datetime import timedelta

import pytest

from app import horario_fixo as H
from app import segmentos
from app import tratamentos as T
from app.agenda import servico as S
from app.agenda.erros import AgendaError
from tests.conftest import AGORA, as_
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada

TEL = "+5511966665555"


def _paciente(conn, clinica):
    return S.obter_ou_criar_paciente(conn, clinica.id, TEL, "Lia Prado", "manual")


def _abrir(conn, clinica, avisos=True, sessoes=None, inicio=None):
    p = _paciente(conn, clinica)
    t = T.criar(conn, clinica.id, p["id"], service_id=clinica.servico, professional_id=clinica.prof_a,
                sessoes_previstas=None, intervalo_dias=7, orientacao=None, avisos_paciente=avisos)
    r = H.marcar_ao_abrir(conn, clinica.id, t["id"], inicio=inicio or as_(24, 9), sessoes=sessoes, agora=AGORA)
    return T.obter(conn, clinica.id, t["id"]), r


def _fila(conn, clinica, kind):
    return conn.execute(
        """select count(*) from outbound_messages o join patients p on p.id = o.patient_id
           where o.clinic_id = %s and p.phone = %s and o.kind = %s and o.status = 'agendada'""",
        (clinica.id, TEL, kind)).fetchone()[0]


def test_sem_fim_marca_a_janela_e_guarda_ate_onde_foi(conn, clinica):
    t, r = _abrir(conn, clinica)
    assert len(r["marcadas"]) == H.JANELA and r["falhas"] == []
    assert t["horario_fixo"] and t["marcadas"] == H.JANELA
    assert t["serie_ate"] == as_(24, 9) + timedelta(days=7 * (H.JANELA - 1))
    # todas na terça às 09:00, ligadas ao tratamento
    assert {(c["starts_at"].astimezone(as_(1, 0).tzinfo).weekday(), c["starts_at"].astimezone(as_(1, 0).tzinfo).hour)
            for c in r["marcadas"]} == {(1, 9)}
    assert _fila(conn, clinica, "confirmacao") == 1 and _fila(conn, clinica, "lembrete") == H.JANELA


def test_renovacao_acrescenta_so_o_que_falta_e_nao_recria_cancelada(conn, clinica):
    t, r = _abrir(conn, clinica)
    # paciente desmarca a 2ª sessão: ela não volta sozinha
    S.cancelar(conn, clinica.id, appointment_id=r["marcadas"][1]["id"], telefone=None, ator="recepcao", agora=AGORA)
    uma_semana = AGORA + timedelta(days=7)
    n = H.renovar_todos(conn, uma_semana, clinica.id)
    assert n == 1
    t2 = T.obter(conn, clinica.id, t["id"])
    assert t2["serie_ate"] == t["serie_ate"] + timedelta(days=7)
    cancelada = conn.execute("select status from appointments where id = %s", (r["marcadas"][1]["id"],)).fetchone()[0]
    assert cancelada == "cancelada"
    assert H.renovar_todos(conn, uma_semana, clinica.id) == 0  # janela cheia: nada a fazer


def test_aguardando_pausa_a_renovacao(conn, clinica):
    t, _ = _abrir(conn, clinica)
    T.aguardar(conn, clinica.id, t["id"], motivo_espera="outro", motivo_texto="viagem", previsao=None)
    assert H.renovar_todos(conn, AGORA + timedelta(days=14), clinica.id) == 0


def test_encerrar_cancela_as_futuras_sem_avisar(conn, clinica):
    t, _ = _abrir(conn, clinica)
    T.encerrar(conn, clinica.id, t["id"], status="interrompido", volta_em=None)
    assert H.cancelar_futuras(conn, clinica.id, t["id"], AGORA) == H.JANELA
    assert _fila(conn, clinica, "lembrete") == 0 and _fila(conn, clinica, "cancelamento") == 0
    assert H.renovar_todos(conn, AGORA + timedelta(days=14), clinica.id) == 0


def test_numero_fixo_de_sessoes(conn, clinica):
    t, r = _abrir(conn, clinica, sessoes=4)
    assert len(r["marcadas"]) == 4 and not t["horario_fixo"] and t["sessoes_previstas"] == 4


def test_nada_coube_da_erro(conn, clinica):
    with pytest.raises(AgendaError) as e:
        _abrir(conn, clinica, sessoes=2, inicio=as_(22, 9))  # domingos: clínica fechada
    assert e.value.codigo == "SERIE_VAZIA"


def test_avisos_desligados_nao_mandam_confirmacao_nem_lembrete(conn, clinica):
    t, _ = _abrir(conn, clinica, avisos=False)
    assert _fila(conn, clinica, "confirmacao") == 0 and _fila(conn, clinica, "lembrete") == 0
    H.renovar_todos(conn, AGORA + timedelta(days=7), clinica.id)
    assert _fila(conn, clinica, "lembrete") == 0
    # sessão avulsa marcada depois (Ísis/recepção) também fica sem aviso
    S.marcar(conn, clinica.id, telefone=TEL, nome=None, professional_id=clinica.prof_a, service_id=clinica.servico,
             inicio=as_(25, 14), ator="recepcao", agora=AGORA)
    assert _fila(conn, clinica, "confirmacao") == 0 and _fila(conn, clinica, "lembrete") == 0


def test_ligar_e_desligar_avisos_depois(conn, clinica):
    t, _ = _abrir(conn, clinica)
    assert _fila(conn, clinica, "lembrete") == H.JANELA
    T.editar(conn, clinica.id, t["id"], {"avisos_paciente": False})
    H.sincronizar_lembretes(conn, clinica.id, t["id"], AGORA)
    assert _fila(conn, clinica, "lembrete") == 0
    T.editar(conn, clinica.id, t["id"], {"avisos_paciente": True})
    H.sincronizar_lembretes(conn, clinica.id, t["id"], AGORA)
    assert _fila(conn, clinica, "lembrete") == H.JANELA


def test_desligar_horario_fixo_para_de_renovar(conn, clinica):
    t, _ = _abrir(conn, clinica)
    T.editar(conn, clinica.id, t["id"], {"horario_fixo": False})
    assert H.renovar_todos(conn, AGORA + timedelta(days=14), clinica.id) == 0
    with pytest.raises(AgendaError):
        T.editar(conn, clinica.id, t["id"], {"horario_fixo": True})


def test_padrao_por_tipo_de_clinica():
    assert segmentos.avisos_tratamento({"segmento": "psicanalise"}) is False
    assert segmentos.avisos_tratamento({"segmento": "odontologia"}) is True
    assert segmentos.avisos_tratamento({}) is True


def test_rota_abrir_com_horario_fixo(cliente, conn, clinica):  # noqa: F811
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    p = _paciente(conn, clinica)
    corpo = {"service_id": str(clinica.servico), "professional_id": str(clinica.prof_a), "avisos_paciente": False,
             "serie": {"inicio": "2099-03-03T09:00:00-03:00"}}
    r = rec.post(f"/api/clinics/{clinica.id}/patients/{p['id']}/tratamentos", json=corpo)
    # 2099 está fora do horizonte da agenda: nada coube → nada fica gravado
    assert r.status_code == 409 and r.json()["codigo"] == "SERIE_VAZIA"
    assert T.do_paciente(conn, clinica.id, p["id"]) == []
    sem_prof = {**corpo, "professional_id": None}
    assert rec.post(f"/api/clinics/{clinica.id}/patients/{p['id']}/tratamentos", json=sem_prof).status_code == 422
    lista = rec.get(f"/api/clinics/{clinica.id}/patients/{p['id']}/tratamentos").json()
    assert lista["avisos_padrao"] is True
