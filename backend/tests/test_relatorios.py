"""Etapa 15A — relatórios em Excel (D73–D75)."""

from datetime import date
from io import BytesIO

from openpyxl import load_workbook

from app import relatorios as R
from tests.test_acesso import _como, _usuario, cliente  # noqa: F401


def _consulta(conn, clinica, quando, status, nome="Ana", tel="+5511955550001"):
    pid = conn.execute("""insert into patients (clinic_id, phone, name) values (%s, %s, %s)
                          on conflict (clinic_id, phone) do update set name = excluded.name returning id""",
                       (clinica.id, tel, nome)).fetchone()[0]
    conn.execute("""insert into appointments (clinic_id, patient_id, professional_id, service_id, starts_at, ends_at, status)
                    values (%s, %s, %s, %s, %s::timestamptz, %s::timestamptz + interval '1 hour', %s)""",
                 (clinica.id, pid, clinica.prof_a, clinica.servico, quando, quando, status))


def _abrir(dados):
    return load_workbook(BytesIO(dados))


def test_formula_vira_texto():
    assert R.seguro("=HYPERLINK(\"x\")") == "'=HYPERLINK(\"x\")" and R.seguro("Ana") == "Ana" and R.seguro(10) == 10


def test_recall_so_quem_sumiu_e_nao_tem_nada_marcado(conn, clinica):
    conn.execute("update services set price_cents = 20000 where id = %s", (clinica.servico,))
    _consulta(conn, clinica, "2025-01-10 10:00-03", "realizada", "Sumida", "+5511955550001")
    _consulta(conn, clinica, "2025-01-10 11:00-03", "realizada", "Volta logo", "+5511955550002")
    _consulta(conn, clinica, "2099-01-10 11:00-03", "agendada", "Volta logo", "+5511955550002")
    wb = _abrir(R.gerar(conn, clinica.id, "recall", de=date.today(), ate=date.today(), prof=None, meses=6)[0])
    nomes = [r[0] for r in wb["Chamar de volta"].iter_rows(min_row=2, values_only=True)]
    assert nomes == ["Sumida"] and wb.sheetnames[0] == "Sobre"


def test_producao_e_faltas_contam_certo(conn, clinica):
    conn.execute("update services set price_cents = 15000 where id = %s", (clinica.servico,))
    for st in ("realizada", "realizada", "faltou", "cancelada"):
        _consulta(conn, clinica, "2026-03-02 09:00-03", st)  # segunda-feira
    p = _abrir(R.gerar(conn, clinica.id, "producao", de=date(2026, 3, 1), ate=date(2026, 3, 31), prof=None, meses=6)[0])
    linha = next(p["Por profissional"].iter_rows(min_row=2, values_only=True))
    assert linha[:4] == ("Dra. A", 2, 1, 1) and abs(linha[4] - 2 / 3) < 0.01 and linha[5] == 300
    f = _abrir(R.gerar(conn, clinica.id, "faltas", de=date(2026, 3, 1), ate=date(2026, 3, 31), prof=None, meses=6)[0])
    assert len(list(f["Lista"].iter_rows(min_row=2))) == 2
    assert next(f["Por dia da semana"].iter_rows(min_row=2, values_only=True))[:3] == ("Segunda", 4, 1)


def test_atendimentos_filtra_profissional_e_periodo(conn, clinica):
    _consulta(conn, clinica, "2026-03-02 09:00-03", "realizada")
    _consulta(conn, clinica, "2026-05-02 09:00-03", "realizada")
    a = _abrir(R.gerar(conn, clinica.id, "atendimentos", de=date(2026, 3, 1), ate=date(2026, 3, 31), prof=clinica.prof_b, meses=6)[0])
    assert len(list(a["Atendimentos"].iter_rows(min_row=2))) == 0
    a = _abrir(R.gerar(conn, clinica.id, "atendimentos", de=date(2026, 3, 1), ate=date(2026, 3, 31), prof=clinica.prof_a, meses=6)[0])
    assert len(list(a["Atendimentos"].iter_rows(min_row=2))) == 1


def test_so_admin_baixa_e_fica_registrado(cliente, conn, clinica, outra_clinica):  # noqa: F811
    url = f"/api/clinics/{clinica.id}/relatorios/atendimentos.xlsx?de=2026-03-01&ate=2026-03-31"
    assert _como(cliente, _usuario(conn, clinic_id=clinica.id)).get(url).status_code == 403
    r = _como(cliente, _usuario(conn, clinic_id=clinica.id, papel="clinic_admin")).get(url)
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert conn.execute("select tipo from report_exports where clinic_id = %s", (clinica.id,)).fetchone()[0] == "atendimentos"
    outra = _como(cliente, _usuario(conn, clinic_id=outra_clinica.id, papel="clinic_admin"))
    assert outra.get(url).status_code == 403  # admin de outra clínica não baixa


def test_dashboard_filtra_a_agenda_por_profissional(cliente, conn, clinica, outra_clinica):  # noqa: F811
    from datetime import datetime, time
    from zoneinfo import ZoneInfo

    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    _consulta(conn, clinica, datetime.combine(hoje, time(23, 0), ZoneInfo("America/Sao_Paulo")).isoformat(), "agendada")
    c = _como(cliente, _usuario(conn, clinic_id=clinica.id))
    base = f"/api/clinics/{clinica.id}/dashboard"
    assert len(c.get(base).json()["consultas_hoje"]) == 1
    assert len(c.get(f"{base}?profissional={clinica.prof_a}").json()["consultas_hoje"]) == 1
    assert len(c.get(f"{base}?profissional={clinica.prof_b}").json()["consultas_hoje"]) == 0
    assert c.get(f"{base}?profissional={outra_clinica.prof_a}").status_code == 404
