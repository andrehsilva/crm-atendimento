"""Fixtures de teste com banco.

Cada teste roda dentro de uma transação que é DESFEITA no final: nada fica gravado no Supabase.
Sem DATABASE_URL no .env, os testes de banco são pulados.
"""

from datetime import datetime, time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import psycopg
import pytest

from app.config import get_settings

TZ = ZoneInfo("America/Sao_Paulo")
# "Agora" fixo: sexta 20/11/2026 10:00 — os testes não dependem do dia em que rodam
AGORA = datetime(2026, 11, 20, 10, 0, tzinfo=TZ)


@pytest.fixture
def conn():
    url = get_settings().database_url
    if not url:
        pytest.skip("DATABASE_URL não configurada")
    with psycopg.connect(url) as c:
        try:
            yield c
        finally:
            c.rollback()


def _clinica(conn, telefone: str, slug: str, nome: str) -> SimpleNamespace:
    cid = conn.execute(
        "insert into clinics (name, phone, slug) values (%s, %s, %s) returning id", (nome, telefone, slug)
    ).fetchone()[0]
    conn.execute("insert into clinic_ai (clinic_id, usa_plataforma) values (%s, true)", (cid,))  # D46: IA ligada
    for wd in range(5):  # seg-sex 08-18, almoço 12-13
        conn.execute("insert into clinic_hours (clinic_id, weekday, start_time, end_time) values (%s,%s,'08:00','18:00')", (cid, wd))
        conn.execute("insert into clinic_breaks (clinic_id, weekday, start_time, end_time) values (%s,%s,'12:00','13:00')", (cid, wd))
    sid = conn.execute(
        "insert into services (clinic_id, name, duration_min) values (%s, 'Limpeza', 60) returning id", (cid,)
    ).fetchone()[0]
    urg = conn.execute(
        "insert into services (clinic_id, name, duration_min, bookable_by_ai) values (%s, 'Urgência', 60, false) returning id", (cid,)
    ).fetchone()[0]
    profs = []
    for nome_p in ("Dra. A", "Dr. B"):
        pid = conn.execute("insert into professionals (clinic_id, name) values (%s, %s) returning id", (cid, nome_p)).fetchone()[0]
        for s in (sid, urg):
            conn.execute("insert into professional_services (clinic_id, professional_id, service_id) values (%s,%s,%s)", (cid, pid, s))
        profs.append(pid)
    return SimpleNamespace(id=cid, servico=sid, urgencia=urg, prof_a=profs[0], prof_b=profs[1])


@pytest.fixture
def clinica(conn):
    return _clinica(conn, "+5511900000001", "teste-a", "Clínica Teste A")


@pytest.fixture
def outra_clinica(conn):
    return _clinica(conn, "+5511900000002", "teste-b", "Clínica Teste B")


def as_(dia: int, hora: int, minuto: int = 0) -> datetime:
    """Data em novembro/2026 no fuso de São Paulo. Ex.: as_(23, 9) = seg 23/11 09:00."""
    return datetime(2026, 11, dia, hora, minuto, tzinfo=TZ)


__all__ = ["AGORA", "TZ", "as_", "time"]
