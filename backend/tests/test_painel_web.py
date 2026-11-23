"""Um serviço só: o backend entrega o painel compilado sem engolir as rotas da API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.painel_web import servir_painel


def _app(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>painel</html>", encoding="utf-8")
    (tmp_path / "assets" / "app-123.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path.parent / "segredo.txt").write_text("não", encoding="utf-8")
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    assert servir_painel(app, tmp_path)
    return TestClient(app)


def test_rotas_do_painel_e_da_api(tmp_path):
    c = _app(tmp_path)
    assert c.get("/api/ping").json() == {"ok": True}
    r = c.get("/")
    assert "painel" in r.text and r.headers["cache-control"] == "no-cache"
    assert r.headers["x-frame-options"] == "SAMEORIGIN"
    assert "painel" in c.get("/agenda").text  # rota da tela abre o index.html
    r = c.get("/assets/app-123.js")
    assert r.text == "console.log(1)" and "immutable" in r.headers["cache-control"]
    r = c.get("/api/nao-existe")
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}
    assert c.get("/webhooks/x").status_code == 404


def test_nao_sai_da_pasta(tmp_path):
    c = _app(tmp_path)
    for caminho in ("/../segredo.txt", "/%2e%2e/segredo.txt", "/assets/../../segredo.txt"):
        assert "não" not in c.get(caminho).text


def test_sem_painel_compilado_fica_desligado(tmp_path):
    assert servir_painel(FastAPI(), tmp_path / "nao-existe") is False
