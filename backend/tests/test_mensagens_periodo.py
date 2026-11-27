"""Etapa 35 (D130): Mensagens por período e por cliente; resumo de campanhas e aniversários."""

from datetime import timedelta

from app.painel import historico
from tests.conftest import AGORA


def _paciente(conn, clinica, nome, tel):
    return conn.execute("insert into patients (clinic_id, name, phone) values (%s, %s, %s) returning id",
                        (clinica.id, nome, tel)).fetchone()[0]


def _campanha(conn, clinica, titulo):
    return conn.execute(
        """insert into campaigns (clinic_id, titulo, texto, publico, enviar_em) values (%s, %s, 'Oi', 'todos', %s)
           returning id""", (clinica.id, titulo, AGORA - timedelta(days=1))).fetchone()[0]


def _msg(conn, clinica, pid, kind, status, dias_atras, campanha=None):
    quando = AGORA - timedelta(days=dias_atras)
    enviada = quando if status in ("enviada", "entregue", "lida") else None
    return conn.execute(
        """insert into outbound_messages (clinic_id, patient_id, kind, body, status, scheduled_for, sent_at, campaign_id)
           values (%s, %s, %s, 'texto', %s, %s, %s, %s) returning id""",
        (clinica.id, pid, kind, status, quando, enviada, campanha)).fetchone()[0]


def test_padrao_mostra_a_ultima_semana_e_a_fila(conn, clinica):
    ana = _paciente(conn, clinica, "Ana Lima", "+5511970000001")
    recente = _msg(conn, clinica, ana, "lembrete", "entregue", 2)
    antiga = _msg(conn, clinica, ana, "lembrete", "enviada", 20)
    fila = _msg(conn, clinica, ana, "lembrete", "agendada", -3)  # vai sair daqui a 3 dias
    ids = {m["id"] for m in historico.listar(conn, clinica.id, agora=AGORA)}
    assert {recente, fila} <= ids and antiga not in ids
    ids30 = {m["id"] for m in historico.listar(conn, clinica.id, agora=AGORA, dias=30)}
    assert antiga in ids30


def test_periodo_invalido_volta_para_7_dias(conn, clinica):
    ana = _paciente(conn, clinica, "Ana Lima", "+5511970000001")
    antiga = _msg(conn, clinica, ana, "lembrete", "enviada", 20)
    assert antiga not in {m["id"] for m in historico.listar(conn, clinica.id, agora=AGORA, dias=9999)}


def test_cliente_mostra_tudo_dele_de_qualquer_data(conn, clinica):
    ana = _paciente(conn, clinica, "Ana Lima", "+5511970000001")
    bia = _paciente(conn, clinica, "Bia Costa", "+5511970000002")
    velha = _msg(conn, clinica, ana, "aniversario", "lida", 200)
    _msg(conn, clinica, bia, "lembrete", "enviada", 1)
    lista = historico.listar(conn, clinica.id, agora=AGORA, patient_id=ana)
    assert {m["id"] for m in lista} == {velha}
    assert lista[0]["patient_id"] == ana


def test_resumo_por_campanha_e_aniversarios(conn, clinica):
    pids = [_paciente(conn, clinica, f"Pessoa {i} Teste", f"+55119700001{i:02d}") for i in range(5)]
    natal = _campanha(conn, clinica, "Natal")
    for pid, st in zip(pids, ["entregue", "lida", "enviada", "falhou", "agendada"]):
        _msg(conn, clinica, pid, "campanha", st, 1 if st != "agendada" else -1, natal)
    _msg(conn, clinica, pids[0], "aniversario", "falhou", 3)
    _msg(conn, clinica, pids[1], "aniversario", "entregue", 4)
    _msg(conn, clinica, pids[2], "aniversario", "entregue", 40)  # fora da semana
    _msg(conn, clinica, pids[3], "lembrete", "falhou", 1)  # não é disparo em massa

    r = {x["titulo"]: x for x in historico.resumo(conn, clinica.id, agora=AGORA)}
    assert set(r) == {"Natal", "Aniversários"}
    n = r["Natal"]
    assert (n["total"], n["enviadas"], n["entregues"], n["falharam"], n["na_fila"]) == (5, 3, 2, 1, 1)
    a = r["Aniversários"]
    assert (a["total"], a["enviadas"], a["falharam"]) == (2, 1, 1)
