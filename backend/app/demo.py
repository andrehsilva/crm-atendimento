"""Clínica de demonstração (usada pelo scripts/seed_demo.py e pelo botão "Reiniciar demonstração")."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from psycopg.types.json import Jsonb

from app.agenda import servico
from app.painel import chat

TELEFONE_CLINICA = "+5511999990000"
SLUG = "demo"
TZ = ZoneInfo("America/Sao_Paulo")

PROCEDIMENTOS = [
    # nome, descrição, minutos, a Ísis pode marcar?
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

# 0=seg ... 5=sáb
HORARIO = {0: ("08:00", "18:00"), 1: ("08:00", "18:00"), 2: ("08:00", "18:00"),
           3: ("08:00", "18:00"), 4: ("08:00", "17:00"), 5: ("09:00", "13:00")}
ALMOCO = ("12:00", "13:00")  # seg a sex


def _dia_util(d: date, n: int, evitar_sexta: bool = False) -> date:
    while n:
        d += timedelta(days=1)
        if d.weekday() < 5 and not (evitar_sexta and d.weekday() == 4):
            n -= 1
    return d


def criar_demo(conn, reset: bool = False) -> str:
    existente = conn.execute("select id from clinics where slug = %s", (SLUG,)).fetchone()
    if existente and not reset:
        return str(existente[0])
    guardados = {"whatsapp": [], "usuarios": [], "settings": None}
    if existente:
        # O reset recria a clínica do zero, mas mantém o WhatsApp, os usuários e as configurações ligados a ela
        guardados["whatsapp"] = conn.execute(
            "select session, status, phone, enabled from whatsapp_instances where clinic_id = %s", existente).fetchall()
        guardados["usuarios"] = conn.execute(
            "select user_id, role, active from clinic_users where clinic_id = %s", existente).fetchall()
        guardados["settings"] = conn.execute("select settings from clinics where id = %s", existente).fetchone()[0]
        conn.execute("delete from appointment_events where clinic_id = %s", existente)
        conn.execute("delete from outbound_messages where clinic_id = %s", existente)
        conn.execute("delete from appointments where clinic_id = %s", existente)
        conn.execute("delete from clinics where id = %s", existente)

    clinic_id = conn.execute(
        """insert into clinics (name, phone, slug, timezone, address)
           values (%s, %s, %s, %s, %s) returning id""",
        ("Clínica Dental Demo", TELEFONE_CLINICA, SLUG, "America/Sao_Paulo", "Rua das Flores, 123 — Centro, São Paulo/SP"),
    ).fetchone()[0]
    if guardados["settings"]:
        conn.execute("update clinics set settings = %s where id = %s", (Jsonb(guardados["settings"]), clinic_id))
    for sessao, status, fone, ligado in guardados["whatsapp"]:
        conn.execute("insert into whatsapp_instances (clinic_id, session, status, phone, enabled) values (%s,%s,%s,%s,%s)",
                     (clinic_id, sessao, status, fone, ligado))
    for uid, papel, ativo in guardados["usuarios"]:
        conn.execute("insert into clinic_users (clinic_id, user_id, role, active) values (%s,%s,%s,%s)", (clinic_id, uid, papel, ativo))

    for wd, (ini, fim) in HORARIO.items():
        conn.execute("insert into clinic_hours (clinic_id, weekday, start_time, end_time) values (%s,%s,%s,%s)",
                     (clinic_id, wd, ini, fim))
    for wd in range(5):
        conn.execute("insert into clinic_breaks (clinic_id, weekday, start_time, end_time) values (%s,%s,%s,%s)",
                     (clinic_id, wd, *ALMOCO))

    serv = {}
    for nome, desc, minutos, ia in PROCEDIMENTOS:
        serv[nome] = conn.execute(
            """insert into services (clinic_id, name, description, duration_min, bookable_by_ai)
               values (%s,%s,%s,%s,%s) returning id""",
            (clinic_id, nome, desc, minutos, ia),
        ).fetchone()[0]

    prof = {}
    for nome, esp, cor, faz in PROFISSIONAIS:
        pid = conn.execute(
            "insert into professionals (clinic_id, name, specialty, color) values (%s,%s,%s,%s) returning id",
            (clinic_id, nome, esp, cor),
        ).fetchone()[0]
        prof[nome] = pid
        for s in faz:
            conn.execute("insert into professional_services (clinic_id, professional_id, service_id) values (%s,%s,%s)",
                         (clinic_id, pid, serv[s]))

    # Exceção de horário: Dr. Bruno não atende às sextas
    for wd, (ini, fim) in HORARIO.items():
        if wd != 4:
            conn.execute(
                "insert into professional_hours (clinic_id, professional_id, weekday, start_time, end_time) values (%s,%s,%s,%s,%s)",
                (clinic_id, prof["Dr. Bruno Costa"], wd, ini, fim),
            )

    hoje = datetime.now(TZ).date()

    def marcar(nome, tel, dentista, procedimento, dia, hora):
        return servico.marcar(conn, clinic_id, telefone=tel, nome=nome, professional_id=prof[dentista],
                              service_id=serv[procedimento], inicio=datetime.combine(dia, hora, tzinfo=TZ), ator="recepcao")

    marcar("Maria da Silva", "(11) 98765-4321", "Dra. Ana Lima", "Limpeza (profilaxia)", _dia_util(hoje, 1), time(9))
    joao = marcar("João Pereira", "11 97654-3210", "Dr. Bruno Costa", "Avaliação odontológica geral",
                  _dia_util(hoje, 1, evitar_sexta=True), time(14))
    marcar("Carla Souza", "+55 21 99234-5678", "Dra. Ana Lima", "Clareamento a laser", _dia_util(hoje, 2), time(10))
    servico.mudar_status(conn, clinic_id, appointment_id=joao["id"], novo="confirmada", ator="recepcao")

    # Um contato novo que só conversou (coluna "Novo Contato")
    chat.receber(conn, SLUG, "(11) 96543-2109", "Oi! Vocês fazem clareamento?", responder=False)
    conn.execute("update patients set name = 'Pedro Alves' where clinic_id = %s and phone = '+5511965432109'", (clinic_id,))

    # Aniversariante do dia, para o Dashboard
    conn.execute("update patients set birth_date = %s where clinic_id = %s and phone = '+5521992345678'",
                 (hoje.replace(year=1990), clinic_id))
    return str(clinic_id)
