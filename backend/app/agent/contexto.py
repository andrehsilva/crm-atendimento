"""Monta as instruções da Ísis em 3 camadas (spec 02):
1. persona e regras fixas (prompts/isis.md)
2. dados da clínica (do banco)
3. o momento: data/hora, calendário dos próximos dias, quem é o paciente
"""

from datetime import datetime, timedelta
from pathlib import Path

from psycopg.rows import dict_row

from app.agenda import servico
from app.painel.avisos import DIAS, quando

PROMPT = Path(__file__).parent / "prompts" / "isis.md"
DIAS_CURTOS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def _telefone_legivel(e164: str) -> str:
    d = e164.lstrip("+")[2:]
    return f"({d[:2]}) {d[2:-4]}-{d[-4:]}" if len(d) >= 10 else e164


def esta_aberta(conn, clinica: dict, agora: datetime) -> bool:
    wd = agora.weekday()
    r = conn.execute(
        "select start_time, end_time from clinic_hours where clinic_id = %s and weekday = %s and enabled",
        (clinica["id"], wd),
    ).fetchone()
    return bool(r) and r[0] <= agora.time() < r[1]


def instrucoes(conn, clinica: dict, paciente: dict, agora: datetime) -> str:
    cfg = clinica["settings"] or {}
    tz = clinica["tz"]
    aberta = esta_aberta(conn, clinica, agora)
    persona = PROMPT.read_text(encoding="utf-8").format(
        nome_assistente=cfg.get("nome_assistente", "Ísis"),
        clinica=clinica["name"],
        tratamento=cfg.get("tratamento", "você"),
        telefone_urgencia=_telefone_legivel(cfg.get("telefone_urgencia") or clinica["phone"]),
        aviso_horario="" if aberta else " no próximo horário de atendimento (a clínica está fechada agora)",
    )

    # ---- camada 3: o momento
    linhas_cal = []
    for i in range(15):
        d = (agora + timedelta(days=i)).date()
        rot = " (hoje)" if i == 0 else " (amanhã)" if i == 1 else ""
        linhas_cal.append(f"- {DIAS_CURTOS[d.weekday()]} {d:%d/%m/%Y}{rot}")

    hoje = agora.date()
    proximos = []
    for wd in range(7):
        delta = (wd - hoje.weekday()) % 7 or 7  # sempre DEPOIS de hoje
        d = hoje + timedelta(days=delta)
        nome = DIAS[wd].replace("-feira", "")
        proximos.append(f'- "{nome}", "próxima {nome}", "{nome} que vem" = {DIAS[wd]} {d:%d/%m}')
    seg = hoje + timedelta(days=(7 - hoje.weekday()))
    semana_que_vem = f"segunda {seg:%d/%m} a sábado {seg + timedelta(days=5):%d/%m}"

    futuras = servico.consultas_do_paciente(conn, clinica["id"], paciente["phone"], agora=agora)
    consultas = "\n".join(
        f"- {quando(c['starts_at'], tz)}: {c['procedimento']} com {c['profissional']} ({c['status']}) [id {c['id']}]"
        for c in futuras
    ) or "- nenhuma"

    ref = None
    if paciente.get("preferred_professional_id"):
        r = conn.execute("select name from professionals where id = %s", (paciente["preferred_professional_id"],)).fetchone()
        ref = r and r[0]

    # Ações preparadas que esperam o "sim" do paciente (o token não fica no histórico de mensagens)
    pendentes = conn.execute(
        """select id, resumo, created_at from action_tokens
           where clinic_id = %s and patient_id = %s and used_at is null and expires_at > now()
           order by created_at desc limit 3""",
        (clinica["id"], paciente["id"]),
    ).fetchall()
    acoes = "\n".join(f"- token {t[0]}: {t[1]} (preparada às {t[2].astimezone(tz):%H:%M})" for t in pendentes) or "- nenhuma"

    cur = conn.cursor(row_factory=dict_row)
    profs = cur.execute(
        """select p.name, p.specialty, string_agg(s.name, ', ' order by s.name) as faz
           from professionals p join professional_services ps on ps.professional_id = p.id
           join services s on s.id = ps.service_id and s.active
           where p.clinic_id = %s and p.active group by p.id order by p.name""",
        (clinica["id"],),
    ).fetchall()
    servs = cur.execute(
        "select name, duration_min, bookable_by_ai from services where clinic_id = %s and active order by name",
        (clinica["id"],),
    ).fetchall()
    resumo_clinica = "\n".join(
        [f"- Dentista {p['name']}" + (f" ({p['specialty']})" if p["specialty"] else "") + f": faz {p['faz']}" for p in profs]
        + [f"- Procedimento {x['name']}: {x['duration_min']} min" + ("" if x["bookable_by_ai"] else " — só a recepção marca (use chamar_humano)")
           for x in servs]
    )

    momento = f"""
# Agora

Agora é **{DIAS[agora.weekday()]}, {agora:%d/%m/%Y}, {agora:%H:%M}** (horário de {clinica['timezone']}).
A clínica está {"**aberta**" if aberta else "**fechada** neste momento (você continua atendendo e marcando normalmente)"}.

Calendário dos próximos dias:
{chr(10).join(linhas_cal)}

Significado das expressões (já calculado — use exatamente estas datas):
{chr(10).join(proximos)}
- "semana que vem" = de {semana_que_vem}

# Clínica (resumo — endereço, horários e preços em info_clinica)

{resumo_clinica}

# Paciente desta conversa

- Nome: {paciente.get('name') or 'ainda não informado (peça o nome completo antes de marcar)'}
- Telefone: já identificado pelo canal — não peça o telefone.
- Dentista de referência: {ref or 'nenhum ainda'}
- Consultas futuras:
{consultas}

# Ações preparadas aguardando o "sim" do paciente

{acoes}

Se o paciente acabou de concordar com uma dessas ações, chame `confirmar_acao` com o token correspondente
(não prepare de novo). Se ele mudou de ideia, ignore o token e prepare a nova ação.
"""
    return persona + "\n" + momento


def dados_clinica(conn, clinica: dict) -> dict:
    """Usado pela ferramenta info_clinica (camada 2, sob demanda para não pesar o prompt)."""
    cfg = clinica["settings"] or {}
    cur = conn.cursor(row_factory=dict_row)
    horario = cur.execute(
        "select weekday, start_time, end_time from clinic_hours where clinic_id = %s and enabled order by weekday",
        (clinica["id"],),
    ).fetchall()
    pausas = cur.execute("select weekday, start_time, end_time from clinic_breaks where clinic_id = %s", (clinica["id"],)).fetchall()
    profs = cur.execute(
        "select name, specialty from professionals where clinic_id = %s and active order by name", (clinica["id"],)
    ).fetchall()
    servs = cur.execute(
        """select name, description, duration_min, price_cents, bookable_by_ai from services
           where clinic_id = %s and active order by name""",
        (clinica["id"],),
    ).fetchall()
    mostrar_precos = bool(cfg.get("mostrar_precos"))  # RN-AT-10
    return {
        "nome": clinica["name"],
        "endereco": clinica["address"],
        "telefone": _telefone_legivel(clinica["phone"]),
        "horario": [f"{DIAS[h['weekday']]}: {h['start_time']:%H:%M}–{h['end_time']:%H:%M}" for h in horario],
        "pausas": [f"{DIAS[p['weekday']]}: {p['start_time']:%H:%M}–{p['end_time']:%H:%M}" for p in pausas],
        "dentistas": [f"{p['name']}" + (f" ({p['specialty']})" if p["specialty"] else "") for p in profs],
        "procedimentos": [
            {
                "nome": s["name"],
                "duracao_min": s["duration_min"],
                "descricao": s["description"],
                **({"preco": f"R$ {s['price_cents'] / 100:.2f}".replace(".", ",")} if mostrar_precos and s["price_cents"] else {}),
                **({"observacao": "marcado só pela recepção — ofereça falar com a equipe"} if not s["bookable_by_ai"] else {}),
            }
            for s in servs
        ],
        "precos": "informe só os valores listados" if mostrar_precos else "a clínica não divulga preços pelo chat",
        # Texto livre da clínica (Configurações › Perfil): convênios, estacionamento, acessibilidade...
        **({"sobre_a_clinica": cfg["sobre_clinica"]} if cfg.get("sobre_clinica") else {}),
    }
