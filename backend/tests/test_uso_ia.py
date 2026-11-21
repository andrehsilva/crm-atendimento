"""Etapa 10B — tokens, custo estimado, preços, cotação e teto mensal (D44, D45, D46)."""

from datetime import datetime
from decimal import Decimal
from itertools import count
from types import SimpleNamespace

from app import uso_ia
from app.agenda import servico as S
from app.ia import ConfigIA
from app.painel import chat
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401

_TELEFONES = count(10000)
CFG = ConfigIA("clinica", "openai", "gpt-x", "https://api.openai.com/v1", "responses", "k")


def _conversa(conn, clinica, telefone="+5511955550099"):
    pac = S.obter_ou_criar_paciente(conn, clinica.id, telefone, None, origem="web")
    cid = conn.execute("insert into conversations (clinic_id, patient_id, channel) values (%s, %s, 'web') returning id",
                       (clinica.id, pac["id"])).fetchone()[0]
    return pac, cid


def _run(conn, clinica, custo, origem="clinica"):
    _, conv = _conversa(conn, clinica, f"+55119555{next(_TELEFONES):05d}")
    conn.execute(
        """insert into agent_runs (clinic_id, conversation_id, input, tools, output, latency_ms, provider, model, origem,
                                   tokens_entrada, tokens_saida, custo_usd)
           values (%s, %s, 'oi', '[]', 'olá', 10, 'openai', 'gpt-x', %s, 100, 50, %s)""", (clinica.id, conv, origem, custo))


def test_custo_usa_preco_por_milhao_e_cache_mais_barato(conn):
    uso_ia.salvar_preco(conn, "openai", "gpt-x", 2.0, 8.0, 0.5)
    # 1M entrada (200k em cache) + 500k saída = 800k*2 + 200k*0.5 + 500k*8 = 1.6 + 0.1 + 4.0
    assert uso_ia.calcular_custo(conn, CFG, 1_000_000, 500_000, 200_000) == Decimal("5.700000")
    sem_preco = ConfigIA("clinica", "openai", "sem-preco", "", "responses", "k")
    assert uso_ia.calcular_custo(conn, sem_preco, 10, 10, 0) is None


def test_plataforma_opencode_go_usa_preco_do_opencode(conn):
    uso_ia.salvar_preco(conn, "opencode", "gpt-6-luna", 1.0, 1.0, None)
    cfg = ConfigIA("plataforma", "opencode-go", "gpt-6-luna", "", "responses", "k")
    assert uso_ia.calcular_custo(conn, cfg, 1_000_000, 0, 0) == Decimal("1.000000")


def test_tokens_vem_das_metricas_do_agno():
    r = SimpleNamespace(metrics=SimpleNamespace(input_tokens=120, output_tokens=30, cache_read_tokens=100))
    assert uso_ia.tokens_da_resposta(r) == (120, 30, 100)
    assert uso_ia.tokens_da_resposta(SimpleNamespace(metrics=None)) == (0, 0, 0)


def test_niveis_do_teto(conn, clinica):
    assert uso_ia.situacao(conn, clinica.id)["nivel"] == "ok"  # sem teto
    uso_ia.salvar_teto(conn, clinica.id, 10)
    _run(conn, clinica, 7.9)
    assert uso_ia.situacao(conn, clinica.id)["nivel"] == "ok"
    _run(conn, clinica, 0.2)
    s = uso_ia.situacao(conn, clinica.id)
    assert s["nivel"] == "aviso" and s["pct"] == 81.0
    _run(conn, clinica, 2)
    assert uso_ia.pausada(conn, clinica.id)


def test_teto_atingido_pausa_avisa_o_paciente_e_passa_para_a_equipe(conn, clinica, monkeypatch):
    from app.agent import isis

    uso_ia.salvar_teto(conn, clinica.id, 1)
    _run(conn, clinica, 1.5)
    chamou = []
    monkeypatch.setattr(isis, "responder", lambda *a, **k: chamou.append(1) or "não devia")
    monkeypatch.setattr(conn, "commit", lambda: None)
    slug = conn.execute("select slug from clinics where id = %s", (clinica.id,)).fetchone()[0]
    novas = chat.receber(conn, slug, "+5511955556666", "Oi")
    assert not chamou and len(novas) == 2 and novas[1]["content"] == isis.AVISO_EQUIPE
    # a 2ª mensagem não repete o aviso (a conversa já está com a equipe)
    assert len(chat.receber(conn, slug, "+5511955556666", "Alguém?")) == 1


def test_resposta_grava_tokens_e_custo(conn, clinica, monkeypatch):
    from app.agent import isis

    uso_ia.salvar_preco(conn, "opencode", "m", 1.0, 2.0, None)
    cfg = ConfigIA("plataforma", "opencode-go", "m", "https://x", "responses", "k")

    class _IA:
        def __init__(self, **_):
            pass

        def run(self, _):
            return SimpleNamespace(content="Olá!", metrics=SimpleNamespace(input_tokens=1000, output_tokens=500, cache_read_tokens=0))

    monkeypatch.setattr(isis, "Agent", _IA)
    c = S.carregar_clinica(conn, clinica.id)
    pac, conv = _conversa(conn, clinica, "+5511955557777")
    isis.responder(conn, c, pac, {"id": conv, "status": "ativa"}, "oi", datetime.now(c["tz"]), cfg)
    linha = conn.execute("select provider, model, origem, tokens_entrada, tokens_saida, custo_usd from agent_runs "
                         "where conversation_id = %s", (conv,)).fetchone()
    assert linha == ("opencode-go", "m", "plataforma", 1000, 500, Decimal("0.002000"))


def test_rotas_teto_so_admin_e_precos_so_admin_geral(cliente, conn, clinica):  # noqa: F811
    rec, adm = _usuario(conn, clinic_id=clinica.id), _usuario(conn, clinic_id=clinica.id, papel="clinic_admin")
    url = f"/api/clinics/{clinica.id}/config/uso-ia"
    assert _como(cliente, rec).get(url).status_code == 200
    assert _como(cliente, rec).put(f"{url}/teto", json={"teto_usd": 5}).status_code == 403
    assert _como(cliente, adm).put(f"{url}/teto", json={"teto_usd": 5}).json()["situacao"]["teto_usd"] == 5
    preco = {"provedor": "openai", "modelo": "gpt-x", "entrada_usd": 1, "saida_usd": 2}
    assert _como(cliente, adm).put("/api/admin/precos", json=preco).status_code == 403
    sup = _como(cliente, _usuario(conn, super_admin=True))
    assert any(p["model"] == "gpt-x" for p in sup.put("/api/admin/precos", json=preco).json()["precos"])
    assert sup.put("/api/admin/cotacao", json={"cotacao_brl": 5.4}).json()["cotacao_brl"] == 5.4
