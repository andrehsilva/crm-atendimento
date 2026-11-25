"""Etapa 32 (desempenho): cache curto do que é pedido em toda tela — e que nunca mostra dado velho depois de gravar."""

from app.core import cache
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401 — fixture reaproveitada


def test_memo_guarda_e_limpar_apaga():
    cache.ATIVO = True
    chamadas = []
    calc = lambda: chamadas.append(1) or len(chamadas)  # noqa: E731
    assert cache.memo("x", 30, calc) == 1 and cache.memo("x", 30, calc) == 1  # 2ª vez veio do cache
    cache.limpar()
    assert cache.memo("x", 30, calc) == 2
    assert cache.memo("y", -1, calc) == 3 and cache.memo("y", -1, calc) == 4  # vencido: calcula de novo


def test_gravar_limpa_o_cache_dos_dados_da_clinica(cliente, conn, clinica):  # noqa: F811
    cache.ATIVO = True
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    assert adm.get(f"/api/clinics/{clinica.id}").json()["name"] == "Clínica Teste A"
    conn.execute("update clinics set name = 'Mudou por fora' where id = %s", (clinica.id,))
    assert adm.get(f"/api/clinics/{clinica.id}").json()["name"] == "Clínica Teste A"  # ainda do cache (até 30 s)
    adm.post(f"/api/clinics/{clinica.id}/whatsapp/reiniciar")  # qualquer gravação (mesmo recusada) limpa
    assert adm.get(f"/api/clinics/{clinica.id}").json()["name"] == "Mudou por fora"


def test_cadastros_vem_do_cache_ate_gravar(cliente, conn, clinica):  # noqa: F811
    cache.ATIVO = True
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    antes = len(adm.get(f"/api/clinics/{clinica.id}/cadastros").json()["profissionais"])
    conn.execute("insert into professionals (clinic_id, name) values (%s, 'Dr. Novo')", (clinica.id,))
    assert len(adm.get(f"/api/clinics/{clinica.id}/cadastros").json()["profissionais"]) == antes
    cache.limpar()
    assert len(adm.get(f"/api/clinics/{clinica.id}/cadastros").json()["profissionais"]) == antes + 1
