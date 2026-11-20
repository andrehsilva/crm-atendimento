"""Etapa 6 — lembretes, envio da fila e aniversário. WAHA simulado; nada sai de verdade.

"Agora" dos testes: sexta 20/11/2026 10:00 (conftest). Clínica de teste abre seg–sex.
"""

from datetime import date, datetime, time, timedelta

import pytest

from app.agenda import servico as S
from app.canais.waha import WahaErro
from app.config import Settings
from app.mensagens import envio, lembretes
from app.mensagens import regras as R
from app.painel import chat
from tests.conftest import AGORA, TZ, as_

TEL = "+5511977771234"
SESSAO = "sessao-lembretes"


# ---------------------------------------------------------------------------
# Regras puras
# ---------------------------------------------------------------------------
SEG_A_SEX = {0, 1, 2, 3, 4}


def test_lembrete_de_segunda_vai_na_sexta():
    assert R.dia_do_lembrete(date(2026, 11, 23), SEG_A_SEX, set()) == date(2026, 11, 20)


def test_lembrete_respeita_sabado_aberto_e_feriado():
    assert R.dia_do_lembrete(date(2026, 11, 23), SEG_A_SEX | {5}, set()) == date(2026, 11, 21)
    assert R.dia_do_lembrete(date(2026, 11, 23), SEG_A_SEX, {date(2026, 11, 20)}) == date(2026, 11, 19)


@pytest.mark.parametrize(("h", "esperado"), [(time(22), True), (time(7, 59), True), (time(8), False), (time(20, 59), False)])
def test_silencio_noturno(h, esperado):
    assert R.em_silencio(h, time(21), time(8)) is esperado


def test_aniversario_29_de_fevereiro():
    assert R.faz_aniversario(date(1992, 2, 29), date(2027, 2, 28))      # ano comum: comemora dia 28
    assert not R.faz_aniversario(date(1992, 2, 29), date(2028, 2, 28))  # ano bissexto: espera o 29
    assert R.faz_aniversario(date(1990, 11, 20), date(2026, 11, 20))


@pytest.mark.parametrize(("texto", "esperado"), [
    ("1", "confirmar"), (" 1 ", "confirmar"), ("Confirmo!", "confirmar"), ("2", "remarcar"),
    ("3", "cancelar"), ("11", None), ("sim", None), ("1 e 2", None),
])
def test_resposta_ao_lembrete(texto, esperado):
    assert R.resposta_ao_lembrete(texto) == esperado


def test_pedido_para_sair():
    assert R.pediu_para_sair("Parar") and R.pediu_para_sair("SAIR.")
    assert not R.pediu_para_sair("quero sair mais cedo")


# ---------------------------------------------------------------------------
# Criação do lembrete ao marcar / remarcar / cancelar
# ---------------------------------------------------------------------------
def _marcar(conn, clinica, inicio, tel=TEL):
    return S.marcar(conn, clinica.id, telefone=tel, nome="Carla Dias", professional_id=clinica.prof_a,
                    service_id=clinica.servico, inicio=inicio, ator="recepcao", agora=AGORA)


def _lembretes(conn, clinica):
    return conn.execute(
        "select appointment_id, scheduled_for, status from outbound_messages where clinic_id = %s and kind = 'lembrete' order by created_at",
        (clinica.id,),
    ).fetchall()


def test_marcar_agenda_lembrete_no_dia_util_anterior(conn, clinica):
    c = _marcar(conn, clinica, as_(24, 9))  # terça → lembrete segunda 09:00
    (ap, quando, status), = _lembretes(conn, clinica)
    assert ap == c["id"] and status == "agendada" and quando.astimezone(TZ) == as_(23, 9)


def test_sem_lembrete_quando_o_horario_ja_passou(conn, clinica):
    _marcar(conn, clinica, as_(23, 9))  # segunda → lembrete seria sexta 20/11 09:00, mas já são 10:00
    assert _lembretes(conn, clinica) == []


def test_remarcar_troca_o_lembrete(conn, clinica):
    c = _marcar(conn, clinica, as_(24, 9))
    nova = S.remarcar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao",
                      novo_inicio=as_(26, 14), agora=AGORA)["consulta"]
    ls = _lembretes(conn, clinica)
    assert (c["id"], "cancelada") in [(x[0], x[2]) for x in ls]
    assert [x for x in ls if x[2] == "agendada"][0][:2] == (nova["id"], as_(25, 9))


def test_cancelar_cancela_o_lembrete(conn, clinica):
    c = _marcar(conn, clinica, as_(24, 9))
    S.cancelar(conn, clinica.id, appointment_id=c["id"], telefone=None, ator="recepcao", agora=AGORA)
    assert [x[2] for x in _lembretes(conn, clinica)] == ["cancelada"]


# ---------------------------------------------------------------------------
# Envio da fila
# ---------------------------------------------------------------------------
class WahaFalso:
    def __init__(self, falhar=False):
        self.enviadas, self.falhar = [], falhar

    def enviar_texto(self, sessao, chat_id, texto, simular_digitacao=None):
        if self.falhar:
            raise WahaErro("WAHA fora do ar")
        self.enviadas.append((chat_id, texto))
        return f"true_{chat_id}_L{len(self.enviadas)}"


class SemCommit:
    def __init__(self, conn):
        self._c = conn

    def commit(self):
        pass

    def rollback(self):
        pass

    def __getattr__(self, nome):
        return getattr(self._c, nome)


def _cfg(lista=TEL, env="dev"):
    return Settings(_env_file=None, env=env, envio_somente_para=lista, waha_api_url="http://waha", waha_api_key="x")


@pytest.fixture
def ligada(conn, clinica):
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, %s)", (clinica.id, SESSAO))
    return clinica


def _so_lembrete(conn, clinica):
    """Deixa na fila só o lembrete (a confirmação imediata é testada à parte)."""
    conn.execute("update outbound_messages set status = 'cancelada' where clinic_id = %s and kind <> 'lembrete'", (clinica.id,))


def _status(conn, clinica, kind="lembrete"):
    return conn.execute("select status, error, attempts from outbound_messages where clinic_id = %s and kind = %s",
                        (clinica.id, kind)).fetchone()


def test_lembrete_so_sai_na_hora_certa(conn, ligada):
    _marcar(conn, ligada, as_(24, 9))
    _so_lembrete(conn, ligada)
    w = WahaFalso()
    assert envio.enviar_pendentes(SemCommit(conn), as_(23, 8, 59), w, s=_cfg()) == 0
    assert envio.enviar_pendentes(SemCommit(conn), as_(23, 9, 1), w, s=_cfg()) == 1
    chat_id, texto = w.enviadas[0]
    assert chat_id == "5511977771234@c.us" and "1 - Confirmar" in texto
    assert _status(conn, ligada)[0] == "enviada"
    # aparece na conversa do paciente (painel e histórico da Ísis)
    assert conn.execute("select count(*) from messages where clinic_id = %s and author = 'isis'", (ligada.id,)).fetchone()[0] == 1


def test_silencio_noturno_segura_o_envio(conn, ligada):
    _marcar(conn, ligada, as_(24, 9))
    _so_lembrete(conn, ligada)
    assert envio.enviar_pendentes(SemCommit(conn), as_(23, 22), WahaFalso(), s=_cfg()) == 0
    assert _status(conn, ligada)[0] == "agendada"


def test_modo_de_teste_nao_envia_para_numero_fora_da_lista(conn, ligada):
    _marcar(conn, ligada, as_(24, 9))
    _so_lembrete(conn, ligada)
    w = WahaFalso()
    envio.enviar_pendentes(SemCommit(conn), as_(23, 9, 1), w, s=_cfg(lista="+5511900009999"))
    assert w.enviadas == [] and _status(conn, ligada)[0] == "cancelada"


def test_producao_envia_sem_lista(conn, ligada):
    _marcar(conn, ligada, as_(24, 9))
    _so_lembrete(conn, ligada)
    assert envio.enviar_pendentes(SemCommit(conn), as_(23, 9, 1), WahaFalso(), s=_cfg(lista="", env="prod")) == 1


def test_clinica_sem_whatsapp_marca_falha(conn, clinica):
    _marcar(conn, clinica, as_(24, 9))
    _so_lembrete(conn, clinica)
    envio.enviar_pendentes(SemCommit(conn), as_(23, 9, 1), WahaFalso(), s=_cfg())
    assert _status(conn, clinica)[:2] == ("falhou", "clínica sem WhatsApp conectado")


def test_falha_do_waha_tenta_de_novo_ate_3_vezes(conn, ligada):
    _marcar(conn, ligada, as_(24, 9))
    _so_lembrete(conn, ligada)
    w, t = WahaFalso(falhar=True), as_(23, 9, 1)
    for _ in range(3):
        envio.enviar_pendentes(SemCommit(conn), t, w, s=_cfg())
        t += timedelta(minutes=10)
    assert _status(conn, ligada)[0] == "falhou" and _status(conn, ligada)[2] == 3


def test_limite_por_minuto(conn, ligada):
    conn.execute("update clinics set settings = settings || '{\"envio_por_minuto\": 1}' where id = %s", (ligada.id,))
    _marcar(conn, ligada, as_(24, 9))
    _marcar(conn, ligada, as_(24, 14), tel="+5511977775555")
    _so_lembrete(conn, ligada)
    lista = f"{TEL},+5511977775555"
    assert envio.enviar_pendentes(SemCommit(conn), as_(23, 9, 1), WahaFalso(), s=_cfg(lista)) == 1


# ---------------------------------------------------------------------------
# Resposta ao lembrete
# ---------------------------------------------------------------------------
def _lembrete_enviado(conn, clinica):
    c = _marcar(conn, clinica, as_(24, 9))
    _so_lembrete(conn, clinica)
    envio.enviar_pendentes(SemCommit(conn), as_(23, 9, 1), WahaFalso(), s=_cfg())
    cl = S.carregar_clinica(conn, clinica.id)
    p = S.buscar_paciente(conn, clinica.id, TEL)
    cv = chat._conversa(conn, clinica.id, p["id"], "whatsapp")
    return c, cl, p, cv


def test_responder_1_confirma_sem_ia(conn, ligada):
    c, cl, p, cv = _lembrete_enviado(conn, ligada)
    r = lembretes.tratar_resposta(conn, cl, p, cv, "1", as_(23, 10))
    assert r and "confirmada" in r
    assert S.detalhar(conn, ligada.id, c["id"])["status"] == "confirmada"
    assert conn.execute("select crm_stage from patients where id = %s", (p["id"],)).fetchone()[0] == "confirmado"


def test_2_e_3_ficam_para_a_isis(conn, ligada):
    _, cl, p, cv = _lembrete_enviado(conn, ligada)
    assert lembretes.tratar_resposta(conn, cl, p, cv, "3", as_(23, 10)) is None


def test_1_sem_lembrete_como_ultima_mensagem_nao_confirma(conn, ligada):
    c, cl, p, cv = _lembrete_enviado(conn, ligada)
    chat._gravar(conn, ligada.id, cv["id"], "out", "isis", "Temos 1) 9h ou 2) 10h, qual prefere?")
    conn.execute("update messages set created_at = clock_timestamp() + interval '1 minute' where content like 'Temos%%'")
    assert lembretes.tratar_resposta(conn, cl, p, cv, "1", as_(23, 10)) is None
    assert S.detalhar(conn, ligada.id, c["id"])["status"] == "agendada"


def test_parar_desliga_disparos(conn, ligada):
    _, cl, p, cv = _lembrete_enviado(conn, ligada)
    assert "não vai mais receber" in lembretes.tratar_resposta(conn, cl, p, cv, "PARAR", as_(23, 10))
    assert conn.execute("select optout_disparos from patients where id = %s", (p["id"],)).fetchone()[0] is True


# ---------------------------------------------------------------------------
# Aniversário
# ---------------------------------------------------------------------------
def _aniversariante(conn, clinica, tel=TEL, optout=False):
    p = S.obter_ou_criar_paciente(conn, clinica.id, tel, "Joana Prado", "manual")
    conn.execute("update patients set birth_date = '1990-11-20', optout_disparos = %s where id = %s", (optout, p["id"]))
    conn.execute(
        """update clinics set settings = settings || '{"aniversario_ativo": true, "aniversario_texto": "Parabéns, {nome}! — {clinica}"}'
           where id = %s""", (clinica.id,))
    return p


def _aniversarios(conn, clinica):
    return conn.execute("select body from outbound_messages where clinic_id = %s and kind = 'aniversario'", (clinica.id,)).fetchall()


def test_aniversario_uma_vez_por_ano_depois_das_9h(conn, clinica):
    _aniversariante(conn, clinica)
    assert lembretes.gerar_aniversarios(conn, as_(20, 8, 59)) == 0
    lembretes.gerar_aniversarios(conn, as_(20, 9, 0))
    lembretes.gerar_aniversarios(conn, as_(20, 15, 0))  # roda de novo no mesmo dia: não duplica
    assert _aniversarios(conn, clinica) == [("Parabéns, Joana! — Clínica Teste A",)]


def test_aniversario_respeita_quem_pediu_para_sair(conn, clinica):
    _aniversariante(conn, clinica, optout=True)
    lembretes.gerar_aniversarios(conn, as_(20, 10))
    assert _aniversarios(conn, clinica) == []


def test_aniversario_desligado_nao_gera(conn, clinica):
    _aniversariante(conn, clinica)
    conn.execute("update clinics set settings = settings || '{\"aniversario_ativo\": false}' where id = %s", (clinica.id,))
    lembretes.gerar_aniversarios(conn, as_(20, 10))
    assert _aniversarios(conn, clinica) == []


def test_montar_aniversario_nao_quebra_com_chaves_estranhas():
    assert lembretes.montar_aniversario("Oi {nome} {x}", "Ana Paula", "Clínica") == "Oi Ana {x}"


def test_agora_do_teste_e_sexta():
    assert AGORA.weekday() == 4 and isinstance(AGORA, datetime)
