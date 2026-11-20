"""Etapa 8B — proteções de produção."""

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.core.producao import problemas
from app.main import app

BOA = dict(
    env="prod", database_url="postgresql://x", supabase_url="https://x.supabase.co", supabase_anon_key="pub",
    supabase_service_role_key="sec", llm_api_key="k", waha_api_url="https://waha.x", waha_api_key="w",
    waha_webhook_hmac_key="a" * 48, public_base_url="https://isis.exemplo.com.br", frontend_origin="https://isis.exemplo.com.br",
)


def _cfg(**mudar) -> Settings:
    return Settings(_env_file=None, **{**BOA, **mudar})


def test_configuracao_completa_sobe():
    assert problemas(_cfg()) == []


def test_dev_nao_e_checado():
    assert problemas(Settings(_env_file=None, env="dev")) == []


def test_faltando_chave_nao_sobe():
    erros = problemas(_cfg(waha_webhook_hmac_key="", supabase_service_role_key=""))
    assert any("WAHA_WEBHOOK_HMAC_KEY" in e for e in erros) and any("SUPABASE_SERVICE_ROLE_KEY" in e for e in erros)


def test_sem_https_ou_com_tunel_nao_sobe():
    assert any("https://" in e for e in problemas(_cfg(public_base_url="http://isis.exemplo.com.br")))
    assert any("desenvolvimento" in e for e in problemas(_cfg(public_base_url="https://abc.trycloudflare.com")))
    assert any("desenvolvimento" in e for e in problemas(_cfg(frontend_origin="https://localhost:5173")))


def test_chat_de_teste_em_producao_nao_sobe():
    assert any("CHAT_TESTE" in e for e in problemas(_cfg(chat_teste=True)))


def test_chat_de_teste_so_liberado_em_dev():
    assert Settings(_env_file=None, env="dev").chat_teste_liberado is True
    assert _cfg().chat_teste_liberado is False
    assert Settings(_env_file=None, env="dev", chat_teste=False).chat_teste_liberado is False


def test_chat_de_teste_desligado_some(monkeypatch):
    monkeypatch.setattr(get_settings(), "chat_teste", False)
    r = TestClient(app).get("/api/web/demo/history", params={"telefone": "+5511911112222"})
    assert r.status_code == 404


def test_cookie_seguro_em_producao(monkeypatch):
    from fastapi import Response

    from app.auth import acesso
    from app.auth.supabase import Sessao

    monkeypatch.setattr(acesso, "get_settings", lambda: _cfg())
    resp = Response()
    acesso.gravar_cookies(resp, Sessao("a", "r", 3600, "u"))
    cookies = resp.headers.getlist("set-cookie")
    assert all("Secure" in c and "HttpOnly" in c and "SameSite=lax" in c for c in cookies)
