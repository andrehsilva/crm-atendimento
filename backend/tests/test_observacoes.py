"""Etapa 9C — observações do cliente em histórico (D48) e pasta do Google Drive (D49)."""

from tests.test_acesso import _como, _usuario, cliente  # noqa: F401


def _paciente(conn, clinica, telefone="+5511955553333"):
    return conn.execute("insert into patients (clinic_id, phone, name) values (%s, %s, 'Bia') returning id",
                        (clinica.id, telefone)).fetchone()[0]


def _base(clinica, pid):
    return f"/api/clinics/{clinica.id}/patients/{pid}"


def test_historico_com_data_autor_e_mais_recente_em_cima(cliente, conn, clinica):  # noqa: F811
    pid = _paciente(conn, clinica)
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id))
    assert c.post(f"{_base(clinica, pid)}/observacoes", json={"texto": "Primeira **nota**"}).status_code == 201
    r = c.post(f"{_base(clinica, pid)}/observacoes", json={"texto": "  Segunda  "})
    notas = r.json()["notas"]
    assert [n["texto"] for n in notas] == ["Segunda", "Primeira **nota**"]
    assert notas[0]["autor"] and notas[0]["criado_em"] and notas[0]["pode_editar"] and notas[0]["editado_em"] is None
    lista = c.get(f"/api/clinics/{clinica.id}/patients").json()
    assert next(p for p in lista if p["id"] == str(pid))["notas"] == 2


def test_observacao_vazia_e_recusada(cliente, conn, clinica):  # noqa: F811
    pid = _paciente(conn, clinica)
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id))
    assert c.post(f"{_base(clinica, pid)}/observacoes", json={"texto": "   "}).status_code == 422


def test_so_o_autor_corrige_e_o_admin_apaga_qualquer_uma(cliente, conn, clinica):  # noqa: F811
    pid = _paciente(conn, clinica)
    autor, colega = _usuario(conn, clinic_id=clinica.id), _usuario(conn, clinic_id=clinica.id)
    admin = _usuario(conn, clinic_id=clinica.id, papel="clinic_admin")
    nid = _como(cliente, autor).post(f"{_base(clinica, pid)}/observacoes", json={"texto": "Alergia a dipirona"}).json()["notas"][0]["id"]
    url = f"{_base(clinica, pid)}/observacoes/{nid}"

    c = _como(cliente, colega)
    nota = c.get(f"{_base(clinica, pid)}/observacoes").json()["notas"][0]
    assert not nota["pode_editar"] and not nota["pode_apagar"]
    assert c.patch(url, json={"texto": "mudei"}).status_code == 403
    assert c.delete(url).status_code == 403

    r = _como(cliente, autor).patch(url, json={"texto": "Alergia a dipirona e ibuprofeno"})
    assert r.status_code == 200 and r.json()["notas"][0]["texto"].endswith("ibuprofeno")

    c = _como(cliente, admin)
    assert c.patch(url, json={"texto": "admin não corrige texto dos outros"}).status_code == 403
    assert c.delete(url).json()["notas"] == []


def test_link_do_drive_so_aceita_google_drive(cliente, conn, clinica):  # noqa: F811
    pid = _paciente(conn, clinica)
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id))
    url = f"{_base(clinica, pid)}/drive"
    pasta = "https://drive.google.com/drive/folders/1AbC-dEf_123"
    assert c.put(url, json={"url": pasta}).json()["drive_url"] == pasta
    for ruim in ("http://drive.google.com/x", "https://drive.google.com.golpe.com/x", "javascript:alert(1)",
                 "https://example.com/drive.google.com/"):
        assert c.put(url, json={"url": ruim}).status_code == 422, ruim
    assert c.put(url, json={"url": ""}).json()["drive_url"] is None


def test_nota_de_cliente_de_outra_clinica_nao_passa(cliente, conn, clinica, outra_clinica):  # noqa: F811
    pid = _paciente(conn, outra_clinica)
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    assert c.post(f"{_base(clinica, pid)}/observacoes", json={"texto": "x"}).status_code == 422
    assert c.get(f"{_base(clinica, pid)}/observacoes").status_code == 422
    assert c.put(f"{_base(clinica, pid)}/drive", json={"url": "https://drive.google.com/x"}).status_code == 422
