"""Site de apresentação (Etapa 11A).

- Público: GET /site/{slug} (HTML) e /site/{slug}/logo. Só mostra site PUBLICADO de clínica ativa.
- Painel: situação, layout, publicar e prévia em /api/clinics/{id}/site. Mudar e publicar: só o admin da clínica.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, Field

from app import aparencia, configuracao_inicial as inicial
from app.agenda.erros import AgendaError
from app.auth.acesso import acesso, exigir_admin_clinica
from app.config import get_settings
from app.db import get_conn
from app.site import montagem

publico = APIRouter(tags=["site público"])
painel = APIRouter(prefix="/api/clinics/{clinic_id}/site", tags=["site"], dependencies=[Depends(acesso)])

CABECALHOS = {"Content-Security-Policy": montagem.CSP, "X-Content-Type-Options": "nosniff",
              "Referrer-Policy": "strict-origin-when-cross-origin"}


def _html(conteudo: str, status: int = 200, cache: str = "public, max-age=300") -> HTMLResponse:
    return HTMLResponse(conteudo, status_code=status, headers={**CABECALHOS, "Cache-Control": cache})


def _site(conn, clinic_id: UUID) -> tuple[str, bool]:
    r = conn.execute("select template, publicado from clinic_sites where clinic_id = %s", (clinic_id,)).fetchone()
    return r if r else ("classico", False)


# ---------------------------------------------------------------------------
# Público
# ---------------------------------------------------------------------------
def _clinica_publicada(conn, slug: str) -> tuple[UUID, str] | None:
    r = conn.execute(
        """select c.id, s.template from clinics c join clinic_sites s on s.clinic_id = c.id
           where c.slug = %s and c.status = 'ativa' and s.publicado""", (slug.lower(),)).fetchone()
    return (r[0], r[1]) if r else None


@publico.get("/site/{slug}", response_class=HTMLResponse, include_in_schema=False)
def site(slug: str, conn=Depends(get_conn)):
    achada = _clinica_publicada(conn, slug)
    if not achada:
        return _html(montagem.pagina_nao_encontrada(), status=404, cache="no-store")
    return _html(montagem.desenhar(conn, achada[0], achada[1]))


@publico.get("/site/_estatico/fontes/{nome}", include_in_schema=False)
def fonte(nome: str):
    if nome not in montagem.FONTES:
        return Response(status_code=404)
    return FileResponse(montagem.ESTATICO / "fontes" / nome, media_type="font/woff2",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})


@publico.get("/site/_estatico/js/{nome}", include_in_schema=False)
def script(nome: str):
    if nome not in montagem.SCRIPTS:
        return Response(status_code=404)
    return FileResponse(montagem.ESTATICO / "js" / nome, media_type="text/javascript",
                        headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"})


@publico.get("/site/{slug}/equipe/{professional_id}/foto", include_in_schema=False)
def foto_equipe(slug: str, professional_id: UUID, conn=Depends(get_conn)):
    r = conn.execute(
        """select f.mime, f.data from professional_photos f join professionals p on p.id = f.professional_id and p.active
           join clinics c on c.id = f.clinic_id where c.slug = %s and c.status = 'ativa' and f.professional_id = %s""",
        (slug.lower(), professional_id)).fetchone()
    if not r:
        return Response(status_code=404)
    return aparencia.resposta_imagem(r[0], bytes(r[1]))


@publico.get("/site/{slug}/logo", include_in_schema=False)
def logo(slug: str, conn=Depends(get_conn)):
    r = conn.execute("select l.mime, l.data from clinic_logos l join clinics c on c.id = l.clinic_id "
                     "where c.slug = %s and c.status = 'ativa'", (slug.lower(),)).fetchone()
    if not r:
        return Response(status_code=404)
    return aparencia.resposta_imagem(r[0], bytes(r[1]))


# ---------------------------------------------------------------------------
# Painel
# ---------------------------------------------------------------------------
class Layout(BaseModel):
    template: str = Field(pattern="^(classico|moderno|acolhedor)$")


class Publicar(BaseModel):
    publicado: bool


class CorLayout(BaseModel):
    layout: str = Field(pattern="^(classico|moderno|acolhedor)$")
    cor: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")  # vazio = volta para a cor da clínica


def estado(conn, clinic_id: UUID) -> dict:
    template, publicado = _site(conn, clinic_id)
    slug, cfg = conn.execute("select slug, settings from clinics where id = %s", (clinic_id,)).fetchone()
    cores = {k: montagem.cor_do_layout(conn, clinic_id, k) for k in montagem.LAYOUTS}
    return {"template": template, "publicado": publicado, "url": f"{get_settings().site_base_url.rstrip('/')}/{slug}",
            "cores": cores, "cor_clinica": aparencia.cor_da_clinica(cfg),
            "pode_publicar": inicial.concluida(conn, clinic_id),
            "layouts": [{"id": k, "nome": n, "descricao": d} for k, (n, d) in montagem.LAYOUTS.items()]}


@painel.get("", summary="Situação do site (layout, publicado, endereço)")
def ver(clinic_id: UUID, conn=Depends(get_conn)):
    return estado(conn, clinic_id)


@painel.put("", summary="Escolher o layout")
def escolher_layout(clinic_id: UUID, body: Layout, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    conn.execute("""insert into clinic_sites (clinic_id, template) values (%s, %s)
                    on conflict (clinic_id) do update set template = excluded.template, updated_at = now()""",
                 (clinic_id, body.template))
    return estado(conn, clinic_id)


@painel.put("/cor", summary="Cor de um layout (vazio = cor da clínica)")
def salvar_cor(clinic_id: UUID, body: CorLayout, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    cor = aparencia.validar_cor(body.cor) if body.cor else None  # recusa cor clara demais (contraste com o texto branco)
    conn.execute(
        """insert into clinic_sites (clinic_id, cores) values (%s, jsonb_strip_nulls(jsonb_build_object(%s::text, %s::text)))
           on conflict (clinic_id) do update set
             cores = case when %s::text is null then clinic_sites.cores - %s::text
                          else clinic_sites.cores || jsonb_build_object(%s::text, %s::text) end,
             updated_at = now()""",
        (clinic_id, body.layout, cor, cor, body.layout, body.layout, cor))
    return estado(conn, clinic_id)


@painel.post("/publicar", summary="Publicar ou tirar do ar")
def publicar(clinic_id: UUID, body: Publicar, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    if body.publicado and not inicial.concluida(conn, clinic_id):
        raise AgendaError("DADOS_INVALIDOS", "Conclua os Primeiros passos antes de publicar o site.")
    conn.execute(
        """insert into clinic_sites (clinic_id, publicado, publicado_em) values (%s, %s, case when %s then now() end)
           on conflict (clinic_id) do update set publicado = excluded.publicado,
             publicado_em = coalesce(excluded.publicado_em, clinic_sites.publicado_em), updated_at = now()""",
        (clinic_id, body.publicado, body.publicado))
    return estado(conn, clinic_id)


@painel.get("/previa", response_class=HTMLResponse, summary="Prévia do site com um layout (só para a equipe da clínica)")
def previa(clinic_id: UUID, layout: str | None = None, cor: str | None = None, conn=Depends(get_conn)):
    # cor ainda não salva (o painel mostra antes de salvar): só vale se for #RRGGBB legível; senão usa a salva
    ok = cor and aparencia.COR_RE.match(cor) and aparencia.contraste_com_branco(cor) >= aparencia.CONTRASTE_MINIMO
    return _html(montagem.desenhar(conn, clinic_id, layout or _site(conn, clinic_id)[0], previa=True,
                                   cor=cor.lower() if ok else None), cache="no-store")
