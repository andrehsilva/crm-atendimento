"""Etapa 11A — site de apresentação (D58, D61–D63, D65)."""

from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from app import configuracao_inicial as inicial
from app.main import app
from app.site import montagem
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401


def _slug(conn, clinica):
    return conn.execute("select slug from clinics where id = %s", (clinica.id,)).fetchone()[0]


def _publicar(conn, clinica, template="classico"):
    conn.execute("insert into clinic_sites (clinic_id, template, publicado) values (%s, %s, true) "
                 "on conflict (clinic_id) do update set template = excluded.template, publicado = true", (clinica.id, template))


def test_cada_layout_monta_com_os_dados_da_clinica(conn, clinica):
    conn.execute("update clinics set address = 'Rua A, 10 — Centro, São Paulo/SP', settings = %s where id = %s",
                 (Jsonb({"sobre_clinica": "Atendimento com hora marcada.", "segmento": "odontologia"}), clinica.id))
    for layout in montagem.LAYOUTS:
        html = montagem.desenhar(conn, clinica.id, layout)
        assert "Clínica Teste A" in html and "Limpeza" in html and "Dra. A" in html
        assert "https://wa.me/5511900000001?text=" in html and "agendar%20uma%20consulta" in html
        assert '"@type": "Dentist"' in html and "Atendimento com hora marcada." in html
        assert "/site/_estatico/fontes/" in html  # fonte servida pelo próprio servidor (sem Google Fonts)
        assert "<script>" not in html.replace('<script type="application/ld+json">', "")  # nenhum script que rode


def test_horarios_cortam_o_almoco_e_mostram_fechado(conn, clinica):
    h = {d["dia"]: d["faixas"] for d in montagem.dados(conn, clinica.id)["horarios"]}
    assert h["Segunda"] == "08:00–12:00 · 13:00–18:00" and h["Domingo"] is None


def test_preco_so_aparece_com_mostrar_precos(conn, clinica):
    conn.execute("update services set price_cents = 15000 where id = %s", (clinica.servico,))
    assert "R$ 150,00" not in montagem.desenhar(conn, clinica.id, "classico")
    conn.execute("update clinics set settings = settings || %s where id = %s", (Jsonb({"mostrar_precos": True}), clinica.id))
    assert "R$ 150,00" in montagem.desenhar(conn, clinica.id, "classico")


def test_texto_da_clinica_nunca_vira_codigo(conn, clinica):
    conn.execute("update clinics set name = %s, settings = %s where id = %s",
                 ('<script>alert(1)</script>Clínica', Jsonb({"sobre_clinica": '"><img src=x onerror=alert(1)>'}), clinica.id))
    html = montagem.desenhar(conn, clinica.id, "moderno")
    assert "<script>alert(1)" not in html and "<img src=x" not in html and "&lt;script&gt;" in html


def test_cor_escura_dos_links_e_legivel(conn):
    for cor in ("#b85c74", "#2f80c9", "#0f766e", "#c2410c"):
        from app import aparencia
        assert aparencia.contraste_com_branco(montagem.tons(cor)["escura"]) >= 4.5


def test_publico_so_mostra_site_publicado(cliente, conn, clinica):  # noqa: F811
    anon = TestClient(app)
    url = f"/site/{_slug(conn, clinica)}"
    assert anon.get(url).status_code == 404
    _publicar(conn, clinica, "acolhedor")
    r = anon.get(url)
    # 2 profissionais: a apresentação vira carrossel, com o script do próprio servidor
    assert r.status_code == 200 and "data-carrossel" in r.text and "Eu sou a Dra. A" in r.text
    assert '<script src="/site/_estatico/js/carrossel.js" defer></script>' in r.text
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert anon.get("/site/_estatico/js/carrossel.js").status_code == 200
    assert "default-src 'none'" in r.headers["content-security-policy"]
    conn.execute("update clinics set status = 'suspensa' where id = %s", (clinica.id,))
    assert anon.get(url).status_code == 404


def test_site_nao_mostra_dado_de_paciente(cliente, conn, clinica):  # noqa: F811
    conn.execute("insert into patients (clinic_id, phone, name) values (%s, '+5511955558888', 'Paciente Secreto')", (clinica.id,))
    _publicar(conn, clinica)
    r = TestClient(app).get(f"/site/{_slug(conn, clinica)}")
    assert "Paciente Secreto" not in r.text and "955558888" not in r.text


def test_publicar_so_admin_e_so_com_primeiros_passos(cliente, conn, clinica):  # noqa: F811
    rec, adm = _usuario(conn, clinic_id=clinica.id), _usuario(conn, clinic_id=clinica.id, papel="clinic_admin")
    base = f"/api/clinics/{clinica.id}/site"
    assert _como(cliente, rec).get(base).json()["publicado"] is False
    assert _como(cliente, rec).post(f"{base}/publicar", json={"publicado": True}).status_code == 403
    assert _como(cliente, rec).put(base, json={"template": "moderno"}).status_code == 403
    assert _como(cliente, adm).post(f"{base}/publicar", json={"publicado": True}).status_code == 422  # 10C não concluída
    conn.execute("update clinics set configurada_em = now() where id = %s", (clinica.id,))
    assert inicial.concluida(conn, clinica.id)
    assert _como(cliente, adm).put(base, json={"template": "moderno"}).json()["template"] == "moderno"
    assert _como(cliente, adm).post(f"{base}/publicar", json={"publicado": True}).json()["publicado"] is True
    prev = _como(cliente, rec).get(f"{base}/previa?layout=classico")
    assert prev.status_code == 200 and "noindex" in prev.text and "Prévia" in prev.text


def test_foto_da_profissional_aparece_no_site_e_some_se_inativa(cliente, conn, clinica):  # noqa: F811
    conn.execute("insert into professional_photos (professional_id, clinic_id, mime, data) values (%s, %s, 'image/png', %s)",
                 (clinica.prof_a, clinica.id, bytes([0x89]) + b"PNG-foto-de-teste"))
    conn.execute("update professionals set bio = 'Cuida do seu sorriso.' where id = %s", (clinica.prof_a,))
    d = montagem.dados(conn, clinica.id)
    assert d["destaque"]["nome"] == "Dra. A" and d["destaque"]["foto_url"]
    _publicar(conn, clinica)
    anon = TestClient(app)
    assert anon.get(d["destaque"]["foto_url"]).status_code == 200
    conn.execute("update professionals set active = false where id = %s", (clinica.prof_a,))
    assert anon.get(d["destaque"]["foto_url"]).status_code == 404


def test_fontes_so_as_da_lista(cliente):  # noqa: F811
    anon = TestClient(app)
    assert anon.get("/site/_estatico/fontes/fraunces.woff2").status_code == 200
    assert anon.get("/site/_estatico/fontes/..%2F..%2Fmontagem.py").status_code == 404


def test_horarios_agrupados():
    d = lambda n, f: {"dia": n, "faixas": f, "lista": [f] if f else []}  # noqa: E731
    g = montagem.agrupar_horarios([d("Segunda", "8"), d("Terça", "8"), d("Quarta", "8"), d("Quinta", "9"),
                                   d("Sexta", "9"), d("Sábado", None), d("Domingo", None)])
    assert [x["dias"] for x in g] == ["Segunda a quarta", "Quinta e sexta"]


def test_cor_de_cada_layout(cliente, conn, clinica):  # noqa: F811
    adm = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    base = f"/api/clinics/{clinica.id}/site"
    assert adm.put(f"{base}/cor", json={"layout": "moderno", "cor": "#fde68a"}).status_code == 422  # clara demais
    e = adm.put(f"{base}/cor", json={"layout": "moderno", "cor": "#0F766E"}).json()
    assert e["cores"]["moderno"] == "#0f766e" and e["cores"]["acolhedor"] is None
    assert "--cor: #0f766e" in montagem.desenhar(conn, clinica.id, "moderno")
    assert "--cor: #0f766e" not in montagem.desenhar(conn, clinica.id, "acolhedor")  # só aquele layout
    assert "--cor: #7c3aed" in adm.get(f"{base}/previa?layout=moderno&cor=%237c3aed").text  # prévia antes de salvar
    assert "--cor: #0f766e" in adm.get(f"{base}/previa?layout=moderno&cor=javascript:x").text  # cor inválida é ignorada
    assert adm.put(f"{base}/cor", json={"layout": "moderno", "cor": None}).json()["cores"]["moderno"] is None
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id))
    assert rec.put(f"{base}/cor", json={"layout": "moderno", "cor": "#0f766e"}).status_code == 403


# ---------------------------------------------------------------------------
# 11B — editor completo
# ---------------------------------------------------------------------------
PNG = bytes([0x89]) + b"PNG\r\n\x1a\n" + b"0" * 64


def _adm(cliente, conn, clinica):  # noqa: F811
    return _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))


def test_textos_secoes_e_ordem(cliente, conn, clinica):  # noqa: F811
    adm = _adm(cliente, conn, clinica)
    base = f"/api/clinics/{clinica.id}/site"
    c = adm.get(f"{base}/conteudo").json()
    assert c["secoes"]["ordem"] == ["sobre", "procedimentos", "galeria", "visita"] and c["textos"]["titulo"] == ""
    corpo = {"textos": {"titulo": "Consultório da Dra. A", "frase": "Sorrisos com calma.", "sobre": "Somos uma equipe pequena."},
             "secoes": {"ordem": ["visita", "sobre", "procedimentos", "galeria", "inventada"], "ocultas": ["procedimentos"],
                        "equipe_no_topo": False, "procedimentos_ocultos": []}}
    r = adm.put(f"{base}/conteudo", json=corpo).json()
    assert r["secoes"]["ordem"][:2] == ["visita", "sobre"] and "inventada" not in r["secoes"]["ordem"]
    html = montagem.desenhar(conn, clinica.id, "acolhedor")
    assert "Consultório da Dra. A" in html and "Sorrisos com calma." in html and "Somos uma equipe pequena." in html
    assert "Como podemos ajudar" not in html  # seção desligada
    corpo_html = html[html.index("<body>"):]
    assert corpo_html.index("Quando atendemos") < corpo_html.index("Somos uma equipe pequena.")  # ordem escolhida
    assert "data-carrossel" not in html and "Eu sou" not in html  # equipe fora do topo
    rec = _como(cliente, _usuario(conn, clinic_id=clinica.id))
    assert rec.put(f"{base}/conteudo", json=corpo).status_code == 403


def test_esconder_procedimento_do_site(cliente, conn, clinica):  # noqa: F811
    adm = _adm(cliente, conn, clinica)
    corpo = {"textos": {}, "secoes": {"procedimentos_ocultos": [str(clinica.urgencia)]}}
    r = adm.put(f"/api/clinics/{clinica.id}/site/conteudo", json=corpo).json()
    assert {p["nome"]: p["visivel"] for p in r["procedimentos"]} == {"Limpeza": True, "Urgência": False}
    html = montagem.desenhar(conn, clinica.id, "moderno")
    assert "Limpeza" in html and "Urgência" not in html


def test_galeria_envia_legenda_ordem_limite_e_apaga(cliente, conn, clinica):  # noqa: F811
    adm = _adm(cliente, conn, clinica)
    base = f"/api/clinics/{clinica.id}/site"
    for _ in range(2):
        r = adm.post(f"{base}/galeria", content=PNG, headers={"Content-Type": "image/png"})
        assert r.status_code == 201, r.text
    fotos = r.json()["galeria"]
    a, b = fotos[0]["id"], fotos[1]["id"]
    assert adm.patch(f"{base}/galeria/{a}", json={"legenda": "Sala de espera"}).json()["galeria"][0]["legenda"] == "Sala de espera"
    assert [f["id"] for f in adm.put(f"{base}/galeria-ordem", json={"ids": [b, a]}).json()["galeria"]] == [b, a]
    html = montagem.desenhar(conn, clinica.id, "classico")
    assert "Sala de espera" in html and f"/galeria/{b}" in html
    _publicar(conn, clinica)
    assert TestClient(app).get(f"/site/{_slug(conn, clinica)}/galeria/{a}").status_code == 200
    conn.execute("update site_photos set ordem = 0 where clinic_id = %s", (clinica.id,))
    for _ in range(montagem.GALERIA_MAX - 2):
        adm.post(f"{base}/galeria", content=PNG, headers={"Content-Type": "image/png"})
    assert adm.post(f"{base}/galeria", content=PNG, headers={"Content-Type": "image/png"}).status_code == 422  # limite
    assert len(adm.delete(f"{base}/galeria/{a}").json()["galeria"]) == montagem.GALERIA_MAX - 1


def test_sitemap_so_com_sites_publicados(cliente, conn, clinica, outra_clinica):  # noqa: F811
    _publicar(conn, clinica)
    xml = TestClient(app).get("/site/sitemap.xml").text
    assert f"/{_slug(conn, clinica)}</loc>" in xml and f"/{_slug(conn, outra_clinica)}</loc>" not in xml
