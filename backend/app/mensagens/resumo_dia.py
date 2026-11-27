"""Etapa 23 — resumo do dia no WhatsApp pessoal do profissional (RN-RS, D96–D98).

Roda junto com o agendador (a cada 30 s). Para cada profissional que pediu o resumo:
- no horário dele (padrão 07:00), só em dia que a clínica abre e só se houver consulta;
- uma vez por dia (tabela professional_digests), mesmo que a agenda mude depois;
- sem observação clínica, telefone ou convênio: horário, primeiro nome, procedimento, sessão e se confirmou.
"""

import logging
from datetime import date, datetime, time, timedelta
from uuid import UUID

from psycopg.rows import dict_row

from app import segmentos
from app.agenda import regras as R
from app.agenda import servico
from app.canais import modelos_meta
from app.canais.conexao import cliente_da_clinica
from app.canais.meta import ClienteMeta
from app.canais.waha import ClienteWaha, WahaErro
from app.config import Settings, get_settings
from app.mensagens import regras as RM
from app.mensagens.envio import lista_de_teste
from app.painel.avisos import DIAS

log = logging.getLogger("isis.resumo")
MAX_TENTATIVAS = 3
JANELA_HORAS = 3  # passou 3 h do horário (ex.: backend estava desligado) → não manda resumo atrasado


def _hhmm(dt: datetime, tz) -> str:
    return dt.astimezone(tz).strftime("%H:%M")


def _faixas(intervalos: list, tz) -> str:
    return ", ".join(f"{_hhmm(a, tz)}–{_hhmm(b, tz)}" for a, b in intervalos)


def montar(conn, clinica: dict, prof: dict, dia: date) -> str | None:
    """Texto do resumo do dia, ou None quando o profissional não tem consulta nesse dia (D98: não manda)."""
    tz = clinica["tz"]
    ini = datetime.combine(dia, time.min, tzinfo=tz)
    fim = ini + timedelta(days=1)
    consultas = conn.cursor(row_factory=dict_row).execute(
        """select a.starts_at, a.ends_at, a.status, p.name as paciente, s.name as procedimento, a.treatment_id,
                  t.sessoes_previstas,
                  (select count(*) from appointments x where x.treatment_id = a.treatment_id and x.status = 'realizada'
                     and x.starts_at < a.starts_at) as sessoes_antes
           from appointments a join patients p on p.id = a.patient_id and p.clinic_id = a.clinic_id
           join services s on s.id = a.service_id
           left join treatments t on t.id = a.treatment_id
           where a.clinic_id = %s and a.professional_id = %s and a.status in ('agendada', 'confirmada')
             and a.starts_at >= %s and a.starts_at < %s
           order by a.starts_at""",
        (clinica["id"], prof["id"], ini, fim),
    ).fetchall()
    if not consultas:
        return None

    t = segmentos.termos(clinica.get("settings") or {})
    n = len(consultas)
    palavra = t["atendimento"] if n == 1 else t["atendimentos"]
    linhas = []
    for c in consultas:
        nome = (c["paciente"] or "Paciente").split(" ")[0]  # D96: só o primeiro nome
        sessao = ""
        if c["treatment_id"]:
            num = c["sessoes_antes"] + 1
            sessao = f" (sessão {num}" + (f" de {c['sessoes_previstas']})" if c["sessoes_previstas"] else ")")
        marca = "✅" if c["status"] == "confirmada" else "⏳"
        linhas.append(f"{_hhmm(c['starts_at'], tz)} · {nome} · {c['procedimento']}{sessao} {marca}")

    # pausas e horários livres do dia (mesmas regras da agenda)
    horas, pausas = servico._horario(conn, clinica["id"])
    janelas = R.janelas_do_dia(dia, tz, horas, pausas, servico._excecoes(conn, clinica["id"], prof["id"]))
    ocupado = [(c["starts_at"], c["ends_at"]) for c in consultas] + servico._bloqueios(conn, clinica["id"], prof["id"], ini, fim)
    livres = R.subtrair(janelas, ocupado)
    pausas_dia = [(datetime.combine(dia, p.inicio, tzinfo=tz), datetime.combine(dia, p.fim, tzinfo=tz))
                  for p in pausas if p.weekday == dia.weekday()]

    texto = (f"Bom dia, {prof['name']}! ☀️\n"
             f"Hoje, {DIAS[dia.weekday()]}, {dia:%d/%m}, você tem {n} {palavra} na {clinica['name']}:\n\n"
             + "\n".join(linhas) + "\n")
    if pausas_dia:
        texto += f"\n🍽 Pausa: {_faixas(pausas_dia, tz)}"
    texto += f"\n🕒 Livre: {_faixas(livres, tz)}" if livres else "\n🕒 Agenda cheia"
    texto += "\n\n✅ confirmou · ⏳ ainda não confirmou\nBom trabalho! 💪"
    return texto


def _mandar(cliente, sessao, numero: str, texto: str, prof_nome: str, dia: date, clinica: dict) -> None:
    """WAHA: texto livre. WhatsApp oficial (36C, D131): sempre o modelo do resumo — o profissional quase nunca
    escreveu para o número da clínica nas últimas 24 h."""
    if isinstance(cliente, ClienteMeta):
        modelo, params, _ = modelos_meta.resumo_dia(prof_nome, dia, clinica, texto)
        cliente.enviar_modelo(numero, modelo.nome, params)
    else:
        cliente.enviar_texto(sessao, f"{numero.lstrip('+')}@c.us", texto, simular_digitacao=False)


def _registrar(conn, clinic_id, prof_id, dia, status, body=None, erro=None, enviado=False) -> None:
    conn.execute(
        """insert into professional_digests (clinic_id, professional_id, dia, status, body, attempts, error, sent_at)
           values (%s, %s, %s, %s, %s, 1, %s, case when %s then now() end)
           on conflict (professional_id, dia) do update set status = excluded.status, body = excluded.body,
             attempts = professional_digests.attempts + 1, error = excluded.error, sent_at = excluded.sent_at""",
        (clinic_id, prof_id, dia, status, body, erro, enviado),
    )


def enviar_resumos(conn, agora: datetime, cliente: ClienteWaha | None = None, s: Settings | None = None,
                   so_clinica: UUID | None = None) -> int:
    """Uma passada: manda os resumos que venceram. Devolve quantos saíram. `so_clinica` é para os testes."""
    s = s or get_settings()
    permitidos = lista_de_teste(s)
    profs = conn.cursor(row_factory=dict_row).execute(
        """select p.id, p.clinic_id, p.name, p.whatsapp_pessoal, p.resumo_hora,
                  d.status as feito, d.attempts as tentativas
           from professionals p join clinics c on c.id = p.clinic_id
           left join professional_digests d on d.professional_id = p.id
             and d.dia = (%s at time zone c.timezone)::date
           where p.active and p.resumo_ativo and p.whatsapp_pessoal is not null and c.status = 'ativa'
             and (%s::uuid is null or p.clinic_id = %s::uuid)""",
        (agora, so_clinica, so_clinica),
    ).fetchall()
    enviados = 0
    for p in profs:
        if p["feito"] in ("enviado", "sem_consulta", "pulado") or (p["tentativas"] or 0) >= MAX_TENTATIVAS:
            continue
        try:
            clinica = servico.carregar_clinica(conn, p["clinic_id"])
        except Exception:  # noqa: BLE001 — clínica suspensa etc.
            continue
        tz = clinica["tz"]
        local = agora.astimezone(tz)
        dia = local.date()
        hora = datetime.combine(dia, RM.hora(p["resumo_hora"]), tzinfo=tz)
        if local < hora:
            continue
        horas, _ = servico._horario(conn, clinica["id"])
        if dia.weekday() not in horas:  # D98: só em dia que a clínica abre
            continue
        if local > hora + timedelta(hours=JANELA_HORAS):
            _registrar(conn, clinica["id"], p["id"], dia, "pulado", erro="passou da hora (sistema estava fora do ar)")
            conn.commit()
            continue
        texto = montar(conn, clinica, p, dia)
        if texto is None:
            _registrar(conn, clinica["id"], p["id"], dia, "sem_consulta")
        elif permitidos is not None and p["whatsapp_pessoal"] not in permitidos:
            _registrar(conn, clinica["id"], p["id"], dia, "pulado", texto, "modo de teste: número fora de ENVIO_SOMENTE_PARA")
        else:
            inst = conn.execute("select session from whatsapp_instances where clinic_id = %s and enabled",
                                (clinica["id"],)).fetchone()
            if not inst:
                _registrar(conn, clinica["id"], p["id"], dia, "falhou", texto, "clínica sem WhatsApp conectado")
            else:
                try:
                    _mandar(cliente or cliente_da_clinica(conn, clinica["id"]), inst[0], p["whatsapp_pessoal"], texto,
                            p["name"], dia, clinica)
                    _registrar(conn, clinica["id"], p["id"], dia, "enviado", texto, enviado=True)
                    enviados += 1
                except WahaErro as e:
                    log.warning("resumo do dia não saiu (%s): %s", p["name"], e)
                    _registrar(conn, clinica["id"], p["id"], dia, "falhou", texto, str(e)[:300])
        conn.commit()
    return enviados


def enviar_teste(conn, clinica: dict, prof: dict, agora: datetime, cliente: ClienteWaha | None = None,
                 s: Settings | None = None) -> dict:
    """Botão "Mandar teste agora": manda já o resumo do próximo dia com consulta (até 14 dias), marcado como teste.
    Não conta como o envio do dia (não grava em professional_digests). Respeita o modo de teste."""
    s = s or get_settings()
    if not prof.get("whatsapp_pessoal"):
        raise WahaErro("Cadastre o WhatsApp pessoal do profissional antes de testar.")
    permitidos = lista_de_teste(s)
    if permitidos is not None and prof["whatsapp_pessoal"] not in permitidos:
        raise WahaErro("Modo de teste: esse número não está em ENVIO_SOMENTE_PARA.")
    inst = conn.execute("select session from whatsapp_instances where clinic_id = %s and enabled", (clinica["id"],)).fetchone()
    if not inst:
        raise WahaErro("A clínica não tem WhatsApp ligado.")
    hoje = agora.astimezone(clinica["tz"]).date()
    texto, dia = None, hoje
    for i in range(15):
        dia = hoje + timedelta(days=i)
        texto = montar(conn, clinica, prof, dia)
        if texto:
            break
    if not texto:
        texto = f"Bom dia, {prof['name']}! ☀️\nVocê não tem consultas marcadas nos próximos 14 dias."
    corpo = f"🧪 Teste do resumo do dia (de verdade ele chega às {prof.get('resumo_hora') or '07:00'})\n\n{texto}"
    c = cliente or cliente_da_clinica(conn, clinica["id"])
    if isinstance(c, ClienteMeta):  # 36C: na Meta sai o modelo do resumo (o "🧪 teste" não cabe nele)
        _mandar(c, inst[0], prof["whatsapp_pessoal"], texto, prof["name"], dia, clinica)
    else:
        c.enviar_texto(inst[0], f"{prof['whatsapp_pessoal'].lstrip('+')}@c.us", corpo, simular_digitacao=False)
    return {"ok": True, "dia": dia, "texto": corpo}
