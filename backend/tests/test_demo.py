"""D56 — "Reiniciar demonstração" troca só os dados de teste; a clínica e as configurações ficam."""

from psycopg.types.json import Jsonb

from app import demo
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401


def _conta(conn, tabela, cid):
    return conn.execute(f"select count(*) from {tabela} where clinic_id = %s", (cid,)).fetchone()[0]  # noqa: S608


def test_reiniciar_apaga_so_dados_de_teste(conn, clinica):
    cid = clinica.id
    conn.execute("update clinics set name = 'Clínica Rodrigues', settings = %s where id = %s",
                 (Jsonb({"nome_assistente": "Margareth", "cor": "#c2410c"}), cid))
    conn.execute("insert into clinic_logos (clinic_id, mime, data) values (%s, 'image/png', %s)", (cid, b"\x89PNG"))
    conn.execute("update clinic_ai set usa_plataforma = true where clinic_id = %s", (cid,))
    # dados de teste antigos: um cliente com conversa e observação
    pid = conn.execute("insert into patients (clinic_id, phone, name) values (%s, '+5511955550001', 'Antigo') returning id",
                       (cid,)).fetchone()[0]
    conn.execute("insert into patient_notes (clinic_id, patient_id, author_name, body) values (%s, %s, 'x', 'nota')", (cid, pid))
    demo.criar_exemplos(conn, cid)
    profs_antes = _conta(conn, "professionals", cid)

    demo.limpar_dados_de_teste(conn, cid)
    for tabela in demo.TABELAS_DE_TESTE:
        assert _conta(conn, tabela, cid) == 0, tabela
    criadas = demo.criar_exemplos(conn, cid)

    nome, cfg = conn.execute("select name, settings from clinics where id = %s", (cid,)).fetchone()
    assert nome == "Clínica Rodrigues" and cfg["nome_assistente"] == "Margareth" and cfg["cor"] == "#c2410c"
    assert _conta(conn, "clinic_logos", cid) == 1 and _conta(conn, "clinic_ai", cid) == 1
    assert _conta(conn, "professionals", cid) == profs_antes and _conta(conn, "clinic_hours", cid) == 5
    assert criadas == 3 and _conta(conn, "appointments", cid) == 3
    assert not conn.execute("select 1 from patients where clinic_id = %s and name = 'Antigo'", (cid,)).fetchone()
    assert conn.execute("select 1 from patients where clinic_id = %s and name = 'Pedro Alves'", (cid,)).fetchone()


def test_exemplos_usam_a_equipe_da_propria_clinica_e_pulam_o_que_nao_cabe(conn, clinica):
    # só a Dra. A ativa: tudo vai para ela; procedimento que a IA não marca (Urgência) não é usado
    conn.execute("update professionals set active = false where id = %s", (clinica.prof_b,))
    demo.criar_exemplos(conn, clinica.id)
    linhas = conn.execute("select professional_id, service_id from appointments where clinic_id = %s", (clinica.id,)).fetchall()
    assert linhas and all(p == clinica.prof_a and s == clinica.servico for p, s in linhas)


def test_sem_equipe_nao_quebra(conn, clinica):
    conn.execute("update professionals set active = false where clinic_id = %s", (clinica.id,))
    assert demo.criar_exemplos(conn, clinica.id) == 0


def test_so_uma_clinica_de_apresentacao_e_ela_vem_primeiro(cliente, conn, clinica, outra_clinica):  # noqa: F811
    c = _como(cliente, _usuario(conn, super_admin=True))
    for alvo in (clinica.id, outra_clinica.id):
        assert c.patch(f"/api/admin/clinicas/{alvo}", json={"apresentacao": True}).status_code == 200
    assert conn.execute("select id from clinics where apresentacao").fetchall() == [(outra_clinica.id,)]
    assert c.get("/api/clinics").json()[0]["id"] == str(outra_clinica.id)
    admin_clinica = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin"))
    assert admin_clinica.patch(f"/api/admin/clinicas/{clinica.id}", json={"apresentacao": True}).status_code == 403
