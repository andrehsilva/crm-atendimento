"""C17 — dois pacientes pedem o MESMO horário ao mesmo tempo (conexões separadas, de verdade).

Este teste precisa gravar no banco (cada conexão confirma a sua transação). Ele cria uma clínica
temporária e a apaga no fim.
"""

import threading
import uuid
from datetime import datetime, timedelta

import psycopg
import pytest

from app.agenda import servico as S
from app.agenda.erros import AgendaError
from app.config import get_settings
from app.demo import TZ, criar_estrutura


def _proximo_dia_util_10h() -> datetime:
    d = datetime.now(TZ).date() + timedelta(days=2)
    while d.weekday() >= 4:  # seg a qui (Dr. Bruno não atende sexta; usamos a Dra. Ana de qualquer forma)
        d += timedelta(days=1)
    return datetime.combine(d, datetime.min.time(), tzinfo=TZ).replace(hour=10)


def test_c17_dois_pedidos_simultaneos_so_um_marca():
    url = get_settings().database_url
    if not url:
        pytest.skip("DATABASE_URL não configurada")
    sufixo = uuid.uuid4().hex[:8]
    with psycopg.connect(url) as c:
        cid, serv, prof = criar_estrutura(c, f"Concorrência {sufixo}", f"+5511{int(sufixo, 16) % 10**8:08d}0",
                                          f"concorrencia-{sufixo}", None)
        c.commit()
    inicio = _proximo_dia_util_10h()
    largada = threading.Barrier(2)
    resultados: list[str] = []

    def paciente(tel: str, nome: str):
        with psycopg.connect(url) as conn:
            largada.wait()  # os dois pedem no mesmo instante
            try:
                S.marcar(conn, cid, telefone=tel, nome=nome, professional_id=prof["Dra. Ana Lima"],
                         service_id=serv["Limpeza (profilaxia)"], inicio=inicio, ator="isis")
                conn.commit()
                resultados.append("marcou")
            except AgendaError as e:
                conn.rollback()
                resultados.append(e.codigo)
            except Exception as e:  # noqa: BLE001 — qualquer outro erro precisa aparecer no resultado do teste
                conn.rollback()
                resultados.append(f"ERRO {type(e).__name__}: {str(e)[:200]}")

    try:
        t = [threading.Thread(target=paciente, args=(f"+55119770000{i}", f"Paciente {i}")) for i in (1, 2)]
        for x in t:
            x.start()
        for x in t:
            x.join(timeout=30)
        assert sorted(resultados) == ["HORARIO_OCUPADO", "marcou"], resultados
    finally:
        with psycopg.connect(url) as c:
            for tabela in ("appointment_events", "outbound_messages", "appointments"):
                c.execute(f"delete from {tabela} where clinic_id = %s", (cid,))  # noqa: S608 — nomes fixos
            c.execute("delete from clinics where id = %s", (cid,))
            c.commit()
