"""Cria (ou recria) a clínica de demonstração com dados de exemplo.

Uso (na pasta backend):
    uv run python scripts/seed_demo.py            # cria se não existir
    uv run python scripts/seed_demo.py --reset    # apaga a clínica demo e cria de novo
"""

import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agenda import servico  # noqa: E402
from app.config import get_settings  # noqa: E402

TELEFONE_CLINICA = "+5511999990000"
SLUG = "demo"
TZ = ZoneInfo("America/Sao_Paulo")

PROCEDIMENTOS = [
    # nome, descrição, minutos, pode a Ísis marcar?
    ("Avaliação odontológica geral", "Exame clínico completo, diagnóstico e plano de tratamento.", 60, True),
    ("Limpeza (profilaxia)", "Remoção de tártaro e placa bacteriana, com polimento.", 60, True),
    ("Restauração", "Tratamento de cárie com resina na cor do dente.", 60, True),
    ("Clareamento a laser", "Clareamento dental feito no consultório.", 60, True),
    ("Retorno", "Consulta de acompanhamento após um tratamento.", 30, True),
    ("Atendimento de urgência", "Dor, trauma ou infecção. Encaixe feito pela recepção.", 60, False),
]

PROFISSIONAIS = [
    ("Dra. Ana Lima", "Clínica geral e estética", "#B85C74",
     ["Avaliação odontológica geral", "Limpeza (profilaxia)", "Clareamento a laser", "Retorno", "Atendimento de urgência"]),
    ("Dr. Bruno Costa", "Clínica geral e dentística", "#2F80C9",
     ["Avaliação odontológica geral", "Limpeza (profilaxia)", "Restauração", "Retorno", "Atendimento de urgência"]),
]

# Horário da clínica (tela "Horários de Funcionamento"): 0=seg ... 5=sáb
HORARIO = {0: ("08:00", "18:00"), 1: ("08:00", "18:00"), 2: ("08:00", "18:00"),
           3: ("08:00", "18:00"), 4: ("08:00", "17:00"), 5: ("09:00", "13:00")}
ALMOCO = ("12:00", "13:00")  # seg a sex

PACIENTES = [("Maria da Silva", "(11) 98765-4321"), ("João Pereira", "11 97654-3210"), ("Carla Souza", "+55 21 99234-5678")]


def proximo_dia_util(d: date, n: int) -> date:
    while n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def main() -> int:
    reset = "--reset" in sys.argv
    with psycopg.connect(get_settings().database_url) as conn:
        existente = conn.execute("select id from clinics where slug = %s", (SLUG,)).fetchone()
        if existente and not reset:
            print(f"Clínica demo já existe (id {existente[0]}). Use --reset para recriar.")
            return 0
        if existente:
            conn.execute("delete from appointment_events where clinic_id = %s", existente)
            conn.execute("delete from appointments where clinic_id = %s", existente)
            conn.execute("delete from clinics where id = %s", existente)
            print("Clínica demo antiga apagada.")

        clinic_id = conn.execute(
            """insert into clinics (name, phone, slug, timezone, address, settings)
               values (%s, %s, %s, %s, %s, %s) returning id""",
            ("Clínica Dental Demo", TELEFONE_CLINICA, SLUG, "America/Sao_Paulo",
             "Rua das Flores, 123 — Centro, São Paulo/SP", "{}"),
        ).fetchone()[0]

        for wd, (ini, fim) in HORARIO.items():
            conn.execute("insert into clinic_hours (clinic_id, weekday, start_time, end_time) values (%s,%s,%s,%s)",
                         (clinic_id, wd, ini, fim))
        for wd in range(5):
            conn.execute("insert into clinic_breaks (clinic_id, weekday, start_time, end_time) values (%s,%s,%s,%s)",
                         (clinic_id, wd, *ALMOCO))

        serv_ids = {}
        for nome, desc, minutos, ia in PROCEDIMENTOS:
            serv_ids[nome] = conn.execute(
                """insert into services (clinic_id, name, description, duration_min, bookable_by_ai)
                   values (%s,%s,%s,%s,%s) returning id""",
                (clinic_id, nome, desc, minutos, ia),
            ).fetchone()[0]

        prof_ids = {}
        for nome, esp, cor, faz in PROFISSIONAIS:
            pid = conn.execute(
                "insert into professionals (clinic_id, name, specialty, color) values (%s,%s,%s,%s) returning id",
                (clinic_id, nome, esp, cor),
            ).fetchone()[0]
            prof_ids[nome] = pid
            for s in faz:
                conn.execute("insert into professional_services (clinic_id, professional_id, service_id) values (%s,%s,%s)",
                             (clinic_id, pid, serv_ids[s]))

        # Exceção de horário: Dr. Bruno não atende às sextas
        for wd, (ini, fim) in HORARIO.items():
            if wd != 4:
                conn.execute(
                    "insert into professional_hours (clinic_id, professional_id, weekday, start_time, end_time) values (%s,%s,%s,%s,%s)",
                    (clinic_id, prof_ids["Dr. Bruno Costa"], wd, ini, fim),
                )

        # Algumas consultas nos próximos dias úteis, para a agenda não começar vazia
        hoje = datetime.now(TZ).date()
        exemplos = [
            (PACIENTES[0], "Dra. Ana Lima", "Limpeza (profilaxia)", proximo_dia_util(hoje, 1), time(9)),
            (PACIENTES[1], "Dr. Bruno Costa", "Avaliação odontológica geral", proximo_dia_util(hoje, 1), time(14)),
            (PACIENTES[2], "Dra. Ana Lima", "Clareamento a laser", proximo_dia_util(hoje, 2), time(10)),
        ]
        for (nome, tel), prof, serv, dia, hora in exemplos:
            if dia.weekday() == 4 and prof == "Dr. Bruno Costa":
                dia = proximo_dia_util(dia, 1)
            servico.marcar(conn, clinic_id, telefone=tel, nome=nome, professional_id=prof_ids[prof],
                           service_id=serv_ids[serv], inicio=datetime.combine(dia, hora, tzinfo=TZ), ator="recepcao")

    print("Clínica demo criada:")
    print(f"  id: {clinic_id}")
    print(f"  telefone (chave): {TELEFONE_CLINICA}")
    print(f"  {len(PROFISSIONAIS)} dentistas, {len(PROCEDIMENTOS)} procedimentos, {len(exemplos)} consultas de exemplo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
