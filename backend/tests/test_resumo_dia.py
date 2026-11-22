"""Etapa 23 — resumo do dia do profissional (RN-RS, D96–D98). WAHA simulado; nada sai de verdade."""

from datetime import date

from psycopg.rows import dict_row

import pytest

from app import tratamentos as T
from app.agenda import servico as S
from app.canais.waha import WahaErro
from app.config import Settings
from app.mensagens import resumo_dia as RD
from tests.conftest import AGORA, as_
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada
from tests.test_lembretes import SemCommit  # enviar_resumos faz commit: no teste, nada pode ser gravado

NUM = "+5511944443333"


class WahaFalso:
    def __init__(self, falhar=False):
        self.enviadas, self.falhar = [], falhar

    def enviar_texto(self, sessao, chat_id, texto, simular_digitacao=None):
        if self.falhar:
            raise WahaErro("WAHA fora do ar")
        self.enviadas.append((chat_id, texto))
        return "id"


def _cfg(lista="", env="prod"):
    return Settings(_env_file=None, env=env, envio_somente_para=lista, waha_api_url="http://waha", waha_api_key="x")


@pytest.fixture
def pronta(conn, clinica):
    """Dra. A pediu o resumo; clínica com WhatsApp; segunda 23/11 com duas consultas dela."""
    conn.execute("insert into whatsapp_instances (clinic_id, session) values (%s, 'clinica_a')", (clinica.id,))
    conn.execute("update professionals set resumo_ativo = true, whatsapp_pessoal = %s where id = %s", (NUM, clinica.prof_a))
    c1 = S.marcar(conn, clinica.id, telefone="+5511977771111", nome="Maria da Silva", professional_id=clinica.prof_a,
                  service_id=clinica.servico, inicio=as_(23, 8), ator="recepcao", agora=AGORA)
    S.mudar_status(conn, clinica.id, appointment_id=c1["id"], novo="confirmada", ator="recepcao")
    p = S.obter_ou_criar_paciente(conn, clinica.id, "+5511977772222", "João Pereira", "manual")
    t = T.criar(conn, clinica.id, p["id"], service_id=clinica.servico, professional_id=None, sessoes_previstas=4,
                intervalo_dias=7, orientacao=None)
    conn.execute(
        """insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at, status, treatment_id)
           values (%s, %s, %s, %s, '2026-11-16 14:00-03', '2026-11-16 15:00-03', 'realizada', %s)""",
        (clinica.id, p["id"], clinica.prof_a, clinica.servico, t["id"]))
    S.marcar(conn, clinica.id, telefone="+5511977772222", nome=None, professional_id=clinica.prof_a,
             service_id=clinica.servico, inicio=as_(23, 14), ator="recepcao", agora=AGORA)
    return clinica


def _prof(conn, clinica):
    return conn.execute("select id, name from professionals where id = %s", (clinica.prof_a,)).fetchone()


def test_texto_do_resumo(conn, pronta):
    cl = S.carregar_clinica(conn, pronta.id)
    texto = RD.montar(conn, cl, {"id": pronta.prof_a, "name": "Dra. A"}, date(2026, 11, 23))
    assert texto.startswith("Bom dia, Dra. A! ☀️\nHoje, segunda-feira, 23/11, você tem 2 consultas")
    assert "08:00 · Maria · Limpeza ✅" in texto  # só o primeiro nome (D96)
    assert "14:00 · João · Limpeza (sessão 2 de 4) ⏳" in texto
    assert "Pausa: 12:00–13:00" in texto and "Livre: 09:00–12:00, 13:00–14:00, 15:00–18:00" in texto
    assert "Silva" not in texto and "97777" not in texto  # sem sobrenome nem telefone
    assert RD.montar(conn, cl, {"id": pronta.prof_b, "name": "Dr. B"}, date(2026, 11, 23)) is None  # sem consulta


def test_manda_uma_vez_no_horario(conn, pronta):
    w = WahaFalso()
    assert RD.enviar_resumos(SemCommit(conn), as_(23, 6, 59), w, _cfg(), so_clinica=pronta.id) == 0  # antes das 07:00
    assert RD.enviar_resumos(SemCommit(conn), as_(23, 7, 1), w, _cfg(), so_clinica=pronta.id) == 1
    assert RD.enviar_resumos(SemCommit(conn), as_(23, 7, 30), w, _cfg(), so_clinica=pronta.id) == 0  # uma vez por dia (D98)
    chat_id, texto = w.enviadas[0]
    assert chat_id == "5511944443333@c.us" and "Maria" in texto


def test_sem_consulta_fim_de_semana_e_desativado(conn, pronta):
    w = WahaFalso()
    assert RD.enviar_resumos(SemCommit(conn), as_(22, 7, 1), w, _cfg(), so_clinica=pronta.id) == 0  # domingo: clínica fechada
    assert RD.enviar_resumos(SemCommit(conn), as_(24, 7, 1), w, _cfg(), so_clinica=pronta.id) == 0  # terça sem consulta
    st = conn.execute("select status from professional_digests where professional_id = %s and dia = '2026-11-24'",
                      (pronta.prof_a,)).fetchone()[0]
    assert st == "sem_consulta" and w.enviadas == []
    conn.execute("update professionals set resumo_ativo = false where id = %s", (pronta.prof_a,))
    assert RD.enviar_resumos(SemCommit(conn), as_(23, 7, 1), w, _cfg(), so_clinica=pronta.id) == 0  # D97: só quem pediu


def test_modo_de_teste_falha_e_atraso(conn, pronta):
    w = WahaFalso()
    RD.enviar_resumos(SemCommit(conn), as_(23, 7, 1), w, _cfg(lista="+5511900009999", env="dev"), so_clinica=pronta.id)
    assert w.enviadas == [] and conn.execute(
        "select status from professional_digests where professional_id = %s", (pronta.prof_a,)).fetchone()[0] == "pulado"
    conn.execute("delete from professional_digests where professional_id = %s", (pronta.prof_a,))
    ruim = WahaFalso(falhar=True)
    for m in range(4):  # tenta no máximo 3 vezes
        RD.enviar_resumos(SemCommit(conn), as_(23, 7, m + 1), ruim, _cfg(), so_clinica=pronta.id)
    assert conn.execute("select status, attempts from professional_digests where professional_id = %s",
                        (pronta.prof_a,)).fetchone() == ("falhou", 3)
    conn.execute("delete from professional_digests where professional_id = %s", (pronta.prof_a,))
    assert RD.enviar_resumos(SemCommit(conn), as_(23, 11), w, _cfg(), so_clinica=pronta.id) == 0  # 4 h atrasado: não manda


def test_rotas(cliente, conn, clinica):  # noqa: F811
    base = f"/api/clinics/{clinica.id}/config/profissionais/{clinica.prof_a}/resumo"
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    assert rec.put(base, json={"ativo": True, "whatsapp": "11944443333"}).status_code == 403
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    assert adm.put(base, json={"ativo": True}).status_code == 422  # sem número não ativa
    r = adm.put(base, json={"ativo": True, "whatsapp": "(11) 94444-3333", "hora": "06:30"}).json()
    assert (r["ativo"], r["whatsapp"], r["hora"]) == (True, NUM, "06:30")
    assert adm.get(f"{base}/previa?dia=2026-11-23").json()["texto"] is None  # sem consulta nesse dia


def test_mandar_teste_agora(conn, pronta):
    w = WahaFalso()
    cl = S.carregar_clinica(conn, pronta.id)
    prof = conn.cursor(row_factory=dict_row).execute(
        "select id, name, whatsapp_pessoal, resumo_hora from professionals where id = %s", (pronta.prof_a,)).fetchone()
    r = RD.enviar_teste(conn, cl, prof, as_(22, 15), w, _cfg())  # domingo: usa o próximo dia com consulta (segunda)
    assert r["dia"] == date(2026, 11, 23) and w.enviadas[0][1].startswith("🧪 Teste do resumo do dia")
    assert conn.execute("select count(*) from professional_digests where professional_id = %s", (pronta.prof_a,)).fetchone()[0] == 0
    with pytest.raises(WahaErro):  # modo de teste continua valendo
        RD.enviar_teste(conn, cl, prof, as_(22, 15), w, _cfg(lista="+5511900009999", env="dev"))
