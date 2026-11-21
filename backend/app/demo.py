"""Clínica de demonstração (usada pelo scripts/seed_demo.py e pelo botão "Reiniciar demonstração")."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

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


def criar_estrutura(conn, nome: str, telefone: str, slug: str, endereco: str | None) -> tuple:
    """Clínica com horários, procedimentos e os 2 dentistas de exemplo (usada pela demo e pela bateria de cenários)."""
    clinic_id = conn.execute(
        """insert into clinics (name, phone, slug, timezone, address)
           values (%s, %s, %s, %s, %s) returning id""",
        (nome, telefone, slug, "America/Sao_Paulo", endereco),
    ).fetchone()[0]
    # demo e bateria de cenários usam a IA da plataforma (D46)
    conn.execute("insert into clinic_ai (clinic_id, usa_plataforma) values (%s, true)", (clinic_id,))
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

    return clinic_id, serv, prof


# Dados de TESTE da clínica (D56): tudo que nasce de clientes e conversas. A ordem respeita as ligações entre tabelas.
TABELAS_DE_TESTE = ("appointment_events", "outbound_messages", "action_tokens", "agent_runs", "messages",
                    "conversations", "crm_events", "patient_notes", "patient_photos", "appointments", "patients")

# Exemplos: nome, telefone, dias úteis à frente, hora, confirmar?
EXEMPLOS = [
    ("Maria da Silva", "(11) 98765-4321", 1, time(9), False),
    ("João Pereira", "11 97654-3210", 1, time(14), True),
    ("Carla Souza", "+55 21 99234-5678", 2, time(10), False),
]


def limpar_dados_de_teste(conn, clinic_id) -> None:
    """Apaga só clientes, consultas, conversas e mensagens. A clínica (nome, logo, cor, assistente, IA,
    WhatsApp, horários, equipe, procedimentos e usuários) fica como está."""
    for tabela in TABELAS_DE_TESTE:
        conn.execute(f"delete from {tabela} where clinic_id = %s", (clinic_id,))  # noqa: S608 — nomes fixos


def _pares(conn, clinic_id) -> list[tuple]:
    """(profissional, procedimento) ativos que a assistente pode marcar — da própria clínica, como ela está hoje."""
    return conn.execute(
        """select ps.professional_id, ps.service_id from professional_services ps
           join professionals p on p.id = ps.professional_id and p.active
           join services s on s.id = ps.service_id and s.active and s.bookable_by_ai
           where ps.clinic_id = %s order by p.name, s.name""", (clinic_id,)).fetchall()


def criar_exemplos(conn, clinic_id) -> int:
    """Consultas, um contato novo e um aniversariante, usando a equipe e os procedimentos que a clínica tem.
    Exemplo que não cabe na agenda (folga, fora do horário…) é pulado. Devolve quantas consultas criou."""
    from app.agenda.erros import AgendaError

    slug = conn.execute("select slug from clinics where id = %s", (clinic_id,)).fetchone()[0]
    pares = _pares(conn, clinic_id)
    hoje = datetime.now(TZ).date()
    criadas = 0
    for n, (nome, tel, dias, hora, confirmar) in enumerate(EXEMPLOS):
        for prof, serv in pares[n:] + pares[:n]:  # cada exemplo começa num par diferente, para variar a agenda
            dia = _dia_util(hoje, dias)
            try:
                with conn.transaction():
                    c = servico.marcar(conn, clinic_id, telefone=tel, nome=nome, professional_id=prof, service_id=serv,
                                       inicio=datetime.combine(dia, hora, tzinfo=TZ), ator="recepcao")
                    if confirmar:
                        servico.mudar_status(conn, clinic_id, appointment_id=c["id"], novo="confirmada", ator="recepcao")
                criadas += 1
                break
            except AgendaError:
                continue

    # Um contato novo que só conversou (coluna "Novo Contato" do CRM)
    chat.receber(conn, slug, "(11) 96543-2109", "Oi! Vocês fazem clareamento?", responder=False)
    conn.execute("update patients set name = 'Pedro Alves' where clinic_id = %s and phone = '+5511965432109'", (clinic_id,))
    # Aniversariante do dia, para o Dashboard
    conn.execute("update patients set birth_date = %s where clinic_id = %s and phone = '+5521992345678'",
                 (hoje.replace(year=1990), clinic_id))
    return criadas


def criar_demo(conn, reset: bool = False) -> str:
    """Cria a clínica de demonstração na 1ª vez. Com reset=True numa clínica que já existe, só troca os dados
    de teste pelos exemplos (D56) — nunca apaga a clínica nem as configurações dela."""
    # D61: a clínica de demonstração é a marcada como apresentação (D55); "demo" só vale para criar a 1ª vez
    existente = conn.execute("select id from clinics where apresentacao").fetchone() or         conn.execute("select id from clinics where slug = %s", (SLUG,)).fetchone()
    if existente:
        if reset:
            limpar_dados_de_teste(conn, existente[0])
            criar_exemplos(conn, existente[0])
        return str(existente[0])
    clinic_id, _, _ = criar_estrutura(
        conn, "Clínica Dental Demo", TELEFONE_CLINICA, SLUG, "Rua das Flores, 123 — Centro, São Paulo/SP")
    # demo já nasce pronta e vira a clínica de apresentação se ainda não houver uma
    conn.execute("""update clinics set configurada_em = now(),
                    apresentacao = not exists(select 1 from clinics where apresentacao) where id = %s""", (clinic_id,))
    criar_exemplos(conn, clinic_id)
    return str(clinic_id)
