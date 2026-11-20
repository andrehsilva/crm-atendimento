from fastapi.testclient import TestClient

import app.api.health as health
from app.config import Settings
from app.main import app


def _config(**valores) -> Settings:
    base = {"database_url": "", "llm_api_key": ""} | valores
    return Settings(_env_file=None, **base)


def test_health_responde_ok_sem_configuracao(monkeypatch):
    monkeypatch.setattr(health, "get_settings", lambda: _config())
    corpo = TestClient(app).get("/health").json()
    assert corpo["status"] == "ok"
    assert corpo["banco"]["status"] == "não configurado"
    assert corpo["ia"]["status"] == "não configurada"


def test_health_nao_vaza_segredos(monkeypatch):
    monkeypatch.setattr(health, "get_settings", lambda: _config(llm_api_key="sk-segredo-123"))
    texto = TestClient(app).get("/health").text
    assert "sk-segredo-123" not in texto


def test_health_mostra_erro_de_banco_sem_vazar_senha(monkeypatch):
    url = "postgresql://usuario:senhaSecreta@127.0.0.1:1/postgres"
    monkeypatch.setattr(health, "get_settings", lambda: _config(database_url=url))
    corpo = TestClient(app).get("/health").json()
    assert corpo["banco"]["status"] == "erro"
    assert "senhaSecreta" not in str(corpo)
