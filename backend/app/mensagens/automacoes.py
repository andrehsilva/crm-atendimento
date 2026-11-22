"""Etapa 25 — pós-consulta e retorno automáticos (RN-AU, D100–D103).

Os dois começam desligados (o administrador liga). Ninguém recebe duas vezes a mesma coisa: a chave `dedupe_key`
da fila garante uma pós-consulta por atendimento e no máximo 2 convites de retorno por ciclo (desde a última visita).
"""

from datetime import datetime, timedelta

from app.eventos import avisar
from app.mensagens import regras as R
from app.painel.avisos import primeiro_nome

PADRAO = {
    "pos_consulta_ativo": False,
    "pos_consulta_hora": "10:00",
    "pos_consulta_texto": ("Olá, {nome}! Aqui é da {clinica}. Como você está depois do atendimento de ontem? "
                           "Se tiver qualquer dúvida ou desconforto, é só responder por aqui. 💚"),
    "pos_consulta_excluir": [],  # ids de procedimentos que não recebem (ex.: "Retorno")
    "retorno_ativo": False,
    "retorno_hora": "10:00",
    "retorno_meses": 6,
    "retorno_texto": ("Olá, {nome}! Já está na hora de voltar à {clinica} para cuidar do seu sorriso. "
                      "Quer que eu veja um horário para você? É só responder por aqui. 😊"),
    "retorno_texto2": ("Oi, {nome}! Passando para lembrar do seu retorno na {clinica}. "
                       "Quando quiser marcar, é só me chamar por aqui."),
}
JANELA_RETORNO_DIAS = 30  # RN-AU-03: só datas vencidas há pouco (não dispara para todo o histórico)
SEGUNDO_CONVITE_DIAS = 15  # D103


def config(settings: dict | None) -> dict:
    cfg = settings or {}
    return {k: cfg.get(k, v) for k, v in PADRAO.items()}


def montar(texto: str, nome: str | None, clinica: str, procedimento: str = "") -> str:
    return (texto.replace("{nome}", primeiro_nome(nome)).replace("{clinica}", clinica)
            .replace("{procedimento}", procedimento))


def agendar_pos_consulta(conn, clinica: dict, consulta: dict) -> bool:
    """Chamada ao marcar "Compareceu" (RN-AU-02). Põe na fila para o dia seguinte no horário configurado."""
    cfg = config(clinica.get("settings"))
    if not cfg["pos_consulta_ativo"] or str(consulta["service_id"]) in {str(x) for x in cfg["pos_consulta_excluir"]}:
        return False
    tz = clinica["tz"]
    dia = consulta["starts_at"].astimezone(tz).date() + timedelta(days=1)
    quando = datetime.combine(dia, R.hora(cfg["pos_consulta_hora"]), tzinfo=tz)
    nome, proc = conn.execute(
        """select p.name, s.name from patients p, services s where p.id = %s and s.id = %s""",
        (consulta["patient_id"], consulta["service_id"])).fetchone()
    r = conn.execute(
        """insert into outbound_messages (clinic_id, patient_id, appointment_id, kind, body, scheduled_for, dedupe_key)
           values (%s, %s, %s, 'pos_consulta', %s, %s, %s)
           on conflict (clinic_id, kind, dedupe_key) where dedupe_key is not null do nothing returning id""",
        (clinica["id"], consulta["patient_id"], consulta["id"],
         montar(cfg["pos_consulta_texto"], nome, clinica["name"], proc), quando, str(consulta["id"])),
    ).fetchone()
    if r:
        avisar(conn, clinica["id"], "mensagens")
    return bool(r)


def gerar_retornos(conn, agora: datetime, so_clinica=None) -> int:
    """Uma passada (agendador): convites de retorno vencidos hoje (RN-AU-03/04). Devolve quantos entraram na fila."""
    from app.agenda.servico import carregar_clinica

    total = 0
    ids = [r[0] for r in conn.execute(
        """select id from clinics where status = 'ativa' and coalesce((settings->>'retorno_ativo')::boolean, false)
           and (%s::uuid is null or id = %s::uuid)""", (so_clinica, so_clinica)).fetchall()]
    for cid in ids:
        clinica = carregar_clinica(conn, cid)
        cfg = config(clinica["settings"])
        tz = clinica["tz"]
        local = agora.astimezone(tz)
        if local.time() < R.hora(cfg["retorno_hora"]):
            continue
        hoje = local.date()
        meses = int(cfg["retorno_meses"] or 6)
        linhas = conn.execute(
            """with base as (
                 select p.id, p.name,
                        (select max(a.starts_at) from appointments a where a.patient_id = p.id and a.clinic_id = p.clinic_id
                          and a.status = 'realizada') as ultima,
                        (select t.volta_em from treatments t where t.patient_id = p.id and t.clinic_id = p.clinic_id
                          and t.status = 'concluido' and t.volta_em is not null order by t.status_desde desc limit 1) as volta_em
                 from patients p
                 where p.clinic_id = %(c)s and not p.optout_disparos
                   and not exists (select 1 from appointments f where f.patient_id = p.id and f.clinic_id = p.clinic_id
                                   and f.status in ('agendada', 'confirmada') and f.starts_at > %(agora)s)
                   and not exists (select 1 from treatments t where t.patient_id = p.id and t.clinic_id = p.clinic_id
                                   and t.status in ('em_andamento', 'aguardando'))
               )
               select id, name, ultima,
                      coalesce(volta_em, ((ultima at time zone %(tz)s)::date + make_interval(months => %(meses)s))::date) as vence
               from base where ultima is not null""",
            {"c": cid, "agora": agora, "tz": clinica["timezone"], "meses": meses}).fetchall()
        for pid, nome, ultima, vence in linhas:
            if vence > hoje or vence < hoje - timedelta(days=JANELA_RETORNO_DIAS + SEGUNDO_CONVITE_DIAS):
                continue
            ciclo = f"{pid}:{ultima:%Y%m%d}"  # muda quando a pessoa volta: um novo ciclo começa
            enviados = conn.execute(
                """select dedupe_key, coalesce(sent_at, scheduled_for) from outbound_messages
                   where clinic_id = %s and kind = 'retorno' and dedupe_key like %s order by created_at""",
                (cid, ciclo + ":%")).fetchall()
            if not enviados:
                if vence < hoje - timedelta(days=JANELA_RETORNO_DIAS):
                    continue  # venceu há muito: fica só no relatório de recall
                chave, texto = f"{ciclo}:1", cfg["retorno_texto"]
            elif len(enviados) == 1:
                desde = enviados[0][1]
                respondeu = conn.execute(
                    """select exists(select 1 from messages m join conversations cv on cv.id = m.conversation_id
                       where cv.clinic_id = %s and cv.patient_id = %s and m.direction = 'in' and m.created_at > %s)""",
                    (cid, pid, desde)).fetchone()[0]
                if respondeu or agora - desde < timedelta(days=SEGUNDO_CONVITE_DIAS):
                    continue
                chave, texto = f"{ciclo}:2", cfg["retorno_texto2"]
            else:
                continue  # D103: depois do 2º convite, para
            r = conn.execute(
                """insert into outbound_messages (clinic_id, patient_id, kind, body, scheduled_for, dedupe_key)
                   values (%s, %s, 'retorno', %s, %s, %s)
                   on conflict (clinic_id, kind, dedupe_key) where dedupe_key is not null do nothing returning id""",
                (cid, pid, montar(texto, nome, clinica["name"]), agora, chave)).fetchone()
            total += bool(r)
        if total:
            avisar(conn, cid, "mensagens")
    return total
