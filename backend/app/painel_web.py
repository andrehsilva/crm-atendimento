"""Painel (React compilado) servido pelo próprio backend — um serviço só no Easypanel.

Só liga quando a pasta do painel compilado existe (no Dockerfile da raiz ela vem em /app/frontend/dist;
em desenvolvimento o Vite continua servindo as telas e isto fica desligado).

- /assets/*: arquivos com nome versionado → cache longo.
- Qualquer outra rota que não seja da API abre o index.html (aplicação de página única).
- Rotas da API que não existem continuam respondendo 404 em JSON (não viram tela).
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.gzip import GZipMiddleware

DA_API = ("api/", "webhooks/", "site/", "health")

CABECALHOS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    # SAMEORIGIN: a prévia do site (Configurações › Site) abre dentro do próprio painel
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def servir_painel(app: FastAPI, pasta: Path) -> bool:
    """Registra as rotas do painel. Chamar DEPOIS de incluir todos os routers da API."""
    pasta = pasta.resolve()
    indice = pasta / "index.html"
    if not indice.is_file():
        return False

    app.add_middleware(GZipMiddleware, minimum_size=1024)  # o tempo real (text/event-stream) não é comprimido

    @app.middleware("http")
    async def cabecalhos_de_seguranca(request: Request, call_next):
        resposta = await call_next(request)
        for nome, valor in CABECALHOS.items():
            resposta.headers.setdefault(nome, valor)
        return resposta

    @app.get("/{caminho:path}", include_in_schema=False)
    def painel(caminho: str):
        if caminho.startswith(DA_API):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if caminho:
            arquivo = (pasta / caminho).resolve()
            if arquivo.is_file() and arquivo.is_relative_to(pasta):  # nada fora da pasta do painel
                cache = "public, max-age=31536000, immutable" if caminho.startswith("assets/") else "no-cache"
                return FileResponse(arquivo, headers={"Cache-Control": cache})
        return FileResponse(indice, headers={"Cache-Control": "no-cache"})

    return True
