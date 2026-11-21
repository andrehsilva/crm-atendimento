"""Site de apresentação (Etapa 11A).

- Público: GET /site/{slug} (HTML) e /site/{slug}/logo. Só mostra site PUBLICADO de clínica ativa.
- Painel: situação, layout, publicar e prévia em /api/clinics/{id}/site. Mudar e publicar: só o admin da clínica.
"""

from html import escape
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from psycopg.types.json import Jsonb
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


@publico.get("/site/sitemap.xml", include_in_schema=False)
def sitemap(conn=Depends(get_conn)):
    """Lista de sites publicados, para o Google (11B)."""
    base = get_settings().site_base_url.rstrip("/")
    linhas = conn.execute(
        """select c.slug, greatest(s.updated_at, c.updated_at) from clinics c join clinic_sites s on s.clinic_id = c.id
           where s.publicado and c.status = 'ativa' order by c.slug""").fetchall()
    itens = "".join(f"<url><loc>{escape(f'{base}/{slug}')}</loc><lastmod>{quando:%Y-%m-%d}</lastmod></url>"
                    for slug, quando in linhas)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{itens}</urlset>'
    return Response(xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})


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


@publico.get("/site/{slug}/galeria/{foto_id}", include_in_schema=False)
def foto_galeria(slug: str, foto_id: UUID, conn=Depends(get_conn)):
    r = conn.execute("""select f.mime, f.data from site_photos f join clinics c on c.id = f.clinic_id
                        where c.slug = %s and c.status = 'ativa' and f.id = %s""", (slug.lower(), foto_id)).fetchone()
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


# ---------------------------------------------------------------------------
# 11B — conteúdo: textos, seções, procedimentos no site e galeria
# ---------------------------------------------------------------------------
class Textos(BaseModel):
    titulo: str = Field("", max_length=80)
    frase: str = Field("", max_length=200)
    sobre: str = Field("", max_length=1500)


class Secoes(BaseModel):
    ordem: list[str] = Field(default_factory=list, max_length=10)
    ocultas: list[str] = Field(default_factory=list, max_length=10)
    equipe_no_topo: bool = True
    procedimentos_ocultos: list[UUID] = Field(default_factory=list, max_length=200)


class Conteudo(BaseModel):
    textos: Textos
    secoes: Secoes


class Legenda(BaseModel):
    legenda: str | None = Field(None, max_length=120)


class Ordem(BaseModel):
    ids: list[UUID] = Field(max_length=montagem.GALERIA_MAX)


def ver_conteudo(conn, clinic_id: UUID) -> dict:
    c = montagem.conteudo(conn, clinic_id)
    cfg = conn.execute("select settings from clinics where id = %s", (clinic_id,)).fetchone()[0] or {}
    d = montagem.dados(conn, clinic_id)
    ocultos = set(c["secoes"]["procedimentos_ocultos"])
    procs = conn.execute("select id, name from services where clinic_id = %s and active order by name", (clinic_id,)).fetchall()
    fotos = conn.execute("select id, legenda, (extract(epoch from created_at) * 1000)::bigint from site_photos "
                         "where clinic_id = %s order by ordem, created_at", (clinic_id,)).fetchall()
    return {
        **c,
        "nomes_secoes": montagem.SECOES,
        "padroes": {"titulo": d["nome"], "frase": d["frase"] if not c["textos"]["frase"] else None,
                    "sobre": cfg.get("sobre_clinica") or ""},
        "procedimentos": [{"id": str(i), "nome": n, "visivel": str(i) not in ocultos} for i, n in procs],
        "galeria": [{"id": str(i), "legenda": leg, "versao": v} for i, leg, v in fotos],
        "galeria_max": montagem.GALERIA_MAX,
    }


@painel.get("/conteudo", summary="Textos, seções, procedimentos no site e galeria")
def conteudo(clinic_id: UUID, conn=Depends(get_conn)):
    return ver_conteudo(conn, clinic_id)


@painel.put("/conteudo", summary="Salvar textos e seções do site")
def salvar_conteudo(clinic_id: UUID, body: Conteudo, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    validos = set(montagem.SECOES)
    ordem = [x for x in dict.fromkeys(body.secoes.ordem) if x in validos]
    existentes = {r[0] for r in conn.execute("select id from services where clinic_id = %s", (clinic_id,)).fetchall()}
    secoes = {"ordem": ordem, "ocultas": [x for x in set(body.secoes.ocultas) if x in validos],
              "equipe_no_topo": body.secoes.equipe_no_topo,
              "procedimentos_ocultos": [str(x) for x in body.secoes.procedimentos_ocultos if x in existentes]}
    textos = {k: v.strip() for k, v in body.textos.model_dump().items()}
    conn.execute(
        """insert into clinic_sites (clinic_id, textos, secoes) values (%s, %s, %s)
           on conflict (clinic_id) do update set textos = excluded.textos, secoes = excluded.secoes, updated_at = now()""",
        (clinic_id, Jsonb(textos), Jsonb(secoes)))
    return ver_conteudo(conn, clinic_id)


@painel.post("/galeria", status_code=201, summary="Enviar foto para a galeria (o corpo é a imagem: PNG, JPG ou WebP até 512 KB)")
async def enviar_foto(clinic_id: UUID, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    total = conn.execute("select count(*) from site_photos where clinic_id = %s", (clinic_id,)).fetchone()[0]
    if total >= montagem.GALERIA_MAX:
        raise AgendaError("DADOS_INVALIDOS", f"A galeria aceita até {montagem.GALERIA_MAX} fotos. Apague uma para enviar outra.")
    dados, mime = await aparencia.ler_imagem(request)
    conn.execute("insert into site_photos (clinic_id, mime, data, ordem) values (%s, %s, %s, %s)",
                 (clinic_id, mime, dados, total))
    return ver_conteudo(conn, clinic_id)


def _foto(conn, clinic_id: UUID, foto_id: UUID) -> None:
    if not conn.execute("select 1 from site_photos where clinic_id = %s and id = %s", (clinic_id, foto_id)).fetchone():
        raise AgendaError("DADOS_INVALIDOS", "Foto não encontrada.")


@painel.get("/galeria/{foto_id}", summary="Imagem da galeria (para o painel)")
def ver_foto(clinic_id: UUID, foto_id: UUID, conn=Depends(get_conn)):
    r = conn.execute("select mime, data from site_photos where clinic_id = %s and id = %s", (clinic_id, foto_id)).fetchone()
    if not r:
        return Response(status_code=404)
    return aparencia.resposta_imagem(r[0], bytes(r[1]))


@painel.patch("/galeria/{foto_id}", summary="Legenda da foto")
def legenda(clinic_id: UUID, foto_id: UUID, body: Legenda, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    _foto(conn, clinic_id, foto_id)
    conn.execute("update site_photos set legenda = %s where clinic_id = %s and id = %s",
                 ((body.legenda or "").strip() or None, clinic_id, foto_id))
    return ver_conteudo(conn, clinic_id)


@painel.put("/galeria-ordem", summary="Ordem das fotos da galeria")
def ordenar(clinic_id: UUID, body: Ordem, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    for i, fid in enumerate(body.ids):
        conn.execute("update site_photos set ordem = %s where clinic_id = %s and id = %s", (i, clinic_id, fid))
    return ver_conteudo(conn, clinic_id)


@painel.delete("/galeria/{foto_id}", summary="Apagar foto da galeria")
def apagar_foto(clinic_id: UUID, foto_id: UUID, request: Request, conn=Depends(get_conn)):
    exigir_admin_clinica(request, clinic_id)
    _foto(conn, clinic_id, foto_id)
    conn.execute("delete from site_photos where clinic_id = %s and id = %s", (clinic_id, foto_id))
    return ver_conteudo(conn, clinic_id)

