"""Etapa 10C — configuração inicial obrigatória (D51–D54)."""

from psycopg.types.json import Jsonb

from app import configuracao_inicial as inicial, ia
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401


def _url(clinica):
    return f"/api/clinics/{clinica.id}/config/inicial"


def _ok(conn, clinica):
    return {e.codigo: e.ok for e in inicial.etapas(conn, clinica.id)}


def _completa(conn, clinica):
    conn.execute("update clinics set address = 'Rua A, 1', settings = %s where id = %s",
                 (Jsonb({"telefone_urgencia": "+5511999990000", "segmento": "odontologia",
                         "nome_assistente": "Margareth", "tratamento": "você"}), clinica.id))


def test_clinica_nova_comeca_pendente_e_cada_etapa_le_os_dados(conn, clinica):
    ok = _ok(conn, clinica)
    assert not ok["clinica"] and not ok["assistente"] and not ok["aparencia"]
    assert ok["horarios"] and ok["equipe"] and ok["ia"]  # fixture: horários, Limpeza + 2 profissionais, chave da plataforma
    _completa(conn, clinica)
    inicial.confirmar_aparencia(conn, clinica.id)
    assert all(_ok(conn, clinica).values())


def test_equipe_exige_profissional_ativo_que_faca_um_procedimento(conn, clinica):
    conn.execute("update professionals set active = false where clinic_id = %s", (clinica.id,))
    assert not _ok(conn, clinica)["equipe"]


def test_chave_propria_so_conta_depois_do_teste_e_trocar_zera(conn, clinica, monkeypatch):
    conn.execute("update clinic_ai set usa_plataforma = false where clinic_id = %s", (clinica.id,))
    ia.salvar_chave(conn, clinica.id, "openai", "gpt-x", "sk-teste-0123456789", None)
    assert not _ok(conn, clinica)["ia"]
    ia.marcar_verificada(conn, clinica.id, ia.config_da_clinica(conn, clinica.id))
    assert _ok(conn, clinica)["ia"]
    ia.salvar_chave(conn, clinica.id, "openai", "gpt-y", None, None)  # trocou o modelo
    assert not _ok(conn, clinica)["ia"]
    # testar valores digitados diferentes do salvo não conta
    outra = ia.ConfigIA("clinica", "openai", "gpt-y", "https://api.openai.com/v1", "responses", "sk-outra-chave-9999")
    ia.marcar_verificada(conn, clinica.id, outra)
    assert not _ok(conn, clinica)["ia"]


def test_concluir_so_com_tudo_pronto_e_so_o_admin(cliente, conn, clinica):  # noqa: F811
    admin, rec = _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"), _usuario(conn, clinic_id=clinica.id)
    r = _como(cliente, admin).post(f"{_url(clinica)}/concluir")
    assert r.status_code == 422 and "Dados da clínica" in r.json()["mensagem"]
    _completa(conn, clinica)
    assert _como(cliente, rec).post(f"{_url(clinica)}/aparencia").status_code == 403
    assert _como(cliente, admin).post(f"{_url(clinica)}/aparencia").json()["pode_concluir"] is True
    assert _como(cliente, rec).post(f"{_url(clinica)}/concluir").status_code == 403
    assert _como(cliente, admin).post(f"{_url(clinica)}/concluir").json()["concluida"] is True
    assert _como(cliente, rec).get(f"/api/clinics/{clinica.id}").json()["configurada"] is True


def test_depois_de_concluida_nao_trava_e_mostra_pendencia(cliente, conn, clinica):  # noqa: F811
    _completa(conn, clinica)
    inicial.confirmar_aparencia(conn, clinica.id)
    assert inicial.concluir(conn, clinica.id) == []
    conn.execute("update clinic_ai set usa_plataforma = false where clinic_id = %s", (clinica.id,))  # perdeu a IA
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id)).get(f"/api/clinics/{clinica.id}").json()
    assert c["configurada"] is True and c["pendencias"] == ["Inteligência artificial"]
