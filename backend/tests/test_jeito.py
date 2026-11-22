"""Etapa 17 (D77, D78) — "Jeito da clínica": orientações da clínica no fim do prompt, sem passar por cima das regras."""

from psycopg.types.json import Jsonb

from app.agenda import servico as S
from app.agent.contexto import instrucoes
from tests.conftest import AGORA
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401


def test_jeito_entra_no_fim_e_com_aviso_de_prioridade(conn, clinica):
    conn.execute("update clinics set settings = settings || %s where id = %s",
                 (Jsonb({"jeito_clinica": "Somos uma clínica infantil: fale de forma leve."}), clinica.id))
    c = S.carregar_clinica(conn, clinica.id)
    pac = S.obter_ou_criar_paciente(conn, clinica.id, "+5511955550077", None, origem="web")
    texto = instrucoes(conn, c, pac, AGORA)
    assert texto.rstrip().endswith("ORIENTACOES_DA_CLINICA>>>")
    assert "prioridade menor que todas as regras acima" in texto and "clínica infantil" in texto


def test_so_admin_salva_e_limite_de_tamanho(cliente, conn, clinica):  # noqa: F811
    url = f"/api/clinics/{clinica.id}/config/assistente"
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    atual = adm.get(url).json()
    assert adm.put(url, json={**atual, "jeito_clinica": "Ofereça a avaliação primeiro."}).json()["jeito_clinica"] == "Ofereça a avaliação primeiro."
    assert adm.put(url, json={**atual, "jeito_clinica": "x" * 1501}).status_code == 422
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id))
    assert rec.put(url, json={**atual, "jeito_clinica": "mudei"}).status_code == 403
