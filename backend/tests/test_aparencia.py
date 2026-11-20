"""Etapa 9B — cor principal e logo de cada clínica (D40)."""

from app import aparencia
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401
from tests.test_admin import admin  # noqa: F401

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def _url(clinica, resto):
    return f"/api/clinics/{clinica.id}/config/{resto}"


# ---------------------------------------------------------------------------
# Cor
# ---------------------------------------------------------------------------
def test_cor_padrao_e_contraste():
    assert aparencia.cor_da_clinica({}) == aparencia.COR_PADRAO
    assert aparencia.cor_da_clinica({"cor": "lixo"}) == aparencia.COR_PADRAO
    assert aparencia.contraste_com_branco("#000000") == 21
    assert aparencia.contraste_com_branco(aparencia.COR_PADRAO) >= aparencia.CONTRASTE_MINIMO


def test_salvar_cor_e_voltar_ao_padrao(admin, clinica):  # noqa: F811
    r = admin.put(_url(clinica, "aparencia"), json={"cor": "#1F6FEB"})
    assert r.status_code == 200, r.text
    assert r.json()["cor"] == "#1f6feb"
    assert admin.get(f"/api/clinics/{clinica.id}").json()["cor"] == "#1f6feb"
    assert admin.put(_url(clinica, "aparencia"), json={"cor": None}).json()["cor"] == aparencia.COR_PADRAO


def test_cor_clara_demais_ou_invalida_e_recusada(admin, clinica):  # noqa: F811
    r = admin.put(_url(clinica, "aparencia"), json={"cor": "#FFEE58"})  # amarelo claro
    assert r.status_code == 422 and "clara demais" in r.json()["mensagem"]
    assert admin.put(_url(clinica, "aparencia"), json={"cor": "azul"}).status_code == 422


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------
def test_enviar_trocar_e_remover_logo(admin, clinica):  # noqa: F811
    r = admin.put(_url(clinica, "logo"), content=PNG, headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    v1 = r.json()["logo_versao"]
    img = admin.get(f"/api/clinics/{clinica.id}/logo?v={v1}")
    assert img.status_code == 200 and img.content == PNG and img.headers["content-type"] == "image/png"
    assert img.headers["x-content-type-options"] == "nosniff"

    # o tipo vem dos bytes, não do cabeçalho que o navegador mandou
    r = admin.put(_url(clinica, "logo"), content=WEBP, headers={"Content-Type": "image/png"})
    assert r.status_code == 200 and admin.get(f"/api/clinics/{clinica.id}/logo").headers["content-type"] == "image/webp"
    assert admin.get(f"/api/clinics/{clinica.id}").json()["logo_versao"] is not None

    assert admin.delete(_url(clinica, "logo")).json()["logo_versao"] is None
    assert admin.get(f"/api/clinics/{clinica.id}/logo").status_code == 404


def test_logo_svg_ou_grande_demais_e_recusada(admin, clinica):  # noqa: F811
    r = admin.put(_url(clinica, "logo"), content=SVG, headers={"Content-Type": "image/svg+xml"})
    assert r.status_code == 422 and r.json()["codigo"] == "LOGO_INVALIDA"
    grande = PNG + b"\x00" * aparencia.LOGO_MAX
    r = admin.put(_url(clinica, "logo"), content=grande, headers={"Content-Type": "image/png"})
    assert r.status_code == 413 and r.json()["codigo"] == "LOGO_GRANDE"


def test_recepcao_ve_mas_nao_muda_a_aparencia(cliente, conn, clinica):  # noqa: F811
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    assert c.get(_url(clinica, "aparencia")).status_code == 200
    assert c.put(_url(clinica, "aparencia"), json={"cor": "#1f6feb"}).status_code == 403
    assert c.put(_url(clinica, "logo"), content=PNG, headers={"Content-Type": "image/png"}).status_code == 403
    assert c.delete(_url(clinica, "logo")).status_code == 403


# ---------------------------------------------------------------------------
# Foto de perfil
# ---------------------------------------------------------------------------
def test_usuario_envia_e_remove_a_propria_foto(cliente, conn, clinica):  # noqa: F811
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    assert c.get("/api/auth/me").json()["foto_versao"] is None
    r = c.put("/api/auth/foto", content=PNG, headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    assert r.json()["foto_versao"] is not None and c.get("/api/auth/me").json()["foto_versao"] == r.json()["foto_versao"]
    assert c.get("/api/auth/foto").content == PNG
    assert c.put("/api/auth/foto", content=SVG, headers={"Content-Type": "image/svg+xml"}).status_code == 422
    assert c.delete("/api/auth/foto").json()["foto_versao"] is None
    assert c.get("/api/auth/foto").status_code == 404


def test_foto_e_so_do_proprio_usuario(cliente, conn, clinica):  # noqa: F811
    a = _usuario(conn, clinic_id=clinica.id)
    _como(cliente, a).put("/api/auth/foto", content=PNG, headers={"Content-Type": "image/png"})
    assert _como(cliente, _usuario(conn, clinic_id=clinica.id)).get("/api/auth/foto").status_code == 404
    cliente.cookies.clear()
    assert cliente.get("/api/auth/foto").status_code == 401


# ---------------------------------------------------------------------------
# Foto do lead/cliente
# ---------------------------------------------------------------------------
def _paciente(conn, clinica, telefone="+5511966664444"):
    return conn.execute("insert into patients (clinic_id, phone, name) values (%s, %s, 'Lia') returning id",
                        (clinica.id, telefone)).fetchone()[0]


def test_recepcao_poe_foto_no_lead(cliente, conn, clinica):  # noqa: F811
    pid = _paciente(conn, clinica)
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="reception"))
    base = f"/api/clinics/{clinica.id}/patients/{pid}/foto"
    r = c.put(base, content=PNG, headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    assert r.json()["foto_versao"]
    assert c.get(base).content == PNG
    lista = c.get(f"/api/clinics/{clinica.id}/patients").json()
    assert next(p for p in lista if p["id"] == str(pid))["foto_versao"] == r.json()["foto_versao"]
    cards = c.get(f"/api/clinics/{clinica.id}/kanban").json()["cards"]
    assert next(x for x in cards if x["id"] == str(pid))["foto_versao"]
    assert c.delete(base).json()["foto_versao"] is None and c.get(base).status_code == 404


def test_foto_de_lead_de_outra_clinica_nao_passa(cliente, conn, clinica, outra_clinica):  # noqa: F811
    pid = _paciente(conn, outra_clinica)
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    # paciente da clínica B pelo caminho da clínica A: não encontrado
    r = c.put(f"/api/clinics/{clinica.id}/patients/{pid}/foto", content=PNG, headers={"Content-Type": "image/png"})
    assert r.status_code == 422
    assert conn.execute("select count(*) from patient_photos where patient_id = %s", (pid,)).fetchone()[0] == 0


def test_logo_da_tela_de_entrar_e_publica_e_so_a_imagem(cliente, conn, clinica):  # noqa: F811
    from fastapi.testclient import TestClient
    from app.main import app

    anonimo = TestClient(app)
    assert anonimo.get(f"/api/auth/marca/{clinica.id}/logo").status_code == 404  # sem logo
    assert anonimo.get(f"/api/clinics/{clinica.id}/logo").status_code == 401  # a rota do painel continua fechada
