"""Ferramentas da Ísis SEM chamar a IA: as travas de segurança estão no código (RN-AG-11, RN-AG-06, RN-MT-05)."""

import json

from app.agent.ferramentas import Sessao, criar_ferramentas
from app.agent.isis import AVISO_EQUIPE, AVISO_FECHADA, com_aviso_de_transferencia
from app.agenda import servico as S
from tests.conftest import AGORA, as_

TEL = "+5511977776666"


def _sessao(conn, clinica, tel=TEL, nome="Paciente Ísis"):
    c = S.carregar_clinica(conn, clinica.id)
    p = S.obter_ou_criar_paciente(conn, clinica.id, tel, nome, "web")
    conv = conn.execute(
        "insert into conversations (clinic_id, patient_id, channel) values (%s, %s, 'web') returning id, channel, status",
        (clinica.id, p["id"]),
    ).fetchone()
    s = Sessao(conn=conn, clinica=c, paciente=p, conversa={"id": conv[0], "channel": conv[1], "status": conv[2]}, agora=AGORA)
    return s, {f.__name__: f for f in criar_ferramentas(s)}


def _paciente_responde(conn, s):
    """Simula a resposta do paciente DEPOIS do resumo (relógio real + 1s, pois no teste tudo é uma transação só)."""
    conn.execute(
        """insert into messages (clinic_id, conversation_id, direction, author, content, created_at)
           values (%s, %s, 'in', 'paciente', 'sim', clock_timestamp() + interval '1 second')""",
        (s.cid, s.conversa["id"]),
    )


def _consultas(conn, clinica):
    return conn.execute("select count(*) from appointments where clinic_id = %s and status <> 'cancelada'", (clinica.id,)).fetchone()[0]


def test_preparar_nao_grava_nada(conn, clinica):
    s, f = _sessao(conn, clinica)
    r = json.loads(f["preparar_agendamento"]("Limpeza", "2026-11-23T09:00", "Dra. A"))
    assert r["ok"] and r["token"] and "segunda-feira, 23/11 às 09:00" in r["resumo"]
    assert _consultas(conn, clinica) == 0


def test_confirmar_na_mesma_vez_e_bloqueado(conn, clinica):
    s, f = _sessao(conn, clinica)
    token = json.loads(f["preparar_agendamento"]("Limpeza", "2026-11-23T09:00", "Dra. A"))["token"]
    r = json.loads(f["confirmar_acao"](token))
    assert not r["ok"] and "resposta do paciente" in r["mensagem"]
    assert _consultas(conn, clinica) == 0


def test_confirmar_depois_do_sim_marca_uma_vez(conn, clinica):
    s, f = _sessao(conn, clinica)
    token = json.loads(f["preparar_agendamento"]("limpeza", "2026-11-23T09:00", "a"))["token"]
    _paciente_responde(conn, s)
    assert json.loads(f["confirmar_acao"](token))["ok"]
    assert _consultas(conn, clinica) == 1
    assert json.loads(f["confirmar_acao"](token))["erro"] == "STATUS_INVALIDO"  # token não é reaproveitável
    assert _consultas(conn, clinica) == 1


def test_token_de_outro_paciente_nao_funciona(conn, clinica):
    s1, f1 = _sessao(conn, clinica)
    token = json.loads(f1["preparar_agendamento"]("Limpeza", "2026-11-23T09:00", "Dra. A"))["token"]
    s2, f2 = _sessao(conn, clinica, tel="+5511955554444", nome="Outra Pessoa")
    _paciente_responde(conn, s2)
    assert not json.loads(f2["confirmar_acao"](token))["ok"]
    assert _consultas(conn, clinica) == 0


def test_isis_nao_cancela_consulta_de_outro_telefone(conn, clinica):
    outra = S.marcar(conn, clinica.id, telefone="11 91212-3434", nome="Dona Mãe", professional_id=clinica.prof_a,
                     service_id=clinica.servico, inicio=as_(23, 9), ator="recepcao", agora=AGORA)
    s, f = _sessao(conn, clinica)
    r = json.loads(f["preparar_cancelamento"](str(outra["id"])))
    assert r["erro"] == "NAO_E_SUA"


def test_minhas_consultas_so_mostra_as_do_proprio_telefone(conn, clinica):
    S.marcar(conn, clinica.id, telefone="11 91212-3434", nome="Dona Mãe", professional_id=clinica.prof_a,
             service_id=clinica.servico, inicio=as_(23, 9), ator="recepcao", agora=AGORA)
    s, f = _sessao(conn, clinica)
    assert json.loads(f["minhas_consultas"]())["consultas"] == []


def test_horarios_livres_formato_e_limite(conn, clinica):
    s, f = _sessao(conn, clinica)
    r = json.loads(f["horarios_livres"]("Limpeza", "2026-11-23", "2026-11-27", turno="tarde"))
    assert r["ok"] and 0 < len(r["horarios"]) <= 8
    assert all(h["inicio"] >= "2026-11-23T13:00" and h["inicio"][11:13] >= "13" for h in r["horarios"])


def test_procedimento_so_da_recepcao(conn, clinica):
    s, f = _sessao(conn, clinica)
    r = json.loads(f["preparar_agendamento"]("Urgência", "2026-11-23T09:00", "Dra. A"))
    assert r["erro"] == "SO_HUMANO"


def test_chamar_humano_pausa_a_conversa(conn, clinica):
    s, f = _sessao(conn, clinica)
    f["chamar_humano"]("urgência")
    assert conn.execute("select status from conversations where id = %s", (s.conversa["id"],)).fetchone()[0] == "humano"


def test_transferencia_sempre_avisa_o_paciente(conn, clinica):  # D27
    s, f = _sessao(conn, clinica)
    assert com_aviso_de_transferencia("Oi!", s.chamadas, aberta=True) == "Oi!"  # sem transferência, sem aviso
    f["chamar_humano"]("dúvida sobre acompanhante")
    aberta = com_aviso_de_transferencia("Vou verificar.", s.chamadas, aberta=True)
    assert AVISO_EQUIPE in aberta and AVISO_FECHADA.strip() not in aberta
    assert AVISO_FECHADA.strip() in com_aviso_de_transferencia("Vou verificar.", s.chamadas, aberta=False)


def test_remarcar_em_dois_passos(conn, clinica):
    s, f = _sessao(conn, clinica)
    c = S.marcar(conn, clinica.id, telefone=TEL, nome="Paciente Ísis", professional_id=clinica.prof_a,
                 service_id=clinica.servico, inicio=as_(23, 9), ator="recepcao", agora=AGORA)
    r = json.loads(f["preparar_remarcacao"](str(c["id"]), "2026-11-24T14:00"))
    assert r["ok"] and S.detalhar(conn, clinica.id, c["id"])["status"] == "agendada"  # nada mudou ainda
    _paciente_responde(conn, s)
    assert json.loads(f["confirmar_acao"](r["token"]))["ok"]
    assert S.detalhar(conn, clinica.id, c["id"])["status"] == "cancelada"


class _IAQueChamaEquipeEFicaCalada:
    """Simula o achado da Etapa 8: o modelo chama chamar_humano e não escreve nada."""

    def __init__(self, tools, **_):
        self.tools = {f.__name__: f for f in tools}

    def run(self, _entrada):
        self.tools["chamar_humano"]("pediu atendente")
        return type("R", (), {"content": ""})()


def test_chamou_equipe_sem_texto_nao_pede_para_repetir(conn, clinica, monkeypatch):
    from app.agent import isis

    monkeypatch.setattr(isis, "Agent", _IAQueChamaEquipeEFicaCalada)
    s, _ = _sessao(conn, clinica)
    c = S.carregar_clinica(conn, clinica.id)
    saida = isis.responder(conn, c, s.paciente, s.conversa, "Quero falar com uma pessoa", AGORA)
    assert saida.startswith(isis.TEXTO_TRANSFERENCIA) and isis.AVISO_EQUIPE in saida
    assert isis.MSG_FALHA not in saida
    assert conn.execute("select status from conversations where id = %s", (s.conversa["id"],)).fetchone()[0] == "humano"
