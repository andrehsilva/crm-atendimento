"""Etapa 9A — segmentos de negócio e palavras de cada clínica (D38, D39, D41)."""

import pytest
from psycopg.types.json import Jsonb

from app import segmentos
from app.agenda import servico as S
from app.agent.contexto import PROMPT, vocabulario
from tests.conftest import AGORA, as_
from tests.test_admin import NOVA, admin, supabase_falso  # noqa: F401 — fixtures reaproveitadas
from tests.test_acesso import cliente  # noqa: F401

TEL = "+5511977775555"


def _settings(conn, clinica, novos: dict) -> None:
    conn.execute("update clinics set settings = settings || %s where id = %s", (Jsonb(novos), clinica.id))


def _marcar(conn, clinica):
    return S.marcar(conn, clinica.id, telefone=TEL, nome="Carla Dias", professional_id=clinica.prof_a,
                    service_id=clinica.servico, inicio=as_(25, 9), ator="recepcao", agora=AGORA)


def _mensagens(conn, clinica) -> dict:
    return dict(conn.execute("select kind, body from outbound_messages where clinic_id = %s", (clinica.id,)).fetchall())


# ---------------------------------------------------------------------------
# Palavras
# ---------------------------------------------------------------------------
def test_clinica_antiga_sem_segmento_vale_odontologia():
    t = segmentos.termos({})
    assert segmentos.segmento_de({}).codigo == "odontologia"
    assert (t["profissional"], t["cliente"], t["atendimento"], t["sua"]) == ("dentista", "paciente", "consulta", "sua")


def test_palavras_proprias_e_concordancia():
    t = segmentos.termos({"segmento": "estetica", "termos": {"cliente": "aluna", "atendimento": "aula", "genero": "f"}})
    assert (t["cliente"], t["atendimento"], t["sua"], t["o"], t["profissional"]) == ("aluna", "aula", "sua", "a", "profissional")
    assert segmentos.termos({"segmento": "estetica"})["sua"] == "seu"


@pytest.mark.parametrize("codigo", list(segmentos.SEGMENTOS))
def test_texto_da_assistente_monta_para_todo_segmento(codigo):
    texto = PROMPT.read_text(encoding="utf-8").format(
        nome_assistente="Ísis", clinica="Lugar X", tratamento="você", aviso_horario="",
        **vocabulario({"settings": {"segmento": codigo}, "phone": "+5511999998888"}))
    assert "{" not in texto  # nenhuma variável sobrando
    assert segmentos.SEGMENTOS[codigo].tipo_negocio in texto
    if codigo != "odontologia":
        assert "dentista" not in texto.lower() and "odontol" not in texto.lower()


def test_psicologia_cita_cvv_e_nao_pede_o_motivo():
    texto = PROMPT.read_text(encoding="utf-8").format(
        nome_assistente="Ísis", clinica="X", tratamento="você", aviso_horario="",
        **vocabulario({"settings": {"segmento": "psicologia"}, "phone": "+5511999998888"}))
    assert "CVV (188)" in texto and "sessão" in texto and "não peça detalhes do motivo" in texto


# ---------------------------------------------------------------------------
# Mensagens automáticas
# ---------------------------------------------------------------------------
def test_mensagens_de_odontologia_continuam_iguais(conn, clinica):
    _marcar(conn, clinica)
    m = _mensagens(conn, clinica)
    assert "Sua consulta" in m["confirmacao"] and "marcada" in m["confirmacao"] and "🦷 Limpeza com Dra. A" in m["confirmacao"]
    assert "lembrar da sua consulta" in m["lembrete"]


def test_mensagens_usam_as_palavras_do_segmento(conn, clinica):
    _settings(conn, clinica, {"segmento": "estetica"})
    _marcar(conn, clinica)
    m = _mensagens(conn, clinica)
    assert "Seu atendimento" in m["confirmacao"] and "está marcado" in m["confirmacao"] and "✨ Limpeza" in m["confirmacao"]
    assert "lembrar do seu atendimento" in m["lembrete"]


def test_lembrete_discreto_nao_cita_o_procedimento(conn, clinica):
    _settings(conn, clinica, {"segmento": "psicologia"})
    _marcar(conn, clinica)
    m = _mensagens(conn, clinica)
    assert "Limpeza" not in m["lembrete"] and "Limpeza" not in m["confirmacao"]
    assert "com Dra. A" in m["lembrete"] and "sua sessão" in m["lembrete"]


def test_lembrete_discreto_pode_ser_desligado(conn, clinica):
    _settings(conn, clinica, {"segmento": "psicologia", "lembrete_discreto": False})
    _marcar(conn, clinica)
    assert "Limpeza" in _mensagens(conn, clinica)["lembrete"]


# ---------------------------------------------------------------------------
# Admin geral e Perfil
# ---------------------------------------------------------------------------
def test_criar_clinica_de_psicologia_traz_os_procedimentos_do_segmento(admin, conn, supabase_falso):  # noqa: F811
    r = admin.post("/api/admin/clinicas", json={**NOVA, "telefone": "(11) 3333-5555", "segmento": "psicologia"})
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    settings = conn.execute("select settings from clinics where id = %s", (cid,)).fetchone()[0]
    nomes = {x[0] for x in conn.execute("select name from services where clinic_id = %s", (cid,)).fetchall()}
    assert settings["segmento"] == "psicologia" and "Sessão de psicoterapia" in nomes and "Limpeza (profilaxia)" not in nomes
    assert admin.post("/api/admin/clinicas", json={**NOVA, "telefone": "(11) 3333-6666", "segmento": "padaria"}).status_code == 422


def test_perfil_guarda_so_as_palavras_diferentes_do_padrao(admin, conn, clinica):  # noqa: F811
    url = f"/api/clinics/{clinica.id}/config/perfil"
    corpo = {"nome": "Clínica Teste A", "segmento": "medicina",
             "termos": {"profissional": "médico(a)", "cliente": "cliente"}, "lembrete_discreto": True}
    r = admin.put(url, json=corpo)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["segmento"] == "medicina" and d["termos_proprios"] == {"cliente": "cliente"} and d["lembrete_discreto"] is True
    assert admin.get(f"/api/clinics/{clinica.id}").json()["termos"]["cliente"] == "cliente"
