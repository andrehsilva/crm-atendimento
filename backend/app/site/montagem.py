"""Junta os dados públicos da clínica e desenha o site com o layout escolhido (Jinja2, com escape automático)."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape
from psycopg.rows import dict_row

from app import aparencia, segmentos
from app.config import get_settings

# O id "classico" continua no banco; o layout dele foi refeito como "Elegante" (pedido do usuário, 20/11/2026).
LAYOUTS = {
    "classico": ("Elegante", "Foto grande ocupando metade da tela, como capa de revista, e textos sóbrios ao lado."),
    "moderno": ("Moderno", "Faixa forte na cor escolhida, nome enorme, semana em colunas e procedimentos em linhas."),
    "acolhedor": ("Acolhedor", "Fundo suave, foto em círculo e a profissional se apresentando, como numa conversa."),
}
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
FONTES = {"fraunces.woff2", "bricolage.woff2", "nunito.woff2"}
SCRIPTS = {"carrossel.js"}
ESTATICO = Path(__file__).parent / "estatico"
SCHEMA = {"odontologia": "Dentist", "medicina": "MedicalClinic", "fisioterapia": "MedicalClinic",
          "psicologia": "MedicalClinic", "estetica": "HealthAndBeautyBusiness", "outro": "LocalBusiness"}

_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

# A página não roda script nenhum: só estilos próprios e imagens do próprio servidor.
# Só o script do carrossel, servido pelo próprio servidor (script-src 'self'); nada de script embutido na página.
CSP = ("default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; font-src 'self'; script-src 'self'; base-uri 'none'; "
       "form-action 'none'; frame-ancestors 'self'")


# ---------------------------------------------------------------------------
# Cores: a cor da clínica e variações que continuam legíveis
# ---------------------------------------------------------------------------
def _rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(x))) for x in (r, g, b)))


def _misturar(cor: str, com: str, t: float) -> str:
    a, b = _rgb(cor), _rgb(com)
    return _hex(*(x + (y - x) * t for x, y in zip(a, b)))


def tons(cor: str) -> dict:
    """cor = botões e faixas (texto branco grande, contraste ≥ 3:1 garantido pela 9B);
    escura = links e destaques sobre fundo claro (contraste ≥ 4,5:1); suave = fundos."""
    escura, t = cor, 0.0
    while aparencia.contraste_com_branco(escura) < 4.5 and t < 1:
        t += 0.05
        escura = _misturar(cor, "#000000", t)
    return {"cor": cor, "escura": escura, "suave": _misturar(cor, "#ffffff", 0.9), "media": _misturar(cor, "#ffffff", 0.75)}


# ---------------------------------------------------------------------------
# Dados públicos da clínica
# ---------------------------------------------------------------------------
def _horarios(conn, clinic_id: UUID) -> list[dict]:
    horas = conn.execute("select weekday, start_time, end_time from clinic_hours where clinic_id = %s order by start_time",
                         (clinic_id,)).fetchall()
    pausas = conn.execute("select weekday, start_time, end_time from clinic_breaks where clinic_id = %s", (clinic_id,)).fetchall()
    dias = []
    for wd, nome in enumerate(DIAS):
        faixas = []
        for _, ini, fim in (h for h in horas if h[0] == wd):
            cortes = sorted((p[1], p[2]) for p in pausas if p[0] == wd and ini < p[1] < fim)
            atual = ini
            for p_ini, p_fim in cortes:
                faixas.append((atual, p_ini))
                atual = p_fim
            faixas.append((atual, fim))
        texto = " · ".join(f"{a:%H:%M}–{b:%H:%M}" for a, b in faixas)
        dias.append({"dia": nome, "curto": nome[:3], "faixas": texto or None, "lista": [f"{a:%H:%M}–{b:%H:%M}" for a, b in faixas]})
    return dias


def agrupar_horarios(dias: list[dict]) -> list[dict]:
    """Junta dias seguidos com o mesmo horário: "Segunda a sexta · 08:00–12:00 · 13:00–18:00"."""
    grupos: list[dict] = []
    for d in dias:
        if not d["faixas"]:
            continue
        if grupos and grupos[-1]["faixas"] == d["faixas"] and grupos[-1]["fim_idx"] == DIAS.index(d["dia"]) - 1:
            grupos[-1]["fim"], grupos[-1]["fim_idx"] = d["dia"], DIAS.index(d["dia"])
        else:
            grupos.append({"ini": d["dia"], "fim": d["dia"], "fim_idx": DIAS.index(d["dia"]), "faixas": d["faixas"], "lista": d["lista"]})
    for g in grupos:
        g["dias"] = g["ini"] if g["ini"] == g["fim"] else (
            f"{g['ini']} e {g['fim'].lower()}" if DIAS.index(g["fim"]) - DIAS.index(g["ini"]) == 1
            else f"{g['ini']} a {g['fim'].lower()}")
    return grupos


def _preco(cents: int | None) -> str | None:
    if not cents:
        return None
    return "R$ " + f"{cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _duracao(minutos: int) -> str:
    h, m = divmod(minutos, 60)
    return f"{h} h {m:02d} min" if h and m else (f"{h} h" if h else f"{m} min")


def _primeiro_nome(nome: str) -> str:
    """"Dra. Ana Lima" → "Dra. Ana" (como ela se apresenta no site)."""
    partes = nome.split()
    return " ".join(partes[:2]) if partes and partes[0].rstrip(".").lower() in ("dr", "dra") else (partes[0] if partes else nome)


def _cidade(endereco: str | None) -> str | None:
    """"Rua das Flores, 123 — Centro, São Paulo/SP" → "São Paulo"."""
    if not endereco:
        return None
    fim = endereco.split("—")[-1].split(",")[-1].strip()
    return fim.split("/")[0].strip() or None


def _telefone_bonito(e164: str) -> str:
    d = "".join(c for c in e164 if c.isdigit())
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
        return f"({d[:2]}) {d[2:-4]}-{d[-4:]}"
    return e164


def dados(conn, clinic_id: UUID, cor: str | None = None) -> dict:
    """`cor` = cor escolhida para o layout do site (vazio = cor da clínica)."""
    cur = conn.cursor(row_factory=dict_row)
    c = cur.execute("select id, name, slug, phone, address, timezone, settings from clinics where id = %s", (clinic_id,)).fetchone()
    cfg = c["settings"] or {}
    seg = segmentos.segmento_de(cfg)
    termos = segmentos.termos(cfg)
    zap = conn.execute("select phone from whatsapp_instances where clinic_id = %s and enabled", (clinic_id,)).fetchone()
    fone = (zap[0] if zap and zap[0] else None) or c["phone"]
    mostrar_precos = bool(cfg.get("mostrar_precos"))
    procedimentos = [
        {"nome": s["name"], "descricao": s["description"], "duracao": _duracao(s["duration_min"]),
         "preco": _preco(s["price_cents"]) if mostrar_precos else None}
        for s in cur.execute("select name, description, duration_min, price_cents from services "
                             "where clinic_id = %s and active order by name", (clinic_id,)).fetchall()
    ]
    equipe = [
        {"nome": p["name"], "especialidade": p["specialty"], "bio": p["bio"],
         "primeiro_nome": _primeiro_nome(p["name"]),
         "iniciais": "".join(x[0] for x in [w for w in p["name"].replace(".", " ").split() if w[0].isupper()][-2:]).upper(),
         "foto_url": f"/site/{c['slug']}/equipe/{p['id']}/foto?v={p['foto']}" if p["foto"] else None}
        for p in cur.execute(
            """select p.id, p.name, p.specialty, p.bio,
                      (select (extract(epoch from f.updated_at) * 1000)::bigint from professional_photos f
                         where f.professional_id = p.id) as foto
               from professionals p where p.clinic_id = %s and p.active order by p.name""", (clinic_id,)).fetchall()
    ]
    # Em destaque no topo do site: a 1ª pessoa com foto (num consultório pequeno, a dona) — senão a 1ª da lista
    destaque = next((p for p in equipe if p["foto_url"]), equipe[0] if equipe else None)
    logo = aparencia.versao_da_logo(conn, clinic_id)
    s = get_settings()
    nome = c["name"]
    atend = termos["atendimento"]
    cidade = _cidade(c["address"])
    texto_zap = f"Olá! Vim pelo site da {nome} e gostaria de agendar um{'a' if termos.get('genero') == 'f' else ''} {atend}."
    return {
        "nome": nome, "slug": c["slug"], "endereco": c["address"], "sobre": cfg.get("sobre_clinica"), "cidade": cidade,
        # sem "Sobre" preenchido: uma frase neutra (sem promessas — regras de publicidade dos conselhos, D63)
        "apresentacao": cfg.get("sobre_clinica") or (
            f"{seg.tipo_negocio[0].upper()}{seg.tipo_negocio[1:]}{' em ' + cidade if cidade else ''}. "
            f"{termos['atendimentos'][0].upper()}{termos['atendimentos'][1:]} com hora marcada e agendamento pelo WhatsApp."),
        "segmento": seg.nome, "tipo_negocio": seg.tipo_negocio, "termos": termos,
        "assistente": cfg.get("nome_assistente") or "Ísis",
        "chamada": f"Agende {'sua' if termos.get('genero') == 'f' else 'seu'} {atend} pelo WhatsApp.",
        "tons": tons(cor or aparencia.cor_da_clinica(cfg)),
        "logo_url": f"/site/{c['slug']}/logo?v={logo}" if logo else None,
        "iniciais": nome.strip()[:1].upper(),
        "telefone": _telefone_bonito(fone),
        "whatsapp_url": f"https://wa.me/{''.join(ch for ch in fone if ch.isdigit())}?text={quote(texto_zap)}",
        "mapa_url": f"https://www.google.com/maps/search/?api=1&query={quote(c['address'])}" if c["address"] else None,
        "horarios": (horarios := _horarios(conn, clinic_id)),
        "horarios_agrupados": agrupar_horarios(horarios),
        "texto_zap": texto_zap,
        "procedimentos": procedimentos,
        "equipe": equipe,
        "destaque": destaque,
        "hoje": datetime.now(ZoneInfo(c["timezone"])).weekday(),
        "painel_url": s.frontend_origin.rstrip("/"),
        "url": f"{s.site_base_url.rstrip('/')}/{c['slug']}",
        # imagem da prévia do link (WhatsApp, redes): endereço completo da logo
        "imagem_url": f"{s.site_base_url.rstrip('/')}/{c['slug']}/logo?v={logo}" if logo else None,
        "plataforma": s.app_name,
        "schema_tipo": SCHEMA.get(seg.codigo, "LocalBusiness"),
    }


def _json_ld(d: dict) -> str:
    """Dados estruturados para o Google. Escapa "<" para não fechar a tag <script> por engano."""
    ld = {"@context": "https://schema.org", "@type": d["schema_tipo"], "name": d["nome"], "url": d["url"],
          "telephone": d["telefone"]}
    if d["endereco"]:
        ld["address"] = d["endereco"]
    if d["sobre"]:
        ld["description"] = d["sobre"]
    return json.dumps(ld, ensure_ascii=False).replace("<", "\\u003c")


def cor_do_layout(conn, clinic_id: UUID, layout: str) -> str | None:
    r = conn.execute("select cores ->> %s from clinic_sites where clinic_id = %s", (layout, clinic_id)).fetchone()
    cor = r[0] if r else None
    return cor if cor and aparencia.COR_RE.match(cor) and aparencia.contraste_com_branco(cor) >= aparencia.CONTRASTE_MINIMO else None


def desenhar(conn, clinic_id: UUID, layout: str, previa: bool = False, cor: str | None = None) -> str:
    """`cor`: só a prévia passa uma cor ainda não salva; o site publicado usa a cor salva do layout."""
    layout = layout if layout in LAYOUTS else "classico"
    d = dados(conn, clinic_id, cor or cor_do_layout(conn, clinic_id, layout))
    # Com mais de uma pessoa, quem tem foto aparece primeiro no carrossel
    d["carrossel"] = sorted(d["equipe"], key=lambda p: p["foto_url"] is None)
    return _env.get_template(f"{layout}.html").render(s=d, json_ld=_json_ld(d), previa=previa)


def pagina_nao_encontrada() -> str:
    return _env.get_template("nao_encontrado.html").render(plataforma=get_settings().app_name)
